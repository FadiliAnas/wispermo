import SwiftUI

// MARK: - Brand mark (the original WISPERMO logo: caret + voice ripples)
struct BrandMark: View {
    var size: CGFloat = 20
    var body: some View {
        Canvas { ctx, sz in
            let s = min(sz.width, sz.height)
            let k = s / 128                      // original 128 viewBox
            ctx.fill(Path(roundedRect: CGRect(x: 0, y: 0, width: s, height: s),
                          cornerRadius: s * 0.233), with: .color(Color(hex: 0x121211)))
            let paper = Color(hex: 0xFAFAF8)
            ctx.fill(Path(roundedRect: CGRect(x: 40*k, y: 36*k, width: 13*k, height: 56*k),
                          cornerRadius: 6.5*k), with: .color(paper))
            var r1 = Path()
            r1.move(to: CGPoint(x: 68*k, y: 46*k))
            r1.addQuadCurve(to: CGPoint(x: 68*k, y: 82*k), control: CGPoint(x: 86*k, y: 64*k))
            ctx.stroke(r1, with: .color(paper), style: StrokeStyle(lineWidth: 10*k, lineCap: .round))
            var r2 = Path()
            r2.move(to: CGPoint(x: 85*k, y: 38*k))
            r2.addQuadCurve(to: CGPoint(x: 85*k, y: 90*k), control: CGPoint(x: 112*k, y: 64*k))
            ctx.stroke(r2, with: .color(paper.opacity(0.45)), style: StrokeStyle(lineWidth: 10*k, lineCap: .round))
        }
        .frame(width: size, height: size)
    }
}

// MARK: - Card
struct Card<Content: View>: View {
    @ViewBuilder var content: Content
    var body: some View {
        content
            .background(Theme.surface)
            .overlay(RoundedRectangle(cornerRadius: 14).stroke(Theme.border, lineWidth: 1))
            .clipShape(RoundedRectangle(cornerRadius: 14))
    }
}

// MARK: - Section label
struct SectionLabel: View {
    let text: String
    var body: some View {
        Text(text.uppercased())
            .font(.system(size: 11, weight: .bold)).tracking(1.2)
            .foregroundStyle(Theme.faint)
    }
}

// MARK: - Sidebar nav button
struct NavButton: View {
    let icon: String
    let title: String
    let selected: Bool
    let action: () -> Void
    @State private var hover = false

    var body: some View {
        Button(action: action) {
            HStack(spacing: 12) {
                Image(systemName: icon)
                    .font(.system(size: 15, weight: .medium))
                    .frame(width: 20)
                    .foregroundStyle(selected ? Theme.accent : Theme.muted)
                Text(title)
                    .font(.system(size: 14, weight: selected ? .semibold : .medium))
                    .foregroundStyle(selected ? Theme.text : Theme.muted)
                Spacer()
            }
            .padding(.horizontal, 12).frame(height: 40)
            .background(selected ? Theme.accentSoft : (hover ? Theme.surface2 : Color.clear))
            .clipShape(RoundedRectangle(cornerRadius: 11))
        }
        .buttonStyle(.plain)
        .onHover { hover = $0 }
    }
}

// MARK: - Primary / accent buttons
struct InkButton: View {
    let title: String
    let action: () -> Void
    var body: some View {
        Button(action: action) {
            Text(title).font(.system(size: 13, weight: .semibold))
                .foregroundStyle(.white)
                .padding(.horizontal, 16).padding(.vertical, 9)
                .background(Theme.ink).clipShape(RoundedRectangle(cornerRadius: 10))
        }.buttonStyle(.plain)
    }
}

struct AccentButton: View {
    let title: String
    let action: () -> Void
    var body: some View {
        Button(action: action) {
            Text(title).font(.system(size: 13, weight: .semibold))
                .foregroundStyle(.white)
                .padding(.horizontal, 16).padding(.vertical, 9)
                .background(Theme.accent).clipShape(RoundedRectangle(cornerRadius: 10))
        }.buttonStyle(.plain)
    }
}

// MARK: - Stat card
struct StatCard: View {
    let value: String
    let label: String
    var body: some View {
        Card {
            VStack(alignment: .leading, spacing: 2) {
                Text(value).font(Theme.mono(24, .semibold)).foregroundStyle(Theme.text)
                Text(label.uppercased()).font(.system(size: 11)).tracking(0.5)
                    .foregroundStyle(Theme.muted)
            }
            .padding(16).frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

// MARK: - Hero gradient card
struct HeroCard<Content: View>: View {
    @ViewBuilder var content: Content
    var body: some View {
        content
            .background(Theme.heroGradient)
            .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: - Settings field row
struct FieldRow<Control: View>: View {
    let title: String
    let subtitle: String
    @ViewBuilder var control: Control
    var body: some View {
        HStack(alignment: .center, spacing: 16) {
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(.system(size: 13, weight: .semibold)).foregroundStyle(Theme.text)
                Text(subtitle).font(.system(size: 12)).foregroundStyle(Theme.muted)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 16)
            control
        }
        .padding(.vertical, 9)
    }
}

struct SettingsSection<Content: View>: View {
    let title: String
    @ViewBuilder var content: Content
    var body: some View {
        Card {
            VStack(alignment: .leading, spacing: 0) {
                Text(title).font(.system(size: 15, weight: .semibold)).foregroundStyle(Theme.text)
                    .padding(.bottom, 4)
                content
            }
            .padding(.horizontal, 18).padding(.vertical, 14)
        }
    }
}
