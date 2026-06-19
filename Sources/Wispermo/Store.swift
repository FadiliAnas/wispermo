import Foundation

struct Entry: Codable, Identifiable {
    var id = UUID()
    var text: String
    var lang: String
    var date: Date
    var words: Int
    var seconds: Double
}

struct Stats {
    var words = 0, wpm = 0, count = 0, avgWords = 0, streak = 0
    var gainedMinutes = 0.0
}

/// Transcription history + metrics, persisted to JSON in Application Support.
@MainActor
final class Store: ObservableObject {
    static let shared = Store()
    @Published private(set) var entries: [Entry] = []   // newest first
    private let url: URL
    private let typingWPM = 40.0

    private init() {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("Wispermo", isDirectory: true)
        try? FileManager.default.createDirectory(at: base, withIntermediateDirectories: true)
        url = base.appendingPathComponent("history.json")
        load()
    }

    func add(text: String, lang: String, seconds: Double) {
        let e = Entry(text: text, lang: lang, date: Date(),
                      words: text.split(whereSeparator: { $0 == " " || $0 == "\n" }).count,
                      seconds: seconds)
        entries.insert(e, at: 0)
        if entries.count > 500 { entries = Array(entries.prefix(500)) }
        save()
    }

    func clear() { entries.removeAll(); save() }

    var stats: Stats {
        var s = Stats()
        s.count = entries.count
        s.words = entries.reduce(0) { $0 + $1.words }
        let speech = entries.reduce(0.0) { $0 + $1.seconds }
        let typeMin = Double(s.words) / typingWPM
        s.gainedMinutes = max(0, typeMin - speech / 60.0)
        if speech > 0 { s.wpm = Int((Double(s.words) / (speech / 60.0)).rounded()) }
        s.avgWords = s.count > 0 ? s.words / s.count : 0
        s.streak = computeStreak()
        return s
    }

    func dailyCounts(_ n: Int = 7) -> [Int] {
        let cal = Calendar.current
        let today = cal.startOfDay(for: Date())
        var counts = [Int](repeating: 0, count: n)
        for e in entries {
            let day = cal.startOfDay(for: e.date)
            if let diff = cal.dateComponents([.day], from: day, to: today).day,
               diff >= 0, diff < n {
                counts[n - 1 - diff] += 1
            }
        }
        return counts
    }

    private func computeStreak() -> Int {
        let cal = Calendar.current
        let days = Set(entries.map { cal.startOfDay(for: $0.date) })
        guard !days.isEmpty else { return 0 }
        var streak = 0
        var day = cal.startOfDay(for: Date())
        if !days.contains(day) {
            day = cal.date(byAdding: .day, value: -1, to: day)!
            if !days.contains(day) { return 0 }
        }
        while days.contains(day) {
            streak += 1
            day = cal.date(byAdding: .day, value: -1, to: day)!
        }
        return streak
    }

    private func load() {
        guard let data = try? Data(contentsOf: url),
              let list = try? JSONDecoder().decode([Entry].self, from: data) else { return }
        entries = list
    }
    private func save() {
        if let data = try? JSONEncoder().encode(entries) { try? data.write(to: url) }
    }
}
