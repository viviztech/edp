import CryptoKit
import CoreFoundation
import Darwin
import Flutter
import UniformTypeIdentifiers
import UIKit

/// Private snapshots expose only opaque identifiers and bounded chunks to Dart.
final class PrivateFilesBridge: NSObject, FlutterPlugin, UIDocumentPickerDelegate {
  private static let maxBytes = 10 * 1024 * 1024
  private static let chunkBytes = 64 * 1024
  private static let childPattern = "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\\.(part|bin)$"
  private static let mediaTypes: Set<String> = [
    "application/pdf", "image/png", "image/jpeg", "image/webp", "text/plain",
  ]
  private enum Failure: Error {
    case code(String)
  }
  private final class Scope {
    let id: String
    let directory: URL
    let lock = NSLock()
    private var cancelled = false
    private var copyCancelled = false
    private var copyGeneration = 0
    private var source: InputStream?
    private var coordinator: NSFileCoordinator?
    // Only accessed on the serial IO queue.
    var entries: [String: Entry] = [:]

    init(id: String, directory: URL) {
      self.id = id
      self.directory = directory
    }
    var closed: Bool {
      lock.lock(); defer { lock.unlock() }
      return cancelled
    }
    func setSource(_ source: InputStream?, coordinator: NSFileCoordinator?) {
      lock.lock(); defer { lock.unlock() }
      self.source = source
      self.coordinator = coordinator
    }
    func beginCopy() -> Int {
      lock.lock(); defer { lock.unlock() }
      copyCancelled = false
      copyGeneration += 1
      return copyGeneration
    }
    func finishCopy(_ generation: Int) {
      lock.lock(); defer { lock.unlock() }
      guard copyGeneration == generation else { return }
      copyGeneration += 1
      source = nil
      coordinator = nil
    }
    var copyingCancelled: Bool {
      lock.lock(); defer { lock.unlock() }
      return copyCancelled || cancelled
    }
    func cancelCopy(generation: Int? = nil) {
      lock.lock()
      if let generation, copyGeneration != generation { lock.unlock(); return }
      copyCancelled = true
      let activeSource = source
      let activeCoordinator = coordinator
      lock.unlock()
      if activeCoordinator != nil || activeSource != nil {
        DispatchQueue.global(qos: .utility).async {
          activeCoordinator?.cancel()
          activeSource?.close()
        }
      }
    }
    func cancel() {
      lock.lock()
      cancelled = true
      lock.unlock()
      // Keep platform-provider cancellation off Flutter's main thread.
      cancelCopy()
    }
  }
  private final class Entry {
    let id: String
    var url: URL
    let mediaType: String
    let byteSize: Int
    let sha256: String
    var complete = false
    var output: FileHandle?
    var received = 0
    var hasher = SHA256()

    init(id: String, url: URL, mediaType: String, byteSize: Int, sha256: String) {
      self.id = id
      self.url = url
      self.mediaType = mediaType
      self.byteSize = byteSize
      self.sha256 = sha256
    }
    var descriptor: [String: Any] {
      ["id": id, "media_type": mediaType, "byte_size": byteSize, "sha256": sha256]
    }
  }
  private struct PendingPick {
    let scope: Scope
    let mediaTypes: Set<String>
    let maxBytes: Int
    let result: FlutterResult
  }

  private let registrar: FlutterPluginRegistrar
  private let io = DispatchQueue(label: "edp.private-files", qos: .utility)
  private let stateLock = NSLock()
  private var scopes: [String: Scope] = [:]
  private var initialized = false
  private var broken = false
  private var detached = false
  private var channel: FlutterMethodChannel?
  private var pendingPick: PendingPick? // Main thread only.
  private weak var picker: UIDocumentPickerViewController?
  private var root: URL {
    FileManager.default.temporaryDirectory.resolvingSymlinksInPath()
      .appendingPathComponent("edp-private-v1", isDirectory: true)
  }

  static func register(with registrar: FlutterPluginRegistrar) {
    let bridge = PrivateFilesBridge(registrar: registrar)
    let channel = FlutterMethodChannel(name: "edp/private_files", binaryMessenger: registrar.messenger())
    bridge.channel = channel
    registrar.addMethodCallDelegate(bridge, channel: channel)
    // Flutter invokes engine detachment only on the published plugin instance.
    registrar.publish(bridge)
  }

  private init(registrar: FlutterPluginRegistrar) { self.registrar = registrar }

