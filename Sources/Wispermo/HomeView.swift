import SwiftUI

struct HomeView: View {
    @ObservedObject var state: AppState
    @ObservedObject private var store = Store.shared
    @ObservedObject private var config = Config.shared

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("Welcome back").font(.system(size: 24, weight: .bold))
                    .foregroundStyle(Theme.text)

                hero
                stats
                permissionsIfNeeded

                SectionLabel(text: "Recent")
                feed
            }
            .padding(EdgeInsets(top: 30, leading: 32, bottom: 30, trailing: 32))
        }
    }

    private var hero: some View {
        HeroCard {
            HStack(spacing: 20) {
                VStack(alignment: .leading, spacing: 8) {
                    (Text("Speak it. Wispermo ") + Text("types").italic() + Text(" it."))
                        .font(Theme.serif(25)).foregroundStyle(.white)
                    Text("Press your hotkey or tap the mic, talk, and your words land in whatever app you're using.")
                        .font(.system(size: 13)).foregroundStyle(.white.opacity(0.82))
                    Text("Hotkey:  \(config.useFn ? "🌐 Fn" : config.hotkeyLabel)   ·   \(config.hotkeyMode == "toggle" ? "press to toggle" : "hold to talk")")
                        .font(.system(size: 12)).foregroundStyle(.white.opacity(0.7))
                        .padding(.top, 4)
                    Spacer(minLength: 0)
                }
                Spacer(minLength: 0)
                VStack(spacing: 8) {
                    Button(action: state.onToggle) {
                        ZStack {
                            Circle().fill(.white).frame(width: 84, height: 84)
                            Image(systemName: state.kind == .recording ? "stop.fill" : "mic.fill")
                                .font(.system(size: 32)).foregroundStyle(Theme.accent)
                        }
                    }
                    .buttonStyle(.plain)
                    .disabled(state.kind == .loading || state.kind == .transcribing)
                    Text(stateLabel).font(.system(size: 12, weight: .semibold))
                        .foregroundStyle(.white)
                }
            }
            .padding(26)
        }
    }

    private var stats: some View {
        let s = store.stats
        return HStack(spacing: 14) {
            StatCard(value: "\(s.words)", label: "Words dictated")
            StatCard(value: s.wpm > 0 ? "\(s.wpm)" : "–", label: "Avg WPM")
            StatCard(value: fmtMinutes(s.gainedMinutes), label: "Time gained")
            StatCard(value: "\(s.streak)", label: "Day streak")
        }
    }

    @ViewBuilder private var permissionsIfNeeded: some View {
        if !(state.micGranted && state.accessibilityGranted && state.inputMonitoringGranted) {
            Card {
                VStack(alignment: .leading, spacing: 10) {
                    Text("Finish setup").font(.system(size: 14, weight: .semibold))
                    permRow("Microphone", state.micGranted, .microphone)
                    permRow("Accessibility — to paste", state.accessibilityGranted, .accessibility)
                    permRow("Input Monitoring — for the hotkey", state.inputMonitoringGranted, .inputMonitoring)
                    Text("After granting, quit and reopen Wispermo.")
                        .font(.system(size: 12)).foregroundStyle(Theme.muted)
                }.padding(16)
            }
        }
    }

    private func permRow(_ title: String, _ ok: Bool, _ pane: Permissions.Pane) -> some View {
        HStack {
            Image(systemName: ok ? "checkmark.circle.fill" : "exclamationmark.circle")
                .foregroundStyle(ok ? Color(hex: 0x4CAF50) : Theme.accent)
            Text(title).font(.system(size: 13)).foregroundStyle(Theme.text)
            Spacer()
            if !ok { Button("Grant") { state.onOpenPane(pane) }.controlSize(.small) }
        }
    }

    @ViewBuilder private var feed: some View {
        if store.entries.isEmpty {
            Text("Nothing yet — press your hotkey and start talking.")
                .font(.system(size: 13)).foregroundStyle(Theme.muted).padding(.top, 4)
        } else {
            VStack(spacing: 0) {
                ForEach(grouped, id: \.0) { day, items in
                    VStack(alignment: .leading, spacing: 0) {
                        SectionLabel(text: day).padding(.top, 12).padding(.bottom, 6)
                        ForEach(items) { e in FeedRow(entry: e) }
                    }
                }
            }
        }
    }

    private var grouped: [(String, [Entry])] {
        var order: [String] = []
        var map: [String: [Entry]] = [:]
        for e in store.entries.prefix(20) {
            let key = dayLabel(e.date)
            if map[key] == nil { map[key] = []; order.append(key) }
            map[key]!.append(e)
        }
        return order.map { ($0, map[$0]!) }
    }

    private var stateLabel: String {
        switch state.kind {
        case .loading: return "Loading…"; case .idle: return "Ready"
        case .recording: return "Listening…"; case .transcribing: return "Transcribing…"
        case .error: return "Error"
        }
    }
    private func fmtMinutes(_ m: Double) -> String {
        if m < 1 { return "\(Int((m * 60).rounded()))s" }
        if m < 60 { return "\(Int(m.rounded()))m" }
        return String(format: "%.1fh", m / 60)
    }
    private func dayLabel(_ date: Date) -> String {
        let cal = Calendar.current
        if cal.isDateInToday(date) { return "Today" }
        if cal.isDateInYesterday(date) { return "Yesterday" }
        let f = DateFormatter(); f.dateFormat = "EEEE d MMM"
        return f.string(from: date)
    }
}

struct FeedRow: View {
    let entry: Entry
    var body: some View {
        HStack(alignment: .top, spacing: 16) {
            Text(time).font(Theme.mono(12, .regular)).foregroundStyle(Theme.faint)
                .frame(width: 72, alignment: .leading)
            Text(entry.text).font(.system(size: 13)).foregroundStyle(Theme.text)
                .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 0)
        }
        .padding(.vertical, 10)
        .overlay(Rectangle().fill(Theme.border).frame(height: 1), alignment: .bottom)
    }
    private var time: String {
        let f = DateFormatter(); f.dateFormat = "h:mm a"; return f.string(from: entry.date).lowercased()
    }
}
