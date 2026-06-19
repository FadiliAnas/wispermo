import SwiftUI

/// Warm-neutral light design system with a single clay accent (Wispr-Flow feel).
enum Theme {
    static let bg        = Color(hex: 0xF3F1EC)
    static let surface   = Color(hex: 0xFFFFFF)
    static let surface2  = Color(hex: 0xEFEDE7)
    static let border    = Color(hex: 0xE7E4DD)
    static let text      = Color(hex: 0x1B1A17)
    static let muted     = Color(hex: 0x6B6760)
    static let faint     = Color(hex: 0x9A968C)
    // accent = black (ink), no orange
    static let accent    = Color(hex: 0x1B1A17)
    static let accentHi  = Color(hex: 0x33312D)
    static let accentSoft = Color(hex: 0xEAE8E2)
    static let ink       = Color(hex: 0x1B1A17)
    static let danger    = Color(hex: 0xC0473C)

    static let heroGradient = LinearGradient(
        colors: [Color(hex: 0x33312D), Color(hex: 0x1B1A17), Color(hex: 0x0E0D0C)],
        startPoint: .leading, endPoint: .trailing)

    static func serif(_ size: CGFloat, _ weight: Font.Weight = .regular) -> Font {
        .custom("New York", size: size).weight(weight)
    }
    static func sans(_ size: CGFloat, _ weight: Font.Weight = .regular) -> Font {
        .system(size: size, weight: weight)
    }
    static func mono(_ size: CGFloat, _ weight: Font.Weight = .semibold) -> Font {
        .system(size: size, weight: weight, design: .monospaced)
    }
}

extension Color {
    init(hex: UInt32) {
        self.init(.sRGB,
                  red: Double((hex >> 16) & 0xFF) / 255,
                  green: Double((hex >> 8) & 0xFF) / 255,
                  blue: Double(hex & 0xFF) / 255,
                  opacity: 1)
    }
}
