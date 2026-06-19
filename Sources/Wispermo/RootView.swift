import SwiftUI

struct RootView: View {
    @ObservedObject var state: AppState

    var body: some View {
        HStack(spacing: 0) {
            Sidebar(state: state)
            ZStack {
                Theme.surface
                switch state.page {
                case .home: HomeView(state: state)
                case .history: HistoryView()
                case .dictionary: DictionaryView()
                case .settings: SettingsView(state: state)
                }
            }
        }
        .frame(minWidth: 860, idealWidth: 940, minHeight: 580, idealHeight: 640)
        .background(Theme.bg)
        .tint(Theme.accent)
        .preferredColorScheme(.light)
        .foregroundStyle(Theme.text)
    }
}

struct Sidebar: View {
    @ObservedObject var state: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 9) {
                BrandMark(size: 20)
                Text("Wispermo").font(.system(size: 15, weight: .heavy))
                    .foregroundStyle(Theme.text)
                Spacer()
            }
            .padding(.horizontal, 6).padding(.top, 4).padding(.bottom, 14)

            ForEach(AppState.Page.allCases) { page in
                NavButton(icon: page.icon, title: page.title,
                          selected: state.page == page) { state.page = page }
            }

            Spacer()

            VStack(alignment: .leading, spacing: 6) {
                HStack(spacing: 8) {
                    Circle().fill(stateColor).frame(width: 8, height: 8)
                    Text(state.status).font(.system(size: 12)).foregroundStyle(Theme.muted)
                        .lineLimit(1)
                }
                if state.kind == .loading, state.modelProgress < 1 {
                    ProgressView(value: state.modelProgress)
                        .progressViewStyle(.linear).controlSize(.small)
                }
            }
            .padding(.horizontal, 8).padding(.vertical, 6)
        }
        .padding(12)
        .frame(width: 212)
        .background(Theme.bg)
        .overlay(Rectangle().fill(Theme.border).frame(width: 1), alignment: .trailing)
    }

    private var stateColor: Color {
        switch state.kind {
        case .recording: return Theme.accent
        case .transcribing: return Theme.faint
        case .idle: return Color(hex: 0x4CAF50)
        default: return Theme.faint
        }
    }
}
