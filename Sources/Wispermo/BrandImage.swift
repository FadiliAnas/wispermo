import AppKit

/// The WISPERMO mark (caret + voice ripples) as a black template image for the
/// macOS menu bar — macOS recolours it for the light/dark menu bar. Drawn with a
/// resolution-independent handler so it's crisp on Retina.
enum BrandImage {
    static func menuBar() -> NSImage {
        let size = NSSize(width: 20, height: 16)
        let image = NSImage(size: size, flipped: false) { rect in
            guard let ctx = NSGraphicsContext.current?.cgContext else { return false }
            let w = rect.width, h = rect.height
            // fit the mark's 128-viewBox bbox (x40..118, y33..95) into the rect
            let bx: CGFloat = 40, by: CGFloat = 33, bw: CGFloat = 78, bh: CGFloat = 62
            let pad: CGFloat = 1
            let s = min((w - 2*pad) / bw, (h - 2*pad) / bh)
            ctx.saveGState()
            ctx.translateBy(x: rect.minX + (w - bw*s) / 2, y: rect.minY + h - (h - bh*s) / 2)
            ctx.scaleBy(x: s, y: -s)               // flip y to match the SVG coords
            ctx.translateBy(x: -bx, y: -by)

            let black = NSColor.black.cgColor
            ctx.addPath(CGPath(roundedRect: CGRect(x: 40, y: 36, width: 13, height: 56),
                               cornerWidth: 6.5, cornerHeight: 6.5, transform: nil))
            ctx.setFillColor(black); ctx.fillPath()

            ctx.setStrokeColor(black); ctx.setLineWidth(10); ctx.setLineCap(.round)
            let r1 = CGMutablePath()
            r1.move(to: CGPoint(x: 68, y: 46))
            r1.addQuadCurve(to: CGPoint(x: 68, y: 82), control: CGPoint(x: 86, y: 64))
            ctx.addPath(r1); ctx.strokePath()

            ctx.setStrokeColor(NSColor.black.withAlphaComponent(0.5).cgColor)
            let r2 = CGMutablePath()
            r2.move(to: CGPoint(x: 85, y: 38))
            r2.addQuadCurve(to: CGPoint(x: 85, y: 90), control: CGPoint(x: 112, y: 64))
            ctx.addPath(r2); ctx.strokePath()
            ctx.restoreGState()
            return true
        }
        image.isTemplate = true
        return image
    }
}
