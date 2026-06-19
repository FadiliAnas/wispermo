import AppKit

/// A small live waveform pill at the bottom-centre of the screen (Wispr-Flow
/// style): scrolling bars driven by the mic level while recording, a subtle
/// shimmer while transcribing — no text. Non-activating, click-through.
@MainActor
final class RecordingOverlay {
    private let panel: NSPanel
    private let wave: WaveView

    init() {
        let w: CGFloat = 120, h: CGFloat = 30
        wave = WaveView(frame: NSRect(x: 0, y: 0, width: w, height: h))
        panel = NSPanel(contentRect: NSRect(x: 0, y: 0, width: w, height: h),
                        styleMask: [.borderless, .nonactivatingPanel],
                        backing: .buffered, defer: false)
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.hasShadow = true
        panel.level = .floating
        panel.collectionBehavior = [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary]
        panel.ignoresMouseEvents = true
        panel.hidesOnDeactivate = false
        panel.contentView = wave
    }

    private func reposition() {
        guard let s = NSScreen.main else { return }
        let f = s.visibleFrame
        panel.setFrameOrigin(NSPoint(x: f.midX - panel.frame.width / 2, y: f.minY + 72))
    }

    func showRecording() {
        reposition(); wave.mode = .recording; wave.reset(); wave.start()
        panel.orderFrontRegardless()
    }
    func showTranscribing() { wave.mode = .transcribing }
    func hide() { wave.stop(); panel.orderOut(nil) }
    func setLevel(_ l: Float) { wave.level = l }
}

final class WaveView: NSView {
    enum Mode { case recording, transcribing }
    var mode: Mode = .recording
    var level: Float = 0
    private let n = 16
    private var bars: [CGFloat] = []
    private var timer: Timer?
    private var phase: CGFloat = 0

    override init(frame: NSRect) {
        bars = Array(repeating: 0.06, count: n)
        super.init(frame: frame)
    }
    required init?(coder: NSCoder) { fatalError() }

    func reset() { bars = Array(repeating: 0.06, count: n); level = 0 }
    func start() {
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 1.0 / 30, repeats: true) { [weak self] _ in
            self?.tick()
        }
    }
    func stop() { timer?.invalidate(); timer = nil }

    private func tick() {
        phase += 0.18
        if mode == .recording {
            var edge = bars.last ?? 0.06
            edge += (CGFloat(level) - edge) * 0.5
            bars.removeFirst()
            bars.append(max(0.06, min(1, edge)))
            level *= 0.85
        }
        needsDisplay = true
    }

    override func draw(_ dirtyRect: NSRect) {
        let r = bounds.insetBy(dx: 2, dy: 2)
        NSColor(white: 0.08, alpha: 0.95).setFill()
        NSBezierPath(roundedRect: r, xRadius: r.height / 2, yRadius: r.height / 2).fill()

        let paper = NSColor(white: 0.97, alpha: 1)
        let cy = r.midY
        if mode == .recording {
            paper.setFill()
            NSBezierPath(ovalIn: NSRect(x: r.minX + 9, y: cy - 2.5, width: 5, height: 5)).fill()
        }
        let x0 = r.minX + 22, x1 = r.maxX - 12
        let bw = (x1 - x0) / CGFloat(n)
        for i in 0..<n {
            let h: CGFloat
            if mode == .recording {
                h = 3 + bars[i] * (r.height - 9)
            } else {
                h = 3 + (0.5 + 0.5 * sin(phase * 1.8 - CGFloat(i) * 0.55)) * (r.height - 13)
            }
            let x = x0 + CGFloat(i) * bw
            paper.setFill()
            NSBezierPath(roundedRect: NSRect(x: x, y: cy - h / 2, width: bw * 0.5, height: h),
                         xRadius: 1.4, yRadius: 1.4).fill()
        }
    }
}
