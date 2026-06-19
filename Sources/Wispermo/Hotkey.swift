import AppKit

/// Global hotkey detection on the MAIN run loop via NSEvent monitors — no
/// background CGEventTap, no separate CFRunLoop, no bridge. This is what makes
/// the Fn key reliable. Needs Input Monitoring permission.
final class HotkeyMonitor {
    enum Trigger: Equatable {
        case fn                                   // the 🌐 / Globe key
        case key(CGKeyCode, NSEvent.ModifierFlags)
    }

    var onPress: () -> Void = {}
    var onRelease: () -> Void = {}

    private var trigger: Trigger
    private var globalMon: Any?
    private var localMon: Any?
    private var fnDown = false
    private var keyHeld = false

    init(trigger: Trigger) { self.trigger = trigger }

    func setTrigger(_ t: Trigger) {
        trigger = t; fnDown = false; keyHeld = false
    }

    func start() {
        let mask: NSEvent.EventTypeMask = [.flagsChanged, .keyDown, .keyUp]
        globalMon = NSEvent.addGlobalMonitorForEvents(matching: mask) { [weak self] e in
            self?.handle(e)
        }
        // local monitor covers the case where one of our own windows is focused
        localMon = NSEvent.addLocalMonitorForEvents(matching: mask) { [weak self] e in
            self?.handle(e); return e
        }
    }

    func stop() {
        if let g = globalMon { NSEvent.removeMonitor(g); globalMon = nil }
        if let l = localMon { NSEvent.removeMonitor(l); localMon = nil }
    }

    private func handle(_ e: NSEvent) {
        switch trigger {
        case .fn:
            guard e.type == .flagsChanged else { return }
            let isDown = e.modifierFlags.contains(.function)
            if isDown, !fnDown { fnDown = true; onPress() }
            else if !isDown, fnDown { fnDown = false; onRelease() }

        case .key(let code, let mods):
            let want = mods.intersection(.deviceIndependentFlagsMask)
            let have = e.modifierFlags.intersection(.deviceIndependentFlagsMask)
            if e.type == .keyDown, e.keyCode == code, have.isSuperset(of: want), !keyHeld {
                keyHeld = true; onPress()
            } else if e.type == .keyUp, e.keyCode == code, keyHeld {
                keyHeld = false; onRelease()
            }
        }
    }
}
