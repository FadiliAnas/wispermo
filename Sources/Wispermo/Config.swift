import Foundation
import Combine

/// Persistent user settings (UserDefaults-backed, observable).
@MainActor
final class Config: ObservableObject {
    static let shared = Config()
    private let d = UserDefaults.standard

    @Published var model: String { didSet { d.set(model, forKey: "model") } }
    @Published var language: String { didSet { d.set(language, forKey: "language") } }
    @Published var output: String { didSet { d.set(output, forKey: "output") } }   // paste/type/clipboard
    @Published var typeDelayMs: Int { didSet { d.set(typeDelayMs, forKey: "typeDelayMs") } }
    @Published var hotkeyMode: String { didSet { d.set(hotkeyMode, forKey: "hotkeyMode") } }  // ptt/toggle
    @Published var useFn: Bool { didSet { d.set(useFn, forKey: "useFn") } }
    @Published var hotkeyKeyCode: Int { didSet { d.set(hotkeyKeyCode, forKey: "hotkeyKeyCode") } }
    @Published var hotkeyLabel: String { didSet { d.set(hotkeyLabel, forKey: "hotkeyLabel") } }
    @Published var trailingSpace: Bool { didSet { d.set(trailingSpace, forKey: "trailingSpace") } }
    @Published var tidyFormatting: Bool { didSet { d.set(tidyFormatting, forKey: "tidyFormatting") } }
    @Published var removeFillers: Bool { didSet { d.set(removeFillers, forKey: "removeFillers") } }
    @Published var smartFormat: Bool { didSet { d.set(smartFormat, forKey: "smartFormat") } }
    @Published var vocabulary: String { didSet { d.set(vocabulary, forKey: "vocabulary") } }
    @Published var showFloatingButton: Bool { didSet { d.set(showFloatingButton, forKey: "showFloatingButton") } }
    @Published var dictionary: [String: String] { didSet { saveDictionary() } }

    private init() {
        model = d.string(forKey: "model") ?? "base"
        language = d.string(forKey: "language") ?? ""
        output = d.string(forKey: "output") ?? "paste"
        typeDelayMs = d.object(forKey: "typeDelayMs") as? Int ?? 6
        hotkeyMode = d.string(forKey: "hotkeyMode") ?? "toggle"
        useFn = d.object(forKey: "useFn") as? Bool ?? true
        hotkeyKeyCode = d.object(forKey: "hotkeyKeyCode") as? Int ?? 98   // F7
        hotkeyLabel = d.string(forKey: "hotkeyLabel") ?? "🌐 Fn"
        trailingSpace = d.object(forKey: "trailingSpace") as? Bool ?? true
        tidyFormatting = d.object(forKey: "tidyFormatting") as? Bool ?? true
        removeFillers = d.object(forKey: "removeFillers") as? Bool ?? false
        smartFormat = d.object(forKey: "smartFormat") as? Bool ?? true
        vocabulary = d.string(forKey: "vocabulary") ?? ""
        showFloatingButton = d.object(forKey: "showFloatingButton") as? Bool ?? true
        if let data = d.data(forKey: "dictionary"),
           let dict = try? JSONDecoder().decode([String: String].self, from: data) {
            dictionary = dict
        } else {
            dictionary = [:]
        }
    }

    private func saveDictionary() {
        if let data = try? JSONEncoder().encode(dictionary) {
            d.set(data, forKey: "dictionary")
        }
    }

    static let models = [("tiny", "Tiny — fastest"), ("base", "Base — fast (recommended)"),
                         ("small", "Small — more accurate"), ("large-v3", "Large v3 — best, slower")]
    static let languages = [("", "Auto-detect"), ("en", "English"), ("fr", "French"),
                            ("ar", "Arabic"), ("es", "Spanish"), ("de", "German"),
                            ("it", "Italian"), ("pt", "Portuguese"), ("nl", "Dutch"),
                            ("ru", "Russian"), ("zh", "Chinese"), ("ja", "Japanese"),
                            ("hi", "Hindi"), ("tr", "Turkish")]
    static let outputs = [("paste", "Paste instantly"), ("type", "Type with writing effect"),
                          ("clipboard", "Copy to clipboard only")]
}
