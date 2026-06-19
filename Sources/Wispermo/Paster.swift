import AppKit
import CoreGraphics

/// Inserts text into the focused app. Native CGEvent injection — no AppleScript,
/// no pyobjc; thread-safe; needs Accessibility.
enum Paster {
    private static let vkCommand: CGKeyCode = 0x37
    private static let vkV: CGKeyCode = 0x09

    static func copyToClipboard(_ text: String) {
        let pb = NSPasteboard.general
        pb.clearContents()
        pb.setString(text, forType: .string)
    }

    enum Mode { case paste, type, clipboard }

    /// Returns a short status; `pasted`/`typed`/`copied`, or `needsAccessibility`.
    @discardableResult
    static func deliver(_ text: String, mode: Mode, typeDelayMs: Int = 6) -> String {
        guard !text.isEmpty else { return "empty" }

        if mode == .clipboard {
            copyToClipboard(text)
            return "copied"
        }
        guard Permissions.accessibilityTrusted else {
            copyToClipboard(text)            // still leave it on the clipboard
            return "needsAccessibility"
        }
        if mode == .type {
            typeUnicode(text, delay: max(0, typeDelayMs))
            return "typed"
        }
        // paste
        copyToClipboard(text)
        usleep(120_000)                      // let the pasteboard settle
        pasteCommandV()
        return "pasted"
    }

    /// A real ⌘V: Cmd down, V down (⌘), V up (⌘), Cmd up — posted at HID level.
    static func pasteCommandV() {
        let src = CGEventSource(stateID: .privateState) ?? CGEventSource(stateID: .hidSystemState)
        let down: (CGKeyCode, Bool, CGEventFlags) -> Void = { key, isDown, flags in
            if let e = CGEvent(keyboardEventSource: src, virtualKey: key, keyDown: isDown) {
                e.flags = flags
                e.post(tap: .cghidEventTap)
            }
            usleep(12_000)
        }
        down(vkCommand, true, .maskCommand)
        down(vkV, true, .maskCommand)
        down(vkV, false, .maskCommand)
        down(vkCommand, false, [])
    }

    /// Types arbitrary text as Unicode keyboard events (no keycode mapping).
    static func typeUnicode(_ text: String, delay: Int) {
        let src = CGEventSource(stateID: .privateState) ?? CGEventSource(stateID: .hidSystemState)
        for ch in text {
            let utf16 = Array(String(ch).utf16)
            for isDown in [true, false] {
                if let e = CGEvent(keyboardEventSource: src, virtualKey: 0, keyDown: isDown) {
                    e.keyboardSetUnicodeString(stringLength: utf16.count, unicodeString: utf16)
                    e.post(tap: .cghidEventTap)
                }
            }
            if delay > 0 { usleep(UInt32(delay) * 1000) }
        }
    }
}
