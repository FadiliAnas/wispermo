import Foundation
import WhisperKit

/// On-device Whisper transcription via WhisperKit (CoreML / Neural Engine).
/// The model is downloaded once on first load and cached.
actor Transcriber {
    private var whisper: WhisperKit?
    private(set) var ready = false

    func load(model: String = "base",
              onProgress: @Sendable @escaping (Double) -> Void = { _ in }) async throws {
        // 1. Bundled model (plug-and-play): the default model + tokenizer ship
        //    inside the .app, so the standard experience needs NO download.
        if let assets = Bundle.main.resourceURL?.appendingPathComponent("WhisperKitAssets") {
            let mf = assets.appendingPathComponent(
                "models/argmaxinc/whisperkit-coreml/openai_whisper-\(model)")
            let tf = assets.appendingPathComponent("models/openai/whisper-\(model)")
            if FileManager.default.fileExists(atPath: mf.path) {
                let config = WhisperKitConfig(model: model, modelFolder: mf.path,
                                              tokenizerFolder: tf, download: false)
                whisper = try await WhisperKit(config)
                onProgress(1); ready = true
                return
            }
        }
        // 2. Fallback: a model the user picked that isn't bundled — download it
        //    (with progress), then init from the local folder.
        let folder = try await WhisperKit.download(variant: model, progressCallback: { p in
            onProgress(p.fractionCompleted)
        })
        let config = WhisperKitConfig(model: model, modelFolder: folder.path)
        whisper = try await WhisperKit(config)
        ready = true
    }

    func transcribe(_ audio: [Float], language: String?) async throws -> String {
        guard let whisper else {
            throw NSError(domain: "Wispermo", code: 10,
                          userInfo: [NSLocalizedDescriptionKey: "Speech model not loaded yet"])
        }
        guard audio.count > 1600 else { return "" }   // < 0.1s -> nothing said
        var options = DecodingOptions()
        if let language, !language.isEmpty { options.language = language }
        let results = try await whisper.transcribe(audioArray: audio, decodeOptions: options)
        return results.map(\.text).joined(separator: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
