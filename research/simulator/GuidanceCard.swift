// Offline proof of a dedicated guidance card from the already captured image.
// This is a cropped image, not a second stream supplied by the iPhone.
import AppKit
import Foundation

guard CommandLine.arguments.count == 3 else {
    fputs("Usage: GuidanceCard input.png output.png\n", stderr)
    exit(2)
}
let input = URL(fileURLWithPath: CommandLine.arguments[1])
let output = URL(fileURLWithPath: CommandLine.arguments[2])
guard let image = NSImage(contentsOf: input),
      let tiff = image.tiffRepresentation,
      let rep = NSBitmapImageRep(data: tiff),
      let cg = rep.cgImage,
      cg.width == 800, cg.height == 480 else {
    fputs("Expected an 800x480 captured CarPlay frame\n", stderr)
    exit(2)
}
// Card bounds measured from the saved Apple Maps screenshot. Calibrate again
// before using a different iPhone, CarPlay layout, or app.
guard let crop = cg.cropping(to: CGRect(x: 100, y: 8, width: 355, height: 115)),
      let bitmap = NSBitmapImageRep(cgImage: crop).representation(using: .png, properties: [:]) else {
    fputs("Crop failed\n", stderr)
    exit(2)
}
try bitmap.write(to: output)
