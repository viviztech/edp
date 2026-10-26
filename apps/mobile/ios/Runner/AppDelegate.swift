import Flutter
import UIKit
import AVFoundation

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  private var externalLinks: FlutterMethodChannel?
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
    if let links = engineBridge.pluginRegistry.registrar(forPlugin: "ExternalLinks") {
      let channel = FlutterMethodChannel(name: "edp/external_links", binaryMessenger: links.messenger())
      externalLinks = channel
      channel.setMethodCallHandler { call, result in
        guard call.method == "open" else { result(FlutterMethodNotImplemented); return }
        guard let args = call.arguments as? [String: Any], let raw = args["url"] as? String,
          raw.count <= 2048, !raw.contains("\\"),
          !raw.unicodeScalars.contains(where: { $0.value <= 32 || $0.value == 127 }),
          let url = URL(string: raw), ["https", "http"].contains(url.scheme ?? ""),
          url.host?.isEmpty == false, url.user == nil, url.password == nil else { result(false); return }
        UIApplication.shared.open(url, options: [:]) { opened in result(opened) }
      }
    }
    if let registrar = engineBridge.pluginRegistry.registrar(forPlugin: "PrivateFilesBridge") {
      PrivateFilesBridge.register(with: registrar)
    }
    if let registrar = engineBridge.pluginRegistry.registrar(forPlugin: "AttendanceScannerBridge") {
      AttendanceScannerBridge.register(with: registrar)
    }
  }
}

/// A narrow native camera boundary: no images, URLs or diagnostics leave it.
final class AttendanceScannerBridge: NSObject, FlutterPlugin {
  private let registrar: FlutterPluginRegistrar
  private var pending = false
  private init(registrar: FlutterPluginRegistrar) { self.registrar = registrar }
  static func register(with registrar: FlutterPluginRegistrar) {
    let bridge = AttendanceScannerBridge(registrar: registrar)
    let channel = FlutterMethodChannel(name: "edp/attendance_scanner", binaryMessenger: registrar.messenger())
    registrar.addMethodCallDelegate(bridge, channel: channel)
  }
  func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
    guard call.method == "scan" else { result(FlutterMethodNotImplemented); return }
    guard !pending, let presenter = registrar.viewController,
      presenter.viewIfLoaded?.window != nil, presenter.presentedViewController == nil,
      let args = call.arguments as? [String: Any],
      let instruction = args["instruction"] as? String, instruction.count <= 2000,
      let cancel = args["cancel"] as? String, cancel.count <= 100 else {
      result(FlutterError(code: "unavailable", message: "Scanner unavailable", details: nil)); return
    }
    pending = true
    AVCaptureDevice.requestAccess(for: .video) { [weak self, weak presenter] granted in
      DispatchQueue.main.async {
        guard let self else { result(FlutterError(code: "unavailable", message: "Scanner closed", details: nil)); return }
        guard granted else { self.pending = false; result(FlutterError(code: "denied", message: "Camera unavailable", details: nil)); return }
        guard let presenter, presenter.viewIfLoaded?.window != nil,
          presenter.presentedViewController == nil else {
          self.pending = false; result(FlutterError(code: "unavailable", message: "Scanner unavailable", details: nil)); return
        }
        let scanner = AttendanceCameraController(instruction: instruction, cancel: cancel) { [weak self] value, error in
          self?.pending = false
          if let error { result(FlutterError(code: error, message: "Scanner unavailable", details: nil)) }
          else { result(value) }
        }
        let navigation = UINavigationController(rootViewController: scanner)
        navigation.modalPresentationStyle = .fullScreen
        presenter.present(navigation, animated: true)
      }
    }
  }
}

private final class AttendanceCameraController: UIViewController, AVCaptureMetadataOutputObjectsDelegate {
  private let capture = AVCaptureSession()
  private let queue = DispatchQueue(label: "edp.attendance.camera")
  private var preview: AVCaptureVideoPreviewLayer?
  private var completion: ((String?, String?) -> Void)?
  private let instruction: String, cancelLabel: String
  init(instruction: String, cancel: String, completion: @escaping (String?, String?) -> Void) {
    self.instruction = instruction; self.cancelLabel = cancel; self.completion = completion
    super.init(nibName: nil, bundle: nil)
  }
  required init?(coder: NSCoder) { return nil }
  override func viewDidLoad() {
    super.viewDidLoad()
    view.backgroundColor = .black
    navigationItem.leftBarButtonItem = UIBarButtonItem(title: cancelLabel, style: .plain, target: self, action: #selector(cancelScan))
    let label = UILabel()
    label.text = instruction; label.numberOfLines = 0; label.textColor = .white
    label.font = .preferredFont(forTextStyle: .body); label.adjustsFontForContentSizeCategory = true
    label.translatesAutoresizingMaskIntoConstraints = false
    view.addSubview(label)
    NSLayoutConstraint.activate([
      label.leadingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.leadingAnchor, constant: 20),
      label.trailingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.trailingAnchor, constant: -20),
      label.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -24)
    ])
    NotificationCenter.default.addObserver(self, selector: #selector(cancelScan), name: UIApplication.didEnterBackgroundNotification, object: nil)
    let layer = AVCaptureVideoPreviewLayer(session: capture)
    layer.videoGravity = .resizeAspectFill; view.layer.insertSublayer(layer, at: 0); preview = layer
    queue.async { [weak self] in self?.configure() }
  }
  private func configure() {
    do {
      guard let camera = AVCaptureDevice.default(for: .video) else { fail(); return }
      let input = try AVCaptureDeviceInput(device: camera), output = AVCaptureMetadataOutput()
      capture.beginConfiguration()
      guard capture.canAddInput(input), capture.canAddOutput(output) else { capture.commitConfiguration(); fail(); return }
      capture.addInput(input); capture.addOutput(output)
      output.setMetadataObjectsDelegate(self, queue: .main)
      guard output.availableMetadataObjectTypes.contains(.qr) else { capture.commitConfiguration(); fail(); return }
      output.metadataObjectTypes = [.qr]
      capture.commitConfiguration(); capture.startRunning()
    } catch { fail() }
  }
  private func fail() { DispatchQueue.main.async { [weak self] in self?.finish(nil, error: "unavailable") } }
  override func viewDidLayoutSubviews() { super.viewDidLayoutSubviews(); preview?.frame = view.bounds }
  override func viewDidDisappear(_ animated: Bool) {
    super.viewDidDisappear(animated)
    queue.async { [capture] in if capture.isRunning { capture.stopRunning() } }
    if completion != nil { finish(nil) }
  }
  deinit { NotificationCenter.default.removeObserver(self) }
  @objc private func cancelScan() { finish(nil) }
  private func finish(_ value: String?, error: String? = nil) {
    guard let reply = completion else { return }
    completion = nil
    queue.async { [capture] in if capture.isRunning { capture.stopRunning() } }
    dismiss(animated: true) { reply(value, error) }
  }
  func metadataOutput(_ output: AVCaptureMetadataOutput, didOutput metadataObjects: [AVMetadataObject], from connection: AVCaptureConnection) {
    guard let value = (metadataObjects.first as? AVMetadataMachineReadableCodeObject)?.stringValue else { return }
    guard value.range(of: "^edp-attendance:[A-Za-z0-9_-]{32,128}$", options: .regularExpression) != nil else {
      finish(nil, error: "invalid_payload"); return
    }
    finish(value)
  }
}
