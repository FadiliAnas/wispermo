import AVFoundation

/// Captures the microphone and returns 16 kHz mono Float samples for WhisperKit.
final class Recorder {
    private let engine = AVAudioEngine()
    private var converter: AVAudioConverter?
    private var samples: [Float] = []
    private let targetRate: Double = 16_000
    private(set) var isRecording = false

    /// Live input level 0…1 (for a meter), called on the main queue.
    var onLevel: ((Float) -> Void)?

    func start() throws {
        guard !isRecording else { return }
        samples.removeAll(keepingCapacity: true)

        let input = engine.inputNode
        let inFormat = input.inputFormat(forBus: 0)
        guard inFormat.sampleRate > 0 else {
            throw NSError(domain: "Wispermo", code: 1,
                          userInfo: [NSLocalizedDescriptionKey: "No microphone input available"])
        }
        guard let outFormat = AVAudioFormat(commonFormat: .pcmFormatFloat32,
                                            sampleRate: targetRate, channels: 1,
                                            interleaved: false) else {
            throw NSError(domain: "Wispermo", code: 2)
        }
        converter = AVAudioConverter(from: inFormat, to: outFormat)

        input.installTap(onBus: 0, bufferSize: 2048, format: inFormat) { [weak self] buffer, _ in
            self?.append(buffer, outFormat: outFormat)
        }
        engine.prepare()
        try engine.start()
        isRecording = true
    }

    /// Stops and returns the captured 16 kHz mono samples.
    @discardableResult
    func stop() -> [Float] {
        guard isRecording else { return [] }
        engine.inputNode.removeTap(onBus: 0)
        engine.stop()
        isRecording = false
        let out = samples
        samples.removeAll(keepingCapacity: false)
        return out
    }

    private func append(_ buffer: AVAudioPCMBuffer, outFormat: AVAudioFormat) {
        guard let converter else { return }
        let ratio = outFormat.sampleRate / buffer.format.sampleRate
        let capacity = AVAudioFrameCount(Double(buffer.frameLength) * ratio) + 16
        guard let outBuf = AVAudioPCMBuffer(pcmFormat: outFormat, frameCapacity: capacity) else { return }

        var consumed = false
        var error: NSError?
        converter.convert(to: outBuf, error: &error) { _, status in
            if consumed { status.pointee = .noDataNow; return nil }
            consumed = true
            status.pointee = .haveData
            return buffer
        }
        guard error == nil, let ch = outBuf.floatChannelData else { return }
        let n = Int(outBuf.frameLength)
        let ptr = ch[0]
        var rms: Float = 0
        samples.reserveCapacity(samples.count + n)
        for i in 0..<n {
            let s = ptr[i]
            samples.append(s)
            rms += s * s
        }
        if n > 0, let onLevel {
            let level = min(1.0, (rms / Float(n)).squareRoot() * 4)
            DispatchQueue.main.async { onLevel(level) }
        }
    }
}