  func detachFromEngine(for registrar: FlutterPluginRegistrar) {
    let closing: [Scope]? = withState {
      guard !detached else { return nil }
      detached = true
      return Array(scopes.values)
    }
    guard let closing else { return }
    closing.forEach { $0.cancel() }
    let removeHandler = {
      self.channel?.setMethodCallHandler(nil)
      self.channel = nil
      self.cancelPicker(nil, notify: false)
    }
    if Thread.isMainThread { removeHandler() }
    else { DispatchQueue.main.async(execute: removeHandler) }
    io.async {
      // An in-flight create may register its scope after the first snapshot.
      // Cleanup runs behind it on the same queue and inspects current scopes.
      for scope in self.withState({ Array(self.scopes.values) }) {
        scope.cancel()
        do { try self.removeScope(scope) }
        catch { self.withState { self.broken = true } }
      }
    }
  }

  private func fail(_ code: String) throws -> Never { throw Failure.code(code) }
  private func identifier(_ value: Any?) throws -> String {
    guard let value = value as? String,
      value.range(of: "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", options: .regularExpression) != nil
    else { try fail("invalid_request") }
    return value
  }
  private func integer(_ value: Any?) throws -> Int {
    guard let value = value as? NSNumber, CFGetTypeID(value) != CFBooleanGetTypeID(),
      !["f", "d"].contains(String(cString: value.objCType)) else { try fail("invalid_request") }
    let number = value.int64Value
    guard number >= 0, number <= Int64(Int.max) else { try fail("invalid_request") }
    return Int(number)
  }
  private func withState<T>(_ action: () throws -> T) rethrows -> T {
    stateLock.lock(); defer { stateLock.unlock() }
    return try action()
  }
  private func check(_ scope: Scope) throws {
    guard !scope.closed,
      withState({ !detached && !broken && scopes[scope.id] === scope }) else { try fail("private_file_cancelled") }
  }
  private func scope(_ args: [String: Any]) throws -> Scope {
    let id = try identifier(args["scope"])
    let scope = withState { initialized && !broken && !detached ? scopes[id] : nil }
    guard let scope else { try fail("private_file_cancelled") }
    try check(scope)
    return scope
  }
  private func entry(_ scope: Scope, _ args: [String: Any]) throws -> Entry {
    try check(scope)
    guard let entry = scope.entries[try identifier(args["id"])] else { try fail("private_file_missing") }
    return entry
  }
  private func resultError(_ error: Error) -> FlutterError {
    if case Failure.code(let code) = error { return FlutterError(code: code, message: nil, details: nil) }
    return FlutterError(code: "private_files_unavailable", message: nil, details: nil)
  }
  private func operation(_ result: @escaping FlutterResult, _ action: @escaping () throws -> Any?) {
    io.async {
      guard self.withState({ !self.detached }) else { return }
      do {
        let value = try action()
        DispatchQueue.main.async {
          guard self.withState({ !self.detached }) else { return }
          result(value)
        }
      } catch {
        let failure = self.resultError(error)
        DispatchQueue.main.async {
          guard self.withState({ !self.detached }) else { return }
          result(failure)
        }
      }
    }
  }

