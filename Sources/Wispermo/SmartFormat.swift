import Foundation

/// Fast, on-device structure detection (no LLM, zero latency): spoken commands,
/// numbered lists, bullet lists, and light email shaping — like Wispr Flow's
/// quick formatting for the common dictation patterns.
enum SmartFormat {
    static func format(_ raw: String) -> String {
        var t = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !t.isEmpty else { return t }
        t = applyCommands(t)
        t = spokenEmail(t)
        if let list = numberedList(t) { return list }
        if let bullets = bulletList(t) { return bullets }
        if let email = emailShape(t) { return email }
        return collapseSpaces(t)
    }

    // MARK: spoken commands → line breaks
    private static func applyCommands(_ s: String) -> String {
        var t = s
        t = replace(t, #"(?i)[\s,]*\bnew paragraph\b[\s,]*"#, "\n\n")
        t = replace(t, #"(?i)[\s,]*\b(?:new|next) line\b[\s,]*"#, "\n")
        return t
    }

    // MARK: spoken email addresses — "john at example dot com" → "john@example.com"
    private static func spokenEmail(_ s: String) -> String {
        let pattern = #"(?i)\b([a-z0-9._%+-]+)\s+at\s+([a-z0-9-]+)\s+dot\s+(com|org|net|edu|io|co|gov|me|app|dev|ai)\b"#
        return replace(s, pattern, "$1@$2.$3")
    }

    // MARK: numbered list — "point/number/step one … two …" or "first … second …"
    private static let ords: [String: Int] = [
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
        "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
        "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
    ]

    private static func numberedList(_ text: String) -> String? {
        let pattern = #"(?i)\b(?:number|point|step)\s+(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)\b[\s,:.\-–]*"#
        let alt = #"(?i)(?:^|[.\n]\s*)(first(?:ly)?|second(?:ly)?|third(?:ly)?|fourth(?:ly)?|fifth(?:ly)?|sixth(?:ly)?|seventh|eighth|ninth|tenth|lastly|finally)\b[\s,:.\-–]*"#
        guard let items = splitByMarkers(text, primary: pattern) ??
                          splitByMarkers(text, primary: alt), items.items.count >= 2
        else { return nil }
        var out = ""
        if !items.preamble.isEmpty { out += sentence(items.preamble) + "\n" }
        for (i, item) in items.items.enumerated() { out += "\(i + 1). \(sentence(item))\n" }
        return out.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    // MARK: bullet list — "bullet point X bullet point Y …"
    private static func bulletList(_ text: String) -> String? {
        let pattern = #"(?i)\b(?:bullet\s*point|bullet)\b[\s,:.\-–]*"#
        guard let items = splitByMarkers(text, primary: pattern), items.items.count >= 1,
              text.range(of: #"(?i)\bbullet\b"#, options: .regularExpression) != nil
        else { return nil }
        var out = ""
        if !items.preamble.isEmpty { out += sentence(items.preamble) + "\n" }
        for item in items.items where !item.isEmpty { out += "• \(sentence(item))\n" }
        return out.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private struct Split { var preamble: String; var items: [String] }
    private static func splitByMarkers(_ text: String, primary: String) -> Split? {
        guard let re = try? NSRegularExpression(pattern: primary) else { return nil }
        let ns = text as NSString
        let ms = re.matches(in: text, range: NSRange(location: 0, length: ns.length))
        guard !ms.isEmpty else { return nil }
        let preamble = ns.substring(to: ms[0].range.location)
            .trimmingCharacters(in: CharacterSet(charactersIn: " ,.;:-–\n"))
        var items: [String] = []
        for (i, m) in ms.enumerated() {
            let start = m.range.location + m.range.length
            let end = (i + 1 < ms.count) ? ms[i + 1].range.location : ns.length
            guard end > start else { continue }
            let item = ns.substring(with: NSRange(location: start, length: end - start))
                .trimmingCharacters(in: CharacterSet(charactersIn: " ,.;:-–\n"))
            if !item.isEmpty { items.append(item) }
        }
        return Split(preamble: preamble, items: items)
    }

    // MARK: light email shaping (greeting / sign-off on their own lines)
    private static func emailShape(_ text: String) -> String? {
        let lower = text.lowercased()
        let greetings = ["dear ", "hi ", "hello ", "hey "]
        let signoffs = ["best regards", "kind regards", "warm regards", "regards",
                        "best wishes", "thanks so much", "thank you", "thanks", "sincerely", "cheers", "best"]
        let hasGreeting = greetings.contains { lower.hasPrefix($0) }
        let hasSignoff = signoffs.contains { lower.contains($0) }
        guard hasGreeting && hasSignoff else { return nil }

        var t = text
        // greeting: first clause up to first comma/period → its own line
        if let comma = t.firstIndex(where: { $0 == "," || $0 == "." }) {
            let greeting = String(t[..<comma]).trimmingCharacters(in: .whitespaces)
            let rest = String(t[t.index(after: comma)...]).trimmingCharacters(in: .whitespaces)
            if greeting.count < 40 { t = greeting + ",\n\n" + rest }
        }
        // sign-off: break before the sign-off phrase
        for phrase in ["best regards", "kind regards", "warm regards", "best wishes",
                       "regards", "sincerely", "cheers", "thanks so much", "thank you", "thanks", "best"] {
            if let r = t.range(of: phrase, options: [.caseInsensitive, .backwards]) {
                let before = String(t[..<r.lowerBound]).trimmingCharacters(in: .whitespaces)
                let signoff = String(t[r.lowerBound...]).trimmingCharacters(in: .whitespaces)
                t = before + "\n\n" + sentence(signoff)
                break
            }
        }
        return t
    }

    // MARK: helpers
    private static func sentence(_ s: String) -> String {
        var t = collapseSpaces(s.trimmingCharacters(in: .whitespacesAndNewlines))
        if let f = t.first, f.isLowercase { t = f.uppercased() + t.dropFirst() }
        return t
    }
    private static func collapseSpaces(_ s: String) -> String {
        replace(s, #" {2,}"#, " ").replacingOccurrences(of: " ,", with: ",")
            .replacingOccurrences(of: " .", with: ".")
    }
    private static func replace(_ s: String, _ pattern: String, _ with: String) -> String {
        guard let re = try? NSRegularExpression(pattern: pattern) else { return s }
        let ns = s as NSString
        return re.stringByReplacingMatches(in: s, range: NSRange(location: 0, length: ns.length),
                                           withTemplate: with)
    }
}
