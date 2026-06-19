#!/usr/bin/env bash
# Generate the Wispermo app icon (.icns): an ink squircle with a paper waveform
# and a clay accent bar. Drawn with CoreGraphics, no design tools needed.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

swift - "$WORK/icon_1024.png" <<'SWIFT'
import AppKit

let out = CommandLine.arguments[1]
let S = 1024
let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: S, pixelsHigh: S,
    bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
    colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
let ctx = NSGraphicsContext.current!.cgContext

let f = CGFloat(S)
let inset = f * 0.085
let rect = CGRect(x: inset, y: inset, width: f - 2*inset, height: f - 2*inset)
let radius = rect.width * 0.233

// ink squircle tile (#121211) — the original WISPERMO brand
ctx.addPath(CGPath(roundedRect: rect, cornerWidth: radius, cornerHeight: radius, transform: nil))
ctx.setFillColor(CGColor(srgbRed: 0.071, green: 0.071, blue: 0.067, alpha: 1))
ctx.fillPath()

// draw the mark in the original 128 viewBox coords (flip y to match SVG)
ctx.saveGState()
ctx.translateBy(x: rect.minX, y: rect.maxY)
ctx.scaleBy(x: rect.width / 128, y: -rect.height / 128)
let paper = CGColor(srgbRed: 0.98, green: 0.98, blue: 0.972, alpha: 1)   // #FAFAF8

// text caret (paper vertical pill)
ctx.addPath(CGPath(roundedRect: CGRect(x: 40, y: 36, width: 13, height: 56),
                   cornerWidth: 6.5, cornerHeight: 6.5, transform: nil))
ctx.setFillColor(paper); ctx.fillPath()

// voice ripple 1
ctx.setStrokeColor(paper); ctx.setLineWidth(10); ctx.setLineCap(.round)
let r1 = CGMutablePath()
r1.move(to: CGPoint(x: 68, y: 46))
r1.addQuadCurve(to: CGPoint(x: 68, y: 82), control: CGPoint(x: 86, y: 64))
ctx.addPath(r1); ctx.strokePath()

// voice ripple 2 (faded)
ctx.setStrokeColor(paper.copy(alpha: 0.45)!)
let r2 = CGMutablePath()
r2.move(to: CGPoint(x: 85, y: 38))
r2.addQuadCurve(to: CGPoint(x: 85, y: 90), control: CGPoint(x: 112, y: 64))
ctx.addPath(r2); ctx.strokePath()
ctx.restoreGState()

NSGraphicsContext.restoreGraphicsState()
let data = rep.representation(using: .png, properties: [:])!
try! data.write(to: URL(fileURLWithPath: out))
SWIFT

ICONSET="$WORK/AppIcon.iconset"; mkdir -p "$ICONSET"
for s in 16 32 128 256 512; do
  sips -z $s $s "$WORK/icon_1024.png" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
  d=$((s*2)); sips -z $d $d "$WORK/icon_1024.png" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$HERE/AppIcon.icns"
cp "$WORK/icon_1024.png" "$HERE/AppIcon.png"
echo "==> made AppIcon.icns + AppIcon.png"
