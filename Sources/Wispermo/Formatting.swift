import Foundation

/// Post-processing for transcribed text: dictionary replacement, light tidy,
/// optional filler removal, de-stutter, trailing space. Fast and deterministic
/// (no LLM) — fixes the things raw speech-to-text gets wrong without changing
/// the user's words or meaning.
enum Formatting {
    @MainActor
    static func process(_ raw: String, config: Config) -> String {
        var text = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return "" }

        // dictionary: spoken phrase -> written form (case-insensitive)
        for (spoken, written) in config.dictionary where !spoken.isEmpty {
            text = replaceCaseInsensitive(text, spoken, written)
        }

        if config.removeFillers {
            for filler in ["um", "uh", "erm", "uhh", "umm", "er", "ah", "hmm"] {
                text = replaceCaseInsensitive(text, " \(filler) ", " ")
                if text.lowercased().hasPrefix("\(filler) ") {
                    text = String(text.dropFirst(filler.count + 1))
                }
            }
            for phrase in [" you know ", " i mean ", " sort of ", " kind of "] {
                text = replaceCaseInsensitive(text, phrase, " ")
            }
        }

        if config.tidyFormatting {
            text = deStutter(text)                              // "the the" -> "the"
            text = regex(text, #"\bi\b"#, "I")                  // standalone i -> I
            text = regex(text, #"\bi'"#, "I'")                  // i'm/i'll/i've -> I'
            text = regex(text, #" {2,}"#, " ")                  // collapse spaces
            text = regex(text, #"\s+([,.!?;:])"#, "$1")         // no space before punct
            if let first = text.first, first.isLowercase {
                text = first.uppercased() + text.dropFirst()
            }
        }

        return text.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// Collapse an immediate repeat of a common function word (a speech restart,
    /// e.g. "I I think" or "the the report"). Limited to words where a double is
    /// virtually always a stutter, so we never touch a valid repetition.
    private static func deStutter(_ s: String) -> String {
        let words = ["the", "a", "an", "i", "to", "and", "of", "is", "it",
                     "we", "you", "but", "so", "in", "on", "my", "with"]
        var t = s
        for w in words {
            t = regex(t, #"(?i)\b(\#(w))\s+\1\b"#, "$1")
        }
        return t
    }

    private static func replaceCaseInsensitive(_ s: String, _ target: String, _ with: String) -> String {
        guard !target.isEmpty else { return s }
        return s.replacingOccurrences(of: target, with: with,
                                      options: [.caseInsensitive], range: nil)
    }

    private static func regex(_ s: String, _ pattern: String, _ with: String) -> String {
        guard let re = try? NSRegularExpression(pattern: pattern) else { return s }
        let ns = s as NSString
        return re.stringByReplacingMatches(in: s, range: NSRange(location: 0, length: ns.length),
                                           withTemplate: with)
    }
}
