import AVFoundation
import ApplicationServices
import AppKit
import IOKit.hid

/// macOS permission checks + prompts. Native APIs (no pyobjc bridge).
enum Permissions {

    // MARK: Accessibility (needed to inject ⌘V / keystrokes)
    static var accessibilityTrusted: Bool {
        AXIsProcessTrusted()
    }

    @discardableResult
    static func requestAccessibility() -> Bool {
        // kAXTrustedCheckOptionPrompt == "AXTrustedCheckOptionPrompt"; use the
        // literal to avoid CFString/Unmanaged import differences across SDKs.
        let opts = ["AXTrustedCheckOptionPrompt": true] as CFDictionary
        return AXIsProcessTrustedWithOptions(opts)
    }

    // MARK: Input Monitoring (needed for the global hotkey / Fn)
    static var inputMonitoringGranted: Bool {
        IOHIDCheckAccess(kIOHIDRequestTypeListenEvent) == kIOHIDAccessTypeGranted
    }

    @discardableResult
    static func requestInputMonitoring() -> Bool {
        IOHIDRequestAccess(kIOHIDRequestTypeListenEvent)
    }

    // MARK: Microphone
    static var microphoneGranted: Bool {
        AVCaptureDevice.authorizationStatus(for: .audio) == .authorized
    }

    static func requestMicrophone(_ done: @escaping (Bool) -> Void) {
        AVCaptureDevice.requestAccess(for: .audio) { ok in
            DispatchQueue.main.async { done(ok) }
        }
    }

    // MARK: deep links to the exact System Settings panes
    static func openSettings(_ pane: Pane) {
        if let url = URL(string: pane.rawValue) {
            NSWorkspace.shared.open(url)
        }
    }

    enum Pane: String {
        case accessibility = "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
        case inputMonitoring = "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"
        case microphone = "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"
    }
}
