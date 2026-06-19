import SwiftUI

struct DictionaryView: View {
    @ObservedObject private var config = Config.shared
    @State private var spoken = ""
    @State private var written = ""
    @State private var showAdd = false

    private var sorted: [(String, String)] {
        config.dictionary.sorted { $0.key.lowercased() < $1.key.lowercased() }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text("Dictionary").font(.system(size: 24, weight: .bold)).foregroundStyle(Theme.text)
                Spacer()
                InkButton(title: showAdd ? "Close" : "Add new") { withAnimation { showAdd.toggle() } }
            }

            hero

            if showAdd {
                Card {
                    HStack(spacing: 8) {
                        TextField("When I say…", text: $spoken).textFieldStyle(.plain)
                            .padding(8).background(Theme.surface2).clipShape(RoundedRectangle(cornerRadius: 8))
                        TextField("Write this", text: $written).textFieldStyle(.plain)
                            .padding(8).background(Theme.surface2).clipShape(RoundedRectangle(cornerRadius: 8))
                        AccentButton(title: "Add") { add() }
                    }.padding(12)
                }
            }

            if sorted.isEmpty {
                Text("No terms yet — tap “Add new” to teach Wispermo a word.")
                    .font(.system(size: 13)).foregroundStyle(Theme.muted).padding(.top, 6)
                Spacer()
            } else {
                ScrollView {
                    VStack(spacing: 0) {
                        ForEach(sorted, id: \.0) { spoken, written in row(spoken, written) }
                    }
                }
            }
        }
        .padding(EdgeInsets(top: 30, leading: 32, bottom: 24, trailing: 32))
    }

    private var hero: some View {
        HeroCard {
            VStack(alignment: .leading, spacing: 8) {
                (Text("Wispermo spells it the way ") + Text("you").italic() + Text(" do."))
                    .font(Theme.serif(23)).foregroundStyle(.white)
                Text("Teach it your names, brands and jargon so they're always typed exactly right.")
                    .font(.system(size: 13)).foregroundStyle(.white.opacity(0.82))
                HStack(spacing: 8) {
                    ForEach(chips, id: \.self) { chip in
                        Text(chip).font(.system(size: 12, weight: .semibold))
                            .foregroundStyle(.white.opacity(0.95))
                            .padding(.horizontal, 11).padding(.vertical, 5)
                            .background(.white.opacity(0.16)).clipShape(Capsule())
                    }
                }.padding(.top, 4)
            }
            .padding(24).frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var chips: [String] {
        let keys = Array(config.dictionary.keys.prefix(5))
        return keys.isEmpty ? ["names", "brands", "jargon"] : keys
    }

    private func row(_ spoken: String, _ written: String) -> some View {
        HStack(spacing: 10) {
            Image(systemName: "sparkles").font(.system(size: 13)).foregroundStyle(Theme.accent).frame(width: 20)
            Text(spoken).font(.system(size: 13, weight: .semibold)).foregroundStyle(Theme.text)
            Image(systemName: "arrow.right").font(.system(size: 11)).foregroundStyle(Theme.faint)
            Text(written.isEmpty ? "—" : written).font(.system(size: 13)).foregroundStyle(Theme.muted)
            Spacer()
            Button(action: { remove(spoken) }) {
                Image(systemName: "xmark").font(.system(size: 12)).foregroundStyle(Theme.faint)
            }.buttonStyle(.plain)
        }
        .padding(.vertical, 11)
        .overlay(Rectangle().fill(Theme.border).frame(height: 1), alignment: .bottom)
    }

    private func add() {
        let s = spoken.trimmingCharacters(in: .whitespaces)
        guard !s.isEmpty else { return }
        config.dictionary[s] = written.trimmingCharacters(in: .whitespaces)
        spoken = ""; written = ""
    }
    private func remove(_ key: String) { config.dictionary.removeValue(forKey: key) }
}
