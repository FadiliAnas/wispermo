import SwiftUI

struct HistoryView: View {
    @ObservedObject private var store = Store.shared
    @State private var query = ""
    @State private var copied: UUID?

    private var filtered: [Entry] {
        let q = query.trimmingCharacters(in: .whitespaces).lowercased()
        return q.isEmpty ? store.entries : store.entries.filter { $0.text.lowercased().contains(q) }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text("History").font(.system(size: 24, weight: .bold)).foregroundStyle(Theme.text)
                Spacer()
                Button(action: { store.clear() }) {
                    Text("Clear all").font(.system(size: 13, weight: .medium))
                        .foregroundStyle(Theme.danger)
                        .padding(.horizontal, 14).padding(.vertical, 8)
                        .overlay(RoundedRectangle(cornerRadius: 10).stroke(Theme.border, lineWidth: 1))
                }.buttonStyle(.plain)
            }

            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass").foregroundStyle(Theme.faint)
                TextField("Search transcriptions…", text: $query).textFieldStyle(.plain)
            }
            .padding(.horizontal, 12).padding(.vertical, 9)
            .background(Theme.surface)
            .overlay(RoundedRectangle(cornerRadius: 10).stroke(Theme.border, lineWidth: 1))
            .clipShape(RoundedRectangle(cornerRadius: 10))

            if filtered.isEmpty {
                Text("Nothing here yet.").font(.system(size: 13)).foregroundStyle(Theme.muted).padding(.top, 8)
                Spacer()
            } else {
                ScrollView {
                    VStack(spacing: 0) {
                        ForEach(filtered) { e in row(e) }
                    }
                }
                Text(copied != nil ? "Copied to clipboard." : "Tip: click an entry to copy it.")
                    .font(.system(size: 12)).foregroundStyle(Theme.muted)
            }
        }
        .padding(EdgeInsets(top: 30, leading: 32, bottom: 24, trailing: 32))
    }

    private func row(_ e: Entry) -> some View {
        Button(action: { copy(e) }) {
            VStack(alignment: .leading, spacing: 4) {
                Text(e.text).font(.system(size: 13)).foregroundStyle(Theme.text)
                    .fixedSize(horizontal: false, vertical: true)
                    .frame(maxWidth: .infinity, alignment: .leading)
                Text("\(ago(e.date)) · \(e.lang.isEmpty ? "–" : e.lang) · \(e.text.count) chars")
                    .font(.system(size: 11)).foregroundStyle(Theme.faint)
            }
            .padding(.vertical, 12)
            .overlay(Rectangle().fill(Theme.border).frame(height: 1), alignment: .bottom)
            .contentShape(Rectangle())
        }.buttonStyle(.plain)
    }

    private func copy(_ e: Entry) {
        Paster.copyToClipboard(e.text); copied = e.id
    }
    private func ago(_ d: Date) -> String {
        let s = Int(Date().timeIntervalSince(d))
        if s < 60 { return "just now" }
        if s < 3600 { return "\(s/60)m ago" }
        if s < 86400 { return "\(s/3600)h ago" }
        return "\(s/86400)d ago"
    }
}
