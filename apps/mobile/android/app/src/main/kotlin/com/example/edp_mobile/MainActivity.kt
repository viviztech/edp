package com.example.edp_mobile

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import android.content.Intent
import android.net.Uri
import io.flutter.plugin.common.MethodChannel
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.codescanner.GmsBarcodeScannerOptions
import com.google.mlkit.vision.codescanner.GmsBarcodeScanning

class MainActivity : FlutterActivity() {
    private var privateFiles: PrivateFilesBridge? = null
    private var externalLinks: MethodChannel? = null
    private var attendanceScanner: MethodChannel? = null
    private var scanReply: MethodChannel.Result? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        privateFiles = PrivateFilesBridge(this, flutterEngine.dartExecutor.binaryMessenger)
        attendanceScanner = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "edp/attendance_scanner").also { channel ->
            channel.setMethodCallHandler { call, result ->
                if (call.method != "scan") { result.notImplemented(); return@setMethodCallHandler }
                if (scanReply != null || isFinishing || isDestroyed) {
                    result.error("unavailable", "Scanner unavailable", null); return@setMethodCallHandler
                }
                scanReply = result
                val options = GmsBarcodeScannerOptions.Builder()
                    .setBarcodeFormats(Barcode.FORMAT_QR_CODE).build()
                try {
                    // Google Play services owns its camera UI and permission; no frames enter Flutter.
                    GmsBarcodeScanning.getClient(this, options).startScan()
                        .addOnSuccessListener { barcode ->
                            if (scanReply !== result) return@addOnSuccessListener
                            val reply = scanReply; scanReply = null
                            val raw = barcode.rawValue
                            if (raw != null && Regex("^edp-attendance:[A-Za-z0-9_-]{32,128}$").matches(raw)) {
                                reply?.success(raw)
                            } else { reply?.error("invalid_payload", "Unsupported attendance code", null) }
                        }
                        .addOnCanceledListener {
                            if (scanReply === result) { scanReply = null; result.success(null) }
                        }
                        .addOnFailureListener {
                            if (scanReply === result) { scanReply = null; result.error("unavailable", "Scanner unavailable", null) }
                        }
                } catch (_: Exception) {
                    scanReply = null; result.error("unavailable", "Scanner unavailable", null)
                }
            }
        }
        externalLinks = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "edp/external_links").also { channel ->
            channel.setMethodCallHandler { call, result ->
                if (call.method != "open") { result.notImplemented(); return@setMethodCallHandler }
                val raw = call.argument<String>("url")
                if (raw == null || raw.length > 2048 || raw.any { it <= ' ' || it.code == 127 } || raw.contains('\\')) {
                    result.success(false); return@setMethodCallHandler
                }
                try {
                    val uri = Uri.parse(raw)
                    if (uri.scheme !in setOf("https", "http") || uri.host.isNullOrEmpty() || !uri.userInfo.isNullOrEmpty()) {
                        result.success(false); return@setMethodCallHandler
                    }
                    startActivity(Intent(Intent.ACTION_VIEW, uri).addCategory(Intent.CATEGORY_BROWSABLE))
                    result.success(true)
                } catch (_: Exception) { result.success(false) }
            }
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        if (privateFiles?.onActivityResult(requestCode, resultCode, data) != true) {
            super.onActivityResult(requestCode, resultCode, data)
        }
    }

    override fun cleanUpFlutterEngine(flutterEngine: FlutterEngine) {
        privateFiles?.detach()
        privateFiles = null
        externalLinks?.setMethodCallHandler(null)
        externalLinks = null
        attendanceScanner?.setMethodCallHandler(null)
        attendanceScanner = null
        val reply = scanReply; scanReply = null
        reply?.error("unavailable", "Scanner closed", null)
        super.cleanUpFlutterEngine(flutterEngine)
    }
}
