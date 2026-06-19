// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "Wispermo",
    platforms: [.macOS(.v14)],
    dependencies: [
        .package(url: "https://github.com/argmaxinc/WhisperKit", from: "0.9.0"),
    ],
    targets: [
        .executableTarget(
            name: "Wispermo",
            dependencies: [
                .product(name: "WhisperKit", package: "WhisperKit"),
            ],
            path: "Sources/Wispermo",
            // Relaxed concurrency during the build-out; tighten to v6 later.
            swiftSettings: [.swiftLanguageMode(.v5)]
        ),
        // Build-time helper: downloads the Whisper model + tokenizer into a
        // folder so build-app.sh can bundle them inside the .app (plug-and-play,
        // no first-run download).
        .executableTarget(
            name: "FetchModel",
            dependencies: [
                .product(name: "WhisperKit", package: "WhisperKit"),
            ],
            path: "Sources/FetchModel",
            swiftSettings: [.swiftLanguageMode(.v5)]
        )
    ]
)