  func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
    guard withState({ !detached }) else { return }
    let args = call.arguments as? [String: Any] ?? [:]
    do {
      switch call.method {
      case "initialize":
        operation(result) { try self.initialize(); return nil }
      case "createScope":
        operation(result) {
          guard self.withState({ self.initialized && !self.broken && !self.detached && self.scopes.count < 8 }) else {
            try self.fail("private_files_unavailable")
          }
          let id = UUID().uuidString.lowercased()
          let directory = self.root.appendingPathComponent(id, isDirectory: true)
          try self.createDirectory(directory)
          let scope = Scope(id: id, directory: directory)
          let registered = self.withState {
            guard !self.detached else { return false }
            self.scopes[id] = scope
            return true
          }
          guard registered else {
            scope.cancel()
            try self.removeScope(scope)
            try self.fail("private_file_cancelled")
          }
          return id
        }
      case "closeScopes", "closeScope":
        let id = call.method == "closeScope" ? try identifier(args["scope"]) : nil
        let closing = withState { scopes.values.filter { id == nil || $0.id == id } }
        closing.forEach { $0.cancel() }
        cancelPicker(id)
        operation(result) { for scope in closing { try self.removeScope(scope) }; return nil }
      case "pickSnapshot":
        try startPick(args, result)
      case "verify":
        operation(result) {
          let scope = try self.scope(args)
          try self.verify(scope, self.entry(scope, args))
          return nil
        }
      case "read":
        operation(result) {
          let scope = try self.scope(args), file = try self.entry(scope, args)
          let offset = try self.integer(args["offset"]), count = try self.integer(args["count"])
          guard file.complete, offset <= file.byteSize, (1...Self.chunkBytes).contains(count),
            count <= file.byteSize - offset else { try self.fail("invalid_request") }
          let input = try FileHandle(forReadingFrom: self.owned(scope, file.url))
          defer { try? input.close() }
          try input.seek(toOffset: UInt64(offset))
          let bytes = try input.read(upToCount: count) ?? Data()
          guard bytes.count == count else { try self.fail("file_changed") }
          try self.check(scope)
          return FlutterStandardTypedData(bytes: bytes)
        }
      case "release", "abort":
        operation(result) {
          let scope = try self.scope(args), id = try self.identifier(args["id"])
          if let entry = scope.entries[id] {
            try self.dispose(scope, entry)
            scope.entries.removeValue(forKey: id)
          }
          return nil
        }
      case "beginDownload":
        operation(result) {
          let scope = try self.scope(args)
          guard let type = args["media_type"] as? String, Self.mediaTypes.contains(type),
            let digest = args["expected_sha256"] as? String,
            digest.range(of: "^[0-9a-f]{64}$", options: .regularExpression) != nil else { try self.fail("file_metadata_invalid") }
          let max = try self.integer(args["max_bytes"]), size = try self.integer(args["expected_byte_size"])
          guard (1...Self.maxBytes).contains(max), size > 0, size <= max else { try self.fail("file_metadata_invalid") }
          try self.capacity(size)
          let id = UUID().uuidString.lowercased()
          let (url, output) = try self.newFile(scope, id)
          let entry = Entry(id: id, url: url, mediaType: type, byteSize: size, sha256: digest)
          entry.output = output
          scope.entries[id] = entry
          return id
        }
      case "append":
        operation(result) {
          let scope = try self.scope(args), entry = try self.entry(scope, args)
          guard let typed = args["bytes"] as? FlutterStandardTypedData else { try self.fail("invalid_request") }
          let bytes = typed.data
          guard !entry.complete, !bytes.isEmpty, bytes.count <= Self.chunkBytes,
            bytes.count <= entry.byteSize - entry.received else { try self.fail("file_too_large") }
          guard let output = entry.output else { try self.fail("private_file_missing") }
          try output.write(contentsOf: bytes)
          entry.hasher.update(data: bytes)
          entry.received += bytes.count
          try self.check(scope)
          return nil
        }
      case "finish":
        operation(result) {
          let scope = try self.scope(args), entry = try self.entry(scope, args)
          do {
            guard !entry.complete else { try self.fail("invalid_request") }
            try entry.output?.close(); entry.output = nil
            guard entry.received == entry.byteSize,
              self.digest(entry.hasher.finalize()) == entry.sha256 else { try self.fail("file_changed") }
            guard try self.detect(scope, entry.url) == entry.mediaType else { try self.fail("file_type_invalid") }
            try self.complete(scope, entry)
            return entry.descriptor
          } catch {
            try self.dispose(scope, entry)
            scope.entries.removeValue(forKey: entry.id)
            throw error
          }
        }
      default: result(FlutterMethodNotImplemented)
      }
    } catch { result(resultError(error)) }
  }

  private func protect(_ url: URL) throws {
    var url = url
    var values = URLResourceValues()
    values.isExcludedFromBackup = true
    try url.setResourceValues(values)
    try FileManager.default.setAttributes([.protectionKey: FileProtectionType.complete], ofItemAtPath: url.path)
  }
  private func createDirectory(_ directory: URL) throws {
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false,
      attributes: [.protectionKey: FileProtectionType.complete, .posixPermissions: 0o700])
    try validate(directory, parent: directory.deletingLastPathComponent(), directory: true)
    try protect(directory)
  }
  private func validate(_ url: URL, parent: URL, directory: Bool) throws {
    let values = try url.resourceValues(forKeys: [.isSymbolicLinkKey, .isDirectoryKey, .isRegularFileKey])
    guard values.isSymbolicLink != true, url.resolvingSymlinksInPath().standardizedFileURL == url.standardizedFileURL,
      url.deletingLastPathComponent().standardizedFileURL == parent.standardizedFileURL,
      directory ? values.isDirectory == true : values.isRegularFile == true else { try fail("private_files_unavailable") }
  }
  private func initialize() throws {
    if withState({ initialized }) { return }
    guard withState({ !broken }) else { try fail("private_files_unavailable") }
    do {
      if !FileManager.default.fileExists(atPath: root.path) { try createDirectory(root) }
      try validate(root, parent: root.deletingLastPathComponent(), directory: true)
      try protect(root)
      let children = try FileManager.default.contentsOfDirectory(at: root, includingPropertiesForKeys: nil)
      guard children.count <= 64 else { try fail("private_files_unavailable") }
      for child in children {
        _ = try identifier(child.lastPathComponent)
        try validate(child, parent: root, directory: true)
        try cleanDirectory(child)
      }
      withState { initialized = true }
    } catch { withState { broken = true }; throw error }
  }
  private func owned(_ scope: Scope, _ file: URL) throws -> URL {
    try validate(scope.directory, parent: root, directory: true)
    let name = file.lastPathComponent
    guard name.range(of: Self.childPattern, options: .regularExpression) != nil,
      file.deletingLastPathComponent() == scope.directory else { try fail("private_files_unavailable") }
    if FileManager.default.fileExists(atPath: file.path) { try validate(file, parent: scope.directory, directory: false) }
    return file
  }
  private func newFile(_ scope: Scope, _ id: String) throws -> (URL, FileHandle) {
    try check(scope)
    let url = try owned(scope, scope.directory.appendingPathComponent("\(id).part"))
    let descriptor = Darwin.open(url.path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, mode_t(0o600))
    guard descriptor >= 0 else { try fail("private_files_unavailable") }
    let output = FileHandle(fileDescriptor: descriptor, closeOnDealloc: true)
    do { try protect(url) }
    catch {
      try? output.close()
      do { try FileManager.default.removeItem(at: url) } catch { withState { broken = true } }
      throw error
    }
    return (url, output)
  }
  private func capacity(_ bytes: Int) throws {
    let entries = withState { scopes.values.flatMap { $0.entries.values } }
    guard entries.count < 8, entries.reduce(0, { $0 + $1.byteSize }) + bytes <= 4 * Self.maxBytes else { try fail("private_file_limit") }
  }
  private func complete(_ scope: Scope, _ entry: Entry) throws {
    try check(scope)
    let target = try owned(scope, scope.directory.appendingPathComponent("\(entry.id).bin"))
    guard !FileManager.default.fileExists(atPath: target.path) else { try fail("private_files_unavailable") }
    try FileManager.default.moveItem(at: owned(scope, entry.url), to: target)
    entry.url = target
    try protect(target)
    try FileManager.default.setAttributes([.posixPermissions: 0o400], ofItemAtPath: target.path)
    entry.complete = true
  }
  private func digest(_ value: SHA256.Digest) -> String { value.map { String(format: "%02x", $0) }.joined() }
  private func verify(_ scope: Scope, _ entry: Entry) throws {
    guard entry.complete else { try fail("file_changed") }
    let input = try FileHandle(forReadingFrom: owned(scope, entry.url))
    defer { try? input.close() }
    var hasher = SHA256(), size = 0
    while true {
      try check(scope)
      let data = try input.read(upToCount: Self.chunkBytes) ?? Data()
      if data.isEmpty { break }
      size += data.count
      guard size <= entry.byteSize else { try fail("file_changed") }
      hasher.update(data: data)
    }
    guard size == entry.byteSize, digest(hasher.finalize()) == entry.sha256,
      try detect(scope, entry.url) == entry.mediaType else { try fail("file_changed") }
    try check(scope)
  }

  /// Validates UTF-8 incrementally, including sequences split across IO chunks.
  private struct TextValidator {
    var remaining = 0, codepoint = 0, minimum = 0
    mutating func append(_ bytes: Data) throws {
      for byte in bytes {
        let value = Int(byte)
        if remaining == 0 {
          if value < 0x80 { try check(value) }
          else if (0xc2...0xdf).contains(value) { remaining = 1; codepoint = value & 31; minimum = 0x80 }
          else if (0xe0...0xef).contains(value) { remaining = 2; codepoint = value & 15; minimum = 0x800 }
          else if (0xf0...0xf4).contains(value) { remaining = 3; codepoint = value & 7; minimum = 0x10000 }
          else { throw Failure.code("file_type_invalid") }
        } else {
          guard (0x80...0xbf).contains(value) else { throw Failure.code("file_type_invalid") }
          codepoint = (codepoint << 6) | (value & 63); remaining -= 1
          if remaining == 0 {
            guard codepoint >= minimum, codepoint <= 0x10ffff,
              !(0xd800...0xdfff).contains(codepoint) else { throw Failure.code("file_type_invalid") }
            try check(codepoint)
          }
        }
      }
    }
    private func check(_ value: Int) throws {
      if (value < 32 && value != 9 && value != 10 && value != 13) || (127...159).contains(value) {
        throw Failure.code("file_type_invalid")
      }
    }
  }
  private func detect(_ scope: Scope, _ url: URL) throws -> String {
    let source = try FileHandle(forReadingFrom: owned(scope, url))
    defer { try? source.close() }
    let prefix = try source.read(upToCount: 16) ?? Data()
    guard !prefix.isEmpty else { try fail("file_metadata_invalid") }
    if prefix.starts(with: [37, 80, 68, 70, 45]) { return "application/pdf" }
    if prefix.starts(with: [137, 80, 78, 71, 13, 10, 26, 10]) { return "image/png" }
    if prefix.starts(with: [255, 216, 255]) { return "image/jpeg" }
    if prefix.count >= 12, prefix.starts(with: Array("RIFF".utf8)),
      prefix.dropFirst(8).starts(with: Array("WEBP".utf8)) { return "image/webp" }
    try source.seek(toOffset: 0)
    var validator = TextValidator(), measured = 0
    while true {
      try check(scope)
      let data = try source.read(upToCount: Self.chunkBytes) ?? Data()
      if data.isEmpty { break }
      measured += data.count
      guard measured <= Self.maxBytes else { try fail("file_too_large") }
      try validator.append(data)
    }
    guard validator.remaining == 0 else { try fail("file_type_invalid") }
    return "text/plain"
  }

  private func startPick(_ args: [String: Any], _ result: @escaping FlutterResult) throws {
    let scope = try scope(args), max = try integer(args["max_bytes"])
    guard pendingPick == nil, (1...Self.maxBytes).contains(max),
      let values = args["allowed_types"] as? [String], !values.isEmpty,
      Set(values).isSubset(of: Self.mediaTypes) else { try fail("file_metadata_invalid") }
    let types: [UTType] = values.compactMap { value in
      switch value {
      case "application/pdf": return .pdf
      case "image/png": return .png
      case "image/jpeg": return .jpeg
      case "image/webp": return UTType(mimeType: "image/webp")
      case "text/plain": return .plainText
      default: return nil
      }
    }
    guard types.count == values.count, let presenter = registrar.viewController,
      presenter.viewIfLoaded?.window != nil, presenter.presentedViewController == nil else { try fail("private_files_unavailable") }
    let picker = UIDocumentPickerViewController(forOpeningContentTypes: types, asCopy: false)
    picker.allowsMultipleSelection = false
    picker.delegate = self
    pendingPick = PendingPick(scope: scope, mediaTypes: Set(values), maxBytes: max, result: result)
    self.picker = picker
    presenter.present(picker, animated: true)
  }
  func documentPickerWasCancelled(_ controller: UIDocumentPickerViewController) {
    guard withState({ !detached }), picker === controller, let pending = pendingPick else { return }
    pendingPick = nil; picker = nil
    pending.result(nil)
  }
  func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
    guard withState({ !detached }), picker === controller, let pending = pendingPick else { return }
    pendingPick = nil; picker = nil
    guard urls.count == 1, let url = urls.first, url.isFileURL else {
      pending.result(FlutterError(code: "file_metadata_invalid", message: nil, details: nil)); return
    }
    operation(pending.result) { try self.copySelection(pending, url) }
  }
  private func cancelPicker(_ id: String?, notify: Bool = true) {
    guard let pending = pendingPick, id == nil || pending.scope.id == id else { return }
    pendingPick = nil
    picker?.delegate = nil
    picker?.dismiss(animated: false); picker = nil
    if notify {
      pending.result(FlutterError(code: "private_file_cancelled", message: nil, details: nil))
    }
  }
  private func copySelection(_ pending: PendingPick, _ selected: URL) throws -> [String: Any] {
    let scope = pending.scope
    try check(scope)
    try capacity(pending.maxBytes)
    let hasAccess = selected.startAccessingSecurityScopedResource()
    defer { if hasAccess { selected.stopAccessingSecurityScopedResource() } }
    let copyGeneration = scope.beginCopy()
    let coordinator = NSFileCoordinator(filePresenter: nil)
    scope.setSource(nil, coordinator: coordinator)
    let deadline = DispatchWorkItem { scope.cancelCopy(generation: copyGeneration) }
    DispatchQueue.global(qos: .utility).asyncAfter(deadline: .now() + 30, execute: deadline)
    defer { deadline.cancel(); scope.finishCopy(copyGeneration) }
    var coordinationError: NSError?, copyError: Error?, completed: Entry?
    coordinator.coordinate(readingItemAt: selected, options: [], error: &coordinationError) { url in
      do {
        try self.check(scope)
        guard !scope.copyingCancelled else { try self.fail("private_file_cancelled") }
        let values = try url.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey, .fileSizeKey])
        guard values.isRegularFile == true, values.isSymbolicLink != true else { try self.fail("file_metadata_invalid") }
        if let reported = values.fileSize, reported > pending.maxBytes { try self.fail("file_too_large") }
        guard let input = InputStream(url: url) else { try self.fail("private_files_unavailable") }
        scope.setSource(input, coordinator: coordinator)
        input.open()
        defer { input.close() }
        let id = UUID().uuidString.lowercased()
        let (target, output) = try self.newFile(scope, id)
        var entry: Entry?, committed = false
        defer {
          try? output.close()
          if !committed {
            do {
              let remaining = try self.owned(scope, entry?.url ?? target)
              if FileManager.default.fileExists(atPath: remaining.path) { try FileManager.default.removeItem(at: remaining) }
            } catch { self.withState { self.broken = true } }
          }
        }
        var hasher = SHA256(), size = 0
        let buffer = UnsafeMutablePointer<UInt8>.allocate(capacity: Self.chunkBytes)
        defer { buffer.deallocate() }
        while true {
          try self.check(scope)
          guard !scope.copyingCancelled else { try self.fail("private_file_cancelled") }
          let count = input.read(buffer, maxLength: min(Self.chunkBytes, pending.maxBytes - size + 1))
          guard count >= 0 else { try self.fail("private_files_unavailable") }
          if count == 0 { break }
          size += count
          guard size <= pending.maxBytes else { try self.fail("file_too_large") }
          let bytes = Data(bytes: buffer, count: count)
          try output.write(contentsOf: bytes)
          hasher.update(data: bytes)
        }
        try output.close()
        guard !scope.copyingCancelled else { try self.fail("private_file_cancelled") }
        guard size > 0 else { try self.fail("file_metadata_invalid") }
        let type = try self.detect(scope, target)
        guard pending.mediaTypes.contains(type) else { try self.fail("file_type_invalid") }
        let snapshot = Entry(id: id, url: target, mediaType: type, byteSize: size, sha256: self.digest(hasher.finalize()))
        entry = snapshot
        try self.complete(scope, snapshot)
        try self.check(scope)
        scope.entries[id] = snapshot
        committed = true; completed = snapshot
      } catch { copyError = error }
    }
    do {
      if let copyError { throw copyError }
      guard !scope.copyingCancelled else { try fail("private_file_cancelled") }
      guard coordinationError == nil, let completed else { try fail("private_files_unavailable") }
      try check(scope)
      return completed.descriptor
    } catch {
      if let completed {
        try dispose(scope, completed)
        scope.entries.removeValue(forKey: completed.id)
      }
      throw error
    }
  }

  private func dispose(_ scope: Scope, _ entry: Entry) throws {
    do {
      try entry.output?.close(); entry.output = nil
      let file = try owned(scope, entry.url)
      if FileManager.default.fileExists(atPath: file.path) { try FileManager.default.removeItem(at: file) }
    } catch { withState { broken = true }; throw error }
  }
  private func cleanDirectory(_ directory: URL) throws {
    try validate(directory, parent: root, directory: true)
    let children = try FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
    guard children.count <= 32 else { try fail("private_files_unavailable") }
    for child in children {
      guard child.lastPathComponent.range(of: Self.childPattern, options: .regularExpression) != nil else { try fail("private_files_unavailable") }
      try validate(child, parent: directory, directory: false)
      try FileManager.default.removeItem(at: child)
    }
    // This directory is empty and has been validated; no recursive caller-target deletion.
    guard Darwin.rmdir(directory.path) == 0 else { try fail("private_files_unavailable") }
  }
  private func removeScope(_ scope: Scope) throws {
    do {
      for entry in scope.entries.values { try dispose(scope, entry) }
      scope.entries.removeAll()
      try cleanDirectory(scope.directory)
      withState { scopes.removeValue(forKey: scope.id) }
    } catch { withState { broken = true }; throw error }
  }
}
