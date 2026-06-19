import SwiftUI

struct SettingsView: View {
    @ObservedObject var state: AppState
    @ObservedObject private var config = Config.shared

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Settings").font(.system(size: 24, weight: .bold)).foregroundStyle(Theme.text)

                SettingsSection(title: "Speech") {
                    FieldRow(title: "Model", subtitle: "Bigger = more accurate, slower") {
                        Picker("", selection: $config.model) {
                            ForEach(Config.models, id: \.0) { Text($0.1).tag($0.0) }
                        }.labelsHidden().frame(width: 220)
                    }
                    divider
                    FieldRow(title: "Language", subtitle: "Pin a language to skip detection") {
                        Picker("", selection: $config.language) {
                            ForEach(Config.languages, id: \.0) { Text($0.1).tag($0.0) }
                        }.labelsHidden().frame(width: 220)
                    }
                }

                SettingsSection(title: "Output") {
                    FieldRow(title: "How text appears", subtitle: "Paste instantly, or type with an effect") {
                        Picker("", selection: $config.output) {
                            ForEach(Config.outputs, id: \.0) { Text($0.1).tag($0.0) }
                        }.labelsHidden().frame(width: 220)
                    }
                    divider
                    FieldRow(title: "Add trailing space", subtitle: "Handy for continuous dictation") {
                        Toggle("", isOn: $config.trailingSpace).labelsHidden()
                    }
                    divider
                    FieldRow(title: "Tidy formatting", subtitle: "Fix capitalisation & spacing") {
                        Toggle("", isOn: $config.tidyFormatting).labelsHidden()
                    }
                    divider
                    FieldRow(title: "Remove filler words", subtitle: "Drop “um”, “uh”, “erm”…") {
                        Toggle("", isOn: $config.removeFillers).labelsHidden()
                    }
                    divider
                    FieldRow(title: "Smart formatting", subtitle: "Auto-detect numbered lists, bullet points & email structure") {
                        Toggle("", isOn: $config.smartFormat).labelsHidden()
                    }
                }

                SettingsSection(title: "Hotkey") {
                    FieldRow(title: "Use the 🌐 / Fn key", subtitle: "Tap or hold Globe/Fn to dictate. Set 🌐 to “Do Nothing” in System Settings ▸ Keyboard.") {
                        Toggle("", isOn: $config.useFn).labelsHidden()
                    }
                    divider
                    FieldRow(title: "Mode", subtitle: "Hold to talk, or press to toggle") {
                        Picker("", selection: $config.hotkeyMode) {
                            Text("Push-to-talk (hold)").tag("ptt")
                            Text("Toggle (press on/off)").tag("toggle")
                        }.labelsHidden().frame(width: 220)
                    }
                    divider
                    FieldRow(title: "Floating mic button", subtitle: "Always-on-top quick button") {
                        Toggle("", isOn: $config.showFloatingButton).labelsHidden()
                    }
                }

                SettingsSection(title: "Vocabulary & names") {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("Comma-separated terms Wispermo should spell correctly (names, brands, jargon).")
                            .font(.system(size: 12)).foregroundStyle(Theme.muted)
                        TextEditor(text: $config.vocabulary)
                            .font(.system(size: 13)).frame(height: 60)
                            .scrollContentBackground(.hidden)
                            .padding(6).background(Theme.surface2)
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                    }.padding(.top, 6)
                }

                SettingsSection(title: "Permissions") {
                    permRow("Microphone", state.micGranted, .microphone)
                    divider
                    permRow("Accessibility — to paste text", state.accessibilityGranted, .accessibility)
                    divider
                    permRow("Input Monitoring — for the hotkey", state.inputMonitoringGranted, .inputMonitoring)
                }

                Text("Wispermo · local, offline dictation · powered by WhisperKit")
                    .font(.system(size: 11)).foregroundStyle(Theme.faint).padding(.top, 4)
            }
            .padding(EdgeInsets(top: 30, leading: 32, bottom: 30, trailing: 32))
        }
    }

    private var divider: some View {
        Rectangle().fill(Theme.border).frame(height: 1)
    }
    private func permRow(_ title: String, _ ok: Bool, _ pane: Permissions.Pane) -> some View {
        FieldRow(title: title, subtitle: ok ? "Granted" : "Not granted") {
            if ok {
                Image(systemName: "checkmark.circle.fill").foregroundStyle(Color(hex: 0x4CAF50))
            } else {
                Button("Open Settings") { state.onOpenPane(pane) }.controlSize(.small)
            }
        }
    }
}
