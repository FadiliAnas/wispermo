import Foundation
import WhisperKit

// Two modes:
//   FetchModel <variant> <outDir>            — download model+tokenizer into outDir
//   FetchModel verify <assetsDir> <variant>  — load OFFLINE from a bundled assets
//                                              dir (download:false) + transcribe
func err(_ s: String) { FileHandle.standardError.write((s + "\n").data(using: .utf8)!) }

let args = CommandLine.arguments
let sema = DispatchSemaphore(value: 0)

if args.count > 1, args[1] == "verify" {
    let assets = URL(fileURLWithPath: args[2])
    let m = args.count > 3 ? args[3] : "base"
    let mf = assets.appendingPathComponent("models/argmaxinc/whisperkit-coreml/openai_whisper-\(m)")
    let tf = assets.appendingPathComponent("models/openai/whisper-\(m)")
    Task {
        do {
            let config = WhisperKitConfig(model: m, modelFolder: mf.path,
                                          tokenizerFolder: tf, download: false)
            let wk = try await WhisperKit(config)
            let silence = [Float](repeating: 0, count: 16_000)   // 1s
            let res = try await wk.transcribe(audioArray: silence)
            err("VERIFY OK: loaded OFFLINE + transcribed (\(res.count) segment(s))")
        } catch {
            err("VERIFY FAIL: \(error)")
            exit(1)
        }
        sema.signal()
    }
    sema.wait()
} else {
    let variant = args.count > 1 ? args[1] : "base"
    let outDir = URL(fileURLWithPath: args.count > 2 ? args[2] : "./wk-assets", isDirectory: true)
    try? FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)
    Task {
        do {
            let config = WhisperKitConfig(model: variant, downloadBase: outDir,
                                          load: true, download: true)
            _ = try await WhisperKit(config)
            err("FetchModel OK: \(variant) -> \(outDir.path)")
        } catch {
            err("FetchModel ERROR: \(error)")
            exit(1)
        }
        sema.signal()
    }
    sema.wait()
}
