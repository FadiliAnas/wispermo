import AppKit

/// Always-on-top, draggable mic button. A non-activating panel so a click
/// toggles dictation without stealing focus from your text field; visible on
/// every Space and over full-screen apps.
@MainActor
final class FloatingButton {
    private let panel: NSPanel
    private let view: FloatingButtonView

    init(onClick: @escaping () -> Void) {
        let size: CGFloat = 56
        view = FloatingButtonView(frame: NSRect(x: 0, y: 0, width: size, height: size))
        view.onClick = onClick
        panel = NSPanel(contentRect: NSRect(x: 0, y: 0, width: size, height: size),
                        styleMask: [.borderless, .nonactivatingPanel],
                        backing: .buffered, defer: false)
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.hasShadow = true
        panel.isFloatingPanel = true
        panel.level = .floating
        panel.collectionBehavior = [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary]
        panel.isMovableByWindowBackground = true
        panel.contentView = view
        panel.hidesOnDeactivate = false
        if let screen = NSScreen.main {
            let f = screen.visibleFrame
            panel.setFrameOrigin(NSPoint(x: f.minX + 24, y: f.midY - size / 2))
        }
    }

    func show() { panel.orderFrontRegardless() }
    func hide() { panel.orderOut(nil) }
    func setRecording(_ r: Bool) { view.recording = r; view.needsDisplay = true }
}

final class FloatingButtonView: NSView {
    var onClick: () -> Void = {}
    var recording = false
    private var press: NSPoint?
    private var dragged = false

    override var isFlipped: Bool { false }

    override func draw(_ dirtyRect: NSRect) {
        let r = bounds.insetBy(dx: 4, dy: 4)
        NSColor(srgbRed: 0.106, green: 0.102, blue: 0.090, alpha: 1).setFill()
        NSBezierPath(ovalIn: r).fill()

        let symbol = recording ? "stop.fill" : "mic.fill"
        guard let base = NSImage(systemSymbolName: symbol, accessibilityDescription: nil) else { return }
        let cfg = NSImage.SymbolConfiguration(pointSize: 22, weight: .medium)
        let img = (base.withSymbolConfiguration(cfg) ?? base)
        guard let tinted = img.copy() as? NSImage else { return }
        tinted.isTemplate = false
        tinted.lockFocus()
        NSColor(srgbRed: 0.98, green: 0.98, blue: 0.972, alpha: 1).set()
        NSRect(origin: .zero, size: tinted.size).fill(using: .sourceAtop)
        tinted.unlockFocus()
        let s = tinted.size
        tinted.draw(in: NSRect(x: bounds.midX - s.width / 2, y: bounds.midY - s.height / 2,
                               width: s.width, height: s.height))
    }

    override func mouseDown(with e: NSEvent) { press = e.locationInWindow; dragged = false }
    override func mouseDragged(with e: NSEvent) {
        guard let p = press else { return }
        if hypot(e.locationInWindow.x - p.x, e.locationInWindow.y - p.y) > 4 {
            dragged = true
            window?.performDrag(with: e)
        }
    }
    override func mouseUp(with e: NSEvent) {
        if !dragged { onClick() }
        press = nil
    }
    override func resetCursorRects() { addCursorRect(bounds, cursor: .pointingHand) }
}
