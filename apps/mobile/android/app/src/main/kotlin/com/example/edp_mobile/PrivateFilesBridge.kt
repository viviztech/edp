package com.example.edp_mobile

import android.app.Activity
import android.app.KeyguardManager
import android.app.admin.DevicePolicyManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.CancellationSignal
import android.os.Handler
import android.os.Looper
import android.os.UserManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.plugin.common.BinaryMessenger
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import java.io.Closeable
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.InputStreamReader
import java.io.RandomAccessFile
import java.nio.charset.CodingErrorAction
import java.security.MessageDigest
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicReference

/** Opaque private snapshots. Selected URI, name and paths never cross the channel. */
class PrivateFilesBridge(
    private val activity: FlutterActivity,
    messenger: BinaryMessenger,
) : MethodChannel.MethodCallHandler {
    companion object {
        private const val MAX_BYTES = 10 * 1024 * 1024
        private const val CHUNK = 64 * 1024
        private const val MAX_HANDLES = 8
        private const val MAX_STORE_BYTES = 4L * MAX_BYTES
        // Never reuse a request code within a process, including engine reattachment.
        private val NEXT_PICK_REQUEST = AtomicInteger(40000)
        private val TYPES = setOf("application/pdf", "image/png", "image/jpeg", "image/webp", "text/plain")
        private val ID = Regex("^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
        private val HASH = Regex("^[0-9a-f]{64}$")
        private val CHILD = Regex("^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\\.(part|bin)$")
    }

    private class Failure(val code: String) : Exception()
    private class Scope(val id: String, val directory: File) {
        val closed = AtomicBoolean(false)
        val entries = mutableMapOf<String, Entry>() // IO executor only.
        val source = AtomicReference<Closeable?>(null)
        val signal = AtomicReference<CancellationSignal?>(null)
    }
    private class Entry(
        val id: String,
        var file: File,
        val mediaType: String,
        val byteSize: Long,
        val sha256: String,
        var complete: Boolean,
        var output: FileOutputStream? = null,
    ) {
        var received = 0L
        val digest: MessageDigest = MessageDigest.getInstance("SHA-256")
    }
    private data class Pick(
        val requestCode: Int,
        val scope: Scope,
        val types: Set<String>,
        val maxBytes: Long,
        val result: MethodChannel.Result,
    )

    private val channel = MethodChannel(messenger, "edp/private_files")
    private val main = Handler(Looper.getMainLooper())
    private val io = Executors.newSingleThreadExecutor { task -> Thread(task, "edp-private-files").apply { isDaemon = true } }
    private val closer = Executors.newCachedThreadPool { task -> Thread(task, "edp-private-cancel").apply { isDaemon = true } }
    private val scopes = ConcurrentHashMap<String, Scope>()
    private val root = File(activity.cacheDir.canonicalFile, "edp-private-v1")
    @Volatile private var initialized = false
    @Volatile private var broken = false
    private var pick: Pick? = null // Main thread only.
    private var outstandingPickRequest: Int? = null // Includes cancelled launch tombstones.

    init { channel.setMethodCallHandler(this) }

    private fun fail(code: String): Nothing = throw Failure(code)
    private fun identifier(value: Any?): String {
        val text = value as? String ?: fail("invalid_request")
        if (!ID.matches(text)) fail("invalid_request")
        return text
    }
    private fun number(value: Any?): Long = when (value) {
        is Int -> value.toLong()
        is Long -> value
        else -> fail("invalid_request")
    }
    private fun requireProtectedStorage() {
        try {
            val policy = activity.getSystemService(Context.DEVICE_POLICY_SERVICE) as? DevicePolicyManager
                ?: fail("private_storage_unavailable")
            val user = activity.getSystemService(Context.USER_SERVICE) as? UserManager
                ?: fail("private_storage_unavailable")
            val keyguard = activity.getSystemService(Context.KEYGUARD_SERVICE) as? KeyguardManager
                ?: fail("private_storage_unavailable")
            // A private cache path alone is not evidence of encryption. Inactive,
            // unsupported, activating and default-key-only storage are rejected.
            val encrypted = policy.storageEncryptionStatus in setOf(
                DevicePolicyManager.ENCRYPTION_STATUS_ACTIVE,
                DevicePolicyManager.ENCRYPTION_STATUS_ACTIVE_PER_USER,
            )
            if (!encrypted || activity.isDeviceProtectedStorage || !user.isUserUnlocked ||
                !keyguard.isDeviceSecure || keyguard.isDeviceLocked) fail("private_storage_unavailable")
        } catch (failure: Failure) { throw failure }
        catch (_: Exception) { fail("private_storage_unavailable") }
    }
    private fun check(scope: Scope, requireProtection: Boolean = true) {
        if (broken || scope.closed.get() || scopes[scope.id] !== scope) fail("private_file_cancelled")
        if (requireProtection) requireProtectedStorage()
    }
    private fun scope(call: MethodCall, requireProtection: Boolean = true): Scope {
        if (!initialized || broken) fail("private_files_unavailable")
        val item = scopes[identifier(call.argument<Any>("scope"))] ?: fail("private_file_cancelled")
        check(item, requireProtection)
        return item
    }
    private fun entry(scope: Scope, call: MethodCall): Entry {
        check(scope)
        return scope.entries[identifier(call.argument<Any>("id"))] ?: fail("private_file_missing")
    }
    private fun operation(result: MethodChannel.Result, action: () -> Any?) {
        io.execute {
            try {
                val value = action()
                main.post { result.success(value) }
            } catch (failure: Failure) {
                main.post { result.error(failure.code, null, null) }
            } catch (_: Exception) {
                main.post { result.error("private_files_unavailable", null, null) }
            }
        }
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        try {
            when (call.method) {
                "initialize" -> operation(result) { initialize(); null }
                "createScope" -> operation(result) {
                    requireProtectedStorage()
                    if (!initialized || broken || scopes.size >= 8) fail("private_files_unavailable")
                    val id = UUID.randomUUID().toString()
                    val directory = File(root, id)
                    if (!directory.mkdir() || directory.canonicalFile.parentFile != root.canonicalFile) fail("private_files_unavailable")
                    scopes[id] = Scope(id, directory)
                    id
                }
                "closeScopes" -> {
                    scopes.values.forEach { cancel(it) }
                    cancelPicker(null)
                    operation(result) { scopes.values.toList().forEach { removeScope(it) }; null }
                }
                "closeScope" -> {
                    val id = identifier(call.argument<Any>("scope"))
                    val item = scopes[id]
                    if (item != null) cancel(item)
                    cancelPicker(id)
                    operation(result) { if (item != null) removeScope(item); null }
                }
                "pickSnapshot" -> startPick(call, result)
                "verify" -> operation(result) {
                    val item = scope(call); verify(item, entry(item, call)); null
                }
                "read" -> operation(result) {
                    val item = scope(call)
                    val file = entry(item, call)
                    val offset = number(call.argument<Any>("offset"))
                    val count = number(call.argument<Any>("count"))
                    if (!file.complete || offset < 0 || offset > file.byteSize || count !in 1..CHUNK.toLong() || count > file.byteSize - offset) fail("invalid_request")
                    val bytes = ByteArray(count.toInt())
                    RandomAccessFile(owned(item, file.file), "r").use { source -> source.seek(offset); source.readFully(bytes) }
                    check(item)
                    bytes
                }
                "release", "abort" -> operation(result) {
                    // Cleanup remains possible after lock or protection changes.
                    val item = scope(call, requireProtection = false)
                    val id = identifier(call.argument<Any>("id"))
                    item.entries[id]?.let { dispose(item, it); item.entries.remove(id) }
                    null
                }
                "beginDownload" -> operation(result) {
                    val item = scope(call)
                    val type = call.argument<String>("media_type") ?: fail("invalid_request")
                    val max = number(call.argument<Any>("max_bytes"))
                    val size = number(call.argument<Any>("expected_byte_size"))
                    val hash = call.argument<String>("expected_sha256") ?: fail("invalid_request")
                    if (type !in TYPES || max !in 1..MAX_BYTES.toLong() || size !in 1..max || !HASH.matches(hash)) fail("file_metadata_invalid")
                    capacity(size)
                    val id = UUID.randomUUID().toString()
                    val file = newFile(item, id, "part")
                    val output = try { FileOutputStream(file, false) }
                    catch (failure: Exception) {
                        if (file.exists() && !owned(item, file).delete()) broken = true
                        throw failure
                    }
                    item.entries[id] = Entry(id, file, type, size, hash, false, output)
                    id
                }
                "append" -> operation(result) {
                    val item = scope(call)
                    val file = entry(item, call)
                    val bytes = call.argument<ByteArray>("bytes") ?: fail("invalid_request")
                    if (file.complete || bytes.isEmpty() || bytes.size > CHUNK || file.received + bytes.size > file.byteSize) fail("file_too_large")
                    (file.output ?: fail("private_file_missing")).write(bytes)
                    file.digest.update(bytes)
                    file.received += bytes.size
                    check(item)
                    null
                }
                "finish" -> operation(result) {
                    val item = scope(call)
                    val file = entry(item, call)
                    try {
                        if (file.complete) fail("invalid_request")
                        file.output?.flush(); file.output?.close(); file.output = null
                        if (file.received != file.byteSize || !same(file.digest.digest(), file.sha256)) fail("file_changed")
                        if (detect(item, file.file) != file.mediaType) fail("file_type_invalid")
                        complete(item, file)
                        descriptor(file)
                    } catch (failure: Exception) {
                        dispose(item, file); item.entries.remove(file.id)
                        throw failure
                    }
                }
                else -> result.notImplemented()
            }
        } catch (failure: Failure) {
            result.error(failure.code, null, null)
        } catch (_: Exception) {
            result.error("private_files_unavailable", null, null)
        }
    }

    private fun initialize() {
        if (initialized) return
        if (broken) fail("private_files_unavailable")
        if (root.exists() && (root.canonicalFile != root.absoluteFile || !root.isDirectory)) fail("private_files_unavailable")
        if (!root.exists() && !root.mkdir()) fail("private_files_unavailable")
        val children = root.listFiles() ?: fail("private_files_unavailable")
        if (children.size > 64) fail("private_files_unavailable")
        for (child in children) {
            if (!ID.matches(child.name) || child.canonicalFile != child.absoluteFile || child.canonicalFile.parentFile != root.canonicalFile || !child.isDirectory) fail("private_files_unavailable")
            cleanDirectory(child)
        }
        initialized = true
    }

    private fun owned(scope: Scope, file: File): File {
        if (scope.directory.canonicalFile != scope.directory.absoluteFile ||
            scope.directory.canonicalFile.parentFile != root.canonicalFile ||
            file.canonicalFile != file.absoluteFile ||
            file.canonicalFile.parentFile != scope.directory.canonicalFile || !CHILD.matches(file.name)) fail("private_files_unavailable")
        return file
    }
    private fun newFile(scope: Scope, id: String, suffix: String): File {
        check(scope)
        val file = owned(scope, File(scope.directory, "$id.$suffix"))
        if (!file.createNewFile()) fail("private_files_unavailable")
        return file
    }
    private fun capacity(bytes: Long) {
        val entries = scopes.values.flatMap { it.entries.values }
        if (entries.size >= MAX_HANDLES || entries.sumOf { it.byteSize } + bytes > MAX_STORE_BYTES) fail("private_file_limit")
    }
    private fun complete(scope: Scope, entry: Entry) {
        check(scope)
        val target = owned(scope, File(scope.directory, "${entry.id}.bin"))
        if (target.exists() || !entry.file.renameTo(target)) fail("private_files_unavailable")
        entry.file = target
        if (!target.setReadOnly()) fail("private_files_unavailable")
        entry.complete = true
    }
    private fun descriptor(entry: Entry): Map<String, Any> = mapOf(
        "id" to entry.id, "media_type" to entry.mediaType, "byte_size" to entry.byteSize, "sha256" to entry.sha256,
    )
    private fun same(bytes: ByteArray, expected: String): Boolean = MessageDigest.isEqual(
        bytes, expected.chunked(2).map { it.toInt(16).toByte() }.toByteArray(),
    )
    private fun digest(bytes: ByteArray): String = bytes.joinToString("") { "%02x".format(it.toInt() and 255) }

    private fun verify(scope: Scope, entry: Entry) {
        if (!entry.complete || owned(scope, entry.file).length() != entry.byteSize) fail("file_changed")
        val hash = MessageDigest.getInstance("SHA-256")
        val buffer = ByteArray(CHUNK)
        var size = 0L
        FileInputStream(entry.file).use { source ->
            while (true) {
                check(scope)
                val count = source.read(buffer)
                if (count < 0) break
                size += count
                if (size > entry.byteSize) fail("file_changed")
                hash.update(buffer, 0, count)
            }
        }
        if (size != entry.byteSize || !same(hash.digest(), entry.sha256) || detect(scope, entry.file) != entry.mediaType) fail("file_changed")
        check(scope)
    }

    private fun detect(scope: Scope, file: File): String {
        check(scope)
        val prefix = ByteArray(16)
        val count = FileInputStream(file).use { it.read(prefix) }
        fun starts(bytes: IntArray) = count >= bytes.size && bytes.indices.all { (prefix[it].toInt() and 255) == bytes[it] }
        if (starts(intArrayOf(37, 80, 68, 70, 45))) return "application/pdf"
        if (starts(intArrayOf(137, 80, 78, 71, 13, 10, 26, 10))) return "image/png"
        if (starts(intArrayOf(255, 216, 255))) return "image/jpeg"
        if (count >= 12 && String(prefix, 0, 4, Charsets.US_ASCII) == "RIFF" && String(prefix, 8, 4, Charsets.US_ASCII) == "WEBP") return "image/webp"
        val decoder = Charsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT)
        try {
            InputStreamReader(FileInputStream(file), decoder).use { reader ->
                val chars = CharArray(16 * 1024)
                while (true) {
                    check(scope)
                    val length = reader.read(chars)
                    if (length < 0) break
                    for (index in 0 until length) {
                        val value = chars[index].code
                        if ((value < 32 && value != 9 && value != 10 && value != 13) || value in 127..159) fail("file_type_invalid")
                    }
                }
            }
        } catch (failure: Failure) { throw failure }
        catch (_: Exception) { fail("file_type_invalid") }
        return "text/plain"
    }

    private fun startPick(call: MethodCall, result: MethodChannel.Result) {
        val item = scope(call)
        if (pick != null || outstandingPickRequest != null) fail("private_files_unavailable")
        val max = number(call.argument<Any>("max_bytes"))
        val values = call.argument<List<Any>>("allowed_types") ?: fail("invalid_request")
        if (max !in 1..MAX_BYTES.toLong() || values.isEmpty() || values.any { it !is String || it !in TYPES }) fail("file_metadata_invalid")
        val types = values.map { it as String }.toSet()
        val requestCode = NEXT_PICK_REQUEST.getAndIncrement()
        if (requestCode !in 40000..65534) fail("private_files_unavailable")
        val pending = Pick(requestCode, item, types, max, result)
        pick = pending
        outstandingPickRequest = requestCode
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            type = if (types.size == 1) types.first() else "*/*"
            putExtra(Intent.EXTRA_MIME_TYPES, types.toTypedArray())
            putExtra(Intent.EXTRA_ALLOW_MULTIPLE, false)
        }
        try { activity.startActivityForResult(intent, requestCode) }
        catch (_: Exception) { pick = null; outstandingPickRequest = null; fail("private_files_unavailable") }
    }

    fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?): Boolean {
        if (requestCode != outstandingPickRequest) return false
        outstandingPickRequest = null
        val pending = pick ?: return true
        pick = null
        if (pending.requestCode != requestCode) {
            pending.result.error("private_file_cancelled", null, null)
            return true
        }
        if (resultCode != Activity.RESULT_OK) { pending.result.success(null); return true }
        val uri = data?.data
        if (uri == null || uri.scheme != "content" || (data.clipData?.itemCount ?: 1) > 1) {
            pending.result.error("file_metadata_invalid", null, null)
            return true
        }
        operation(pending.result) { copySelection(pending, uri) }
        return true
    }

    private fun copySelection(pending: Pick, uri: Uri): Map<String, Any> {
        val item = pending.scope
        check(item)
        capacity(pending.maxBytes)
        val id = UUID.randomUUID().toString()
        val file = newFile(item, id, "part")
        val cancellation = CancellationSignal()
        item.signal.set(cancellation)
        val deadline = Runnable { cancellation.cancel(); cancelSource(item) }
        main.postDelayed(deadline, 30_000)
        var entry: Entry? = null
        try {
            val providerFile = activity.contentResolver.openFileDescriptor(uri, "r", cancellation) ?: fail("private_files_unavailable")
            val source = android.os.ParcelFileDescriptor.AutoCloseInputStream(providerFile)
            item.source.set(source)
            val hash = MessageDigest.getInstance("SHA-256")
            var size = 0L
            source.use { input -> FileOutputStream(file, false).use { output ->
                val buffer = ByteArray(CHUNK)
                while (true) {
                    check(item)
                    if (cancellation.isCanceled) fail("private_file_cancelled")
                    val length = input.read(buffer)
                    if (length < 0) break
                    size += length
                    if (size > pending.maxBytes) fail("file_too_large")
                    output.write(buffer, 0, length)
                    hash.update(buffer, 0, length)
                }
                output.flush()
            } }
            if (size == 0L) fail("file_metadata_invalid")
            val type = detect(item, file)
            if (type !in pending.types) fail("file_type_invalid")
            val snapshot = Entry(id, file, type, size, digest(hash.digest()), false)
            entry = snapshot
            complete(item, snapshot)
            check(item)
            item.entries[id] = snapshot
            return descriptor(snapshot)
        } finally {
            main.removeCallbacks(deadline)
            item.source.set(null)
            item.signal.set(null)
            if (item.entries[id] == null) {
                val remaining = entry?.file ?: file
                if (remaining.exists() && !owned(item, remaining).delete()) broken = true
            }
        }
    }

    private fun cancelSource(scope: Scope) {
        scope.signal.get()?.cancel()
        val source = scope.source.getAndSet(null)
        if (source != null) closer.execute { try { source.close() } catch (_: Exception) {} }
    }
    private fun cancel(scope: Scope) { scope.closed.set(true); cancelSource(scope) }
    private fun cancelPicker(id: String?) {
        val pending = pick ?: return
        if (id == null || pending.scope.id == id) {
            pick = null
            // Keep outstandingPickRequest until its platform callback is drained.
            pending.result.error("private_file_cancelled", null, null)
        }
    }
    private fun dispose(scope: Scope, entry: Entry) {
        entry.output?.close(); entry.output = null
        if (entry.file.exists() && !owned(scope, entry.file).delete()) { broken = true; fail("private_files_unavailable") }
    }
    private fun cleanDirectory(directory: File) {
        val files = directory.listFiles() ?: fail("private_files_unavailable")
        if (files.size > 32) fail("private_files_unavailable")
        for (file in files) {
            if (!CHILD.matches(file.name) || file.canonicalFile != file.absoluteFile || file.canonicalFile.parentFile != directory.canonicalFile || !file.isFile || !file.delete()) fail("private_files_unavailable")
        }
        if (!directory.delete()) fail("private_files_unavailable")
    }
    private fun removeScope(scope: Scope) {
        try {
            scope.entries.values.toList().forEach { dispose(scope, it) }
            scope.entries.clear()
            if (scope.directory.exists()) cleanDirectory(scope.directory)
            scopes.remove(scope.id, scope)
        } catch (failure: Exception) { broken = true; throw failure }
    }

    fun detach() {
        channel.setMethodCallHandler(null)
        scopes.values.forEach { cancel(it) }
        cancelPicker(null)
        io.execute {
            try { scopes.values.toList().forEach { removeScope(it) } }
            catch (_: Exception) { broken = true }
            finally { closer.shutdown() }
        }
        io.shutdown()
    }
}
