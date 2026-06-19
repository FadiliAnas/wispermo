import SwiftUI

/// Observable UI state, updated by AppController and read by the SwiftUI window.
@MainActor
final class AppState: ObservableObject {
    enum Kind { case loading, idle, recording, transcribing, error }
    enum Page: String, CaseIterable, Identifiable {
        case home, history, dictionary, settings
        var id: String { rawValue }
        var title: String {
            switch self {
            case .home: return "Home"; case .history: return "History"
            case .dictionary: return "Dictionary"; case .settings: return "Settings"
            }
        }
        var icon: String {
            switch self {
            case .home: return "house"; case .history: return "clock.arrow.circlepath"
            case .dictionary: return "character.book.closed"; case .settings: return "slider.horizontal.3"
            }
        }
    }

    @Published var page: Page = .home
    @Published var kind: Kind = .loading
    @Published var status: String = "Loading speech model…"
    @Published var level: Float = 0          // live mic level 0…1
    @Published var modelProgress: Double = 1 // first-run model download (0…1; 1 = done)
    @Published var lastText: String = ""

    @Published var micGranted = false
    @Published var accessibilityGranted = false
    @Published var inputMonitoringGranted = false

    // actions wired by the controller
    var onToggle: () -> Void = {}
    var onOpenPane: (Permissions.Pane) -> Void = { _ in }
}
