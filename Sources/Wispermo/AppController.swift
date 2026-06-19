import AppKit
import SwiftUI
import Combine

@MainActor
final class AppController: NSObject, NSApplicationDelegate {
    private var statusItem: NSStatusItem!
    private var statusInfo: NSMenuItem!
    private var window: NSWindow!
    private let appState = AppState()
    private let config = Config.shared
    private let store = Store.shared

    private let hotkey = HotkeyMonitor(trigger: .fn)
    private let recorder = Recorder()
    private let transcriber = Transcriber()
    private var floating: FloatingButton?
    private let overlay = RecordingOverlay()
    private var permTimer: Timer?
    private var cancellables = Set<AnyCancellable>()

    private enum State { case loading, idle, recording, transcribing }
    private var state: State = .loading
    private var recordingStart = Date()
    private var loadedModel = ""
    private var currentTrigger: HotkeyMonitor.Trigger = .fn

    func applicationDidFinishLaunching(_ notification: Notification) {
        if let p = Bundle.main.path(forResource: "AppIcon", ofType: "icns"),
           let icon = NSImage(contentsOfFile: p) {
            NSApp.applicationIconImage = icon
        }
        setupStatusItem()
        setupWindow()
        recorder.onLevel = { [weak self] in
            self?.appState.level = $0; self?.overlay.setLevel($0)
        }
        appState.onToggle = { [weak self] in self?.toggle() }
        appState.onOpenPane = { Permissions.openSettings($0) }
        hotkey.onPress = { [weak self] in self?.hotkeyPress() }
        hotkey.onRelease = { [weak self] in self?.hotkeyRelease() }
        hotkey.start()
        applyConfig()
        config.objectWillChange.sink { [weak self] in
            DispatchQueue.main.async { self?.applyConfig() }
        }.store(in: &cancellables)
        requestPermissions()
        startPermissionPolling()
        Task { await loadModel() }
    }

    func applicationShouldHandleReopen(_ s: NSApplication, hasVisibleWindows: Bool) -> Bool {
        showWindow(); return true
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ s: NSApplication) -> Bool { false }

    // MARK: - config
    private func applyConfig() {
        let desired: HotkeyMonitor.Trigger = config.useFn
            ? .fn : .key(CGKeyCode(config.hotkeyKeyCode), [])
        if desired != currentTrigger {
            currentTrigger = desired
            hotkey.setTrigger(desired)
        }
        if config.showFloatingButton, floating == nil {
            floating = FloatingButton { [weak self] in self?.toggle() }
            floating?.show()
            floating?.setRecording(state == .recording)
        } else if !config.showFloatingButton, floating != nil {
            floating?.hide(); floating = nil
        }
        if !loadedModel.isEmpty, config.model != loadedModel {
            Task { await loadModel() }
        }
    }

    // MARK: - window
    private func setupWindow() {
        let hosting = NSHostingController(rootView: RootView(state: appState))
        window = NSWindow(contentViewController: hosting)
        window.title = "Wispermo"
        window.styleMask = [.titled, .closable, .miniaturizable, .resizable]
        window.titlebarAppearsTransparent = true
        window.titleVisibility = .hidden
        window.backgroundColor = NSColor(srgbRed: 0.953, green: 0.945, blue: 0.925, alpha: 1)
        window.isReleasedWhenClosed = false
        window.setContentSize(NSSize(width: 940, height: 640))
        window.center()
        showWindow()
    }
    private func showWindow() {
        window.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true)
    }

    // MARK: - menu bar
    private func setupStatusItem() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        updateStatusIcon()
        let menu = NSMenu()
        statusInfo = NSMenuItem(title: "Loading model…", action: nil, keyEquivalent: "")
        menu.addItem(statusInfo); menu.addItem(.separator())
        addItem(menu, "Open Wispermo", #selector(showWindowAction))
        addItem(menu, "Start / stop dictation", #selector(toggleAction))
        menu.addItem(.separator())
        addItem(menu, "Quit Wispermo", #selector(quit), key: "q")
        statusItem.menu = menu
    }
    private func addItem(_ menu: NSMenu, _ title: String, _ action: Selector, key: String = "") {
        let it = NSMenuItem(title: title, action: action, keyEquivalent: key)
        it.target = self; menu.addItem(it)
    }
    private lazy var menuBarIcon = BrandImage.menuBar()
    private func updateStatusIcon() {
        // always the WISPERMO logo (a black template) — never a microphone
        statusItem.button?.image = menuBarIcon
    }
    private func setState(_ s: State) {
        state = s
        updateStatusIcon()
        floating?.setRecording(s == .recording)
        switch s {
        case .recording: overlay.showRecording()
        case .transcribing: overlay.showTranscribing()
        case .idle, .loading: overlay.hide()
        }
        let (kind, text): (AppState.Kind, String)
        switch s {
        case .loading: (kind, text) = (.loading, "Loading speech model…")
        case .idle: (kind, text) = (.idle, "Ready")
        case .recording: (kind, text) = (.recording, "Listening…")
        case .transcribing: (kind, text) = (.transcribing, "Transcribing…")
        }
        appState.kind = kind; appState.status = text; statusInfo?.title = text
    }

    // MARK: - hotkey
    private func hotkeyPress() { config.hotkeyMode == "ptt" ? startRecording() : toggle() }
    private func hotkeyRelease() { if config.hotkeyMode == "ptt" { stopAndTranscribe() } }
    private func toggle() {
        if state == .recording { stopAndTranscribe() }
        else if state == .idle { startRecording() }
    }

    // MARK: - record + transcribe
    private func startRecording() {
        guard state == .idle else { return }
        do { try recorder.start(); recordingStart = Date(); setState(.recording) }
        catch { notify("Could not record", error.localizedDescription) }
    }
    private func stopAndTranscribe() {
        guard state == .recording else { return }
        let audio = recorder.stop()
        let secs = Double(audio.count) / 16000.0
        setState(.transcribing)
        let lang = config.language.isEmpty ? nil : config.language
        Task {
            do {
                let raw = try await transcriber.transcribe(audio, language: lang)
                self.finish(raw, seconds: secs)
            } catch {
                self.notify("Transcription failed", error.localizedDescription)
                self.setState(.idle)
            }
        }
    }
    private func finish(_ raw: String, seconds: Double) {
        var text = Formatting.process(raw, config: config)   // dictionary, fillers, tidy
        if config.smartFormat { text = SmartFormat.format(text) }   // lists / bullets / email
        if config.trailingSpace, !text.isEmpty, !text.contains("\n") { text += " " }
        if !text.isEmpty {
            appState.lastText = text.trimmingCharacters(in: .whitespacesAndNewlines)
            store.add(text: appState.lastText, lang: config.language, seconds: seconds)
            let mode: Paster.Mode = config.output == "type" ? .type :
                (config.output == "clipboard" ? .clipboard : .paste)
            let status = Paster.deliver(text, mode: mode, typeDelayMs: config.typeDelayMs)
            if status == "needsAccessibility" {
                notify("Text on clipboard", "Grant Accessibility to auto-paste (⌘V for now).")
            }
        }
        setState(.idle)
    }

    // MARK: - model
    private func loadModel() async {
        let want = config.model
        appState.modelProgress = 0
        do {
            try await transcriber.load(model: want, onProgress: { [weak self] frac in
                Task { @MainActor in self?.onDownloadProgress(frac) }
            })
            loadedModel = want
            appState.modelProgress = 1
            if state == .loading { setState(.idle) }
        } catch {
            appState.modelProgress = 1
            notify("Model load failed", error.localizedDescription)
        }
    }

    private func onDownloadProgress(_ frac: Double) {
        appState.modelProgress = frac
        if state == .loading {
            let pct = Int((frac * 100).rounded())
            let text = frac < 1 ? "Downloading speech model… \(pct)%" : "Preparing model…"
            appState.status = text
            statusInfo?.title = text
        }
    }

    // MARK: - permissions
    private func requestPermissions() {
        Permissions.requestAccessibility()
        Permissions.requestInputMonitoring()
        Permissions.requestMicrophone { [weak self] _ in self?.refreshPermissions() }
    }
    private func startPermissionPolling() {
        refreshPermissions()
        permTimer = Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { [weak self] _ in
            MainActor.assumeIsolated { self?.refreshPermissions() }
        }
    }
    private func refreshPermissions() {
        appState.micGranted = Permissions.microphoneGranted
        appState.accessibilityGranted = Permissions.accessibilityTrusted
        appState.inputMonitoringGranted = Permissions.inputMonitoringGranted
    }

    // MARK: - actions
    @objc private func showWindowAction() { showWindow() }
    @objc private func toggleAction() { toggle() }
    @objc private func quit() { hotkey.stop(); NSApp.terminate(nil) }
    private func notify(_ title: String, _ body: String) {
        statusInfo?.toolTip = "\(title): \(body)"; NSLog("Wispermo: %@ — %@", title, body)
    }
}
