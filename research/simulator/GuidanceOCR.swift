// Offline image analysis only. This process has no connection to a vehicle.
import AppKit
import Foundation
import Vision

struct Line: Codable {
    let text: String
    let confidence: Float
    let box: [Double] // normalized x, y, width, height; y is measured from the bottom
}

struct Result: Codable {
    let source: String
    let width: Int
    let height: Int
    let bannerText: String
    let lines: [Line]
    let observedOnly: Bool
}

guard CommandLine.arguments.count == 2 else {
    fputs("Usage: GuidanceOCR image.png\n", stderr)
    exit(2)
}
let url = URL(fileURLWithPath: CommandLine.arguments[1])
guard let image = NSImage(contentsOf: url),
      let tiff = image.tiffRepresentation,
      let rep = NSBitmapImageRep(data: tiff),
      let cg = rep.cgImage else {
    fputs("Cannot decode image\n", stderr)
    exit(2)
}
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
try VNImageRequestHandler(cgImage: cg).perform([request])
let lines = (request.results ?? []).compactMap { item -> Line? in
    guard let candidate = item.topCandidates(1).first else { return nil }
    let b = item.boundingBox
    return Line(text: candidate.string, confidence: candidate.confidence,
                box: [b.minX, b.minY, b.width, b.height])
}.sorted { a, b in
    let ay = a.box[1] + a.box[3] / 2
    let by = b.box[1] + b.box[3] / 2
    if abs(ay - by) > 0.02 { return ay > by }
    return a.box[0] < b.box[0]
}
// The top-center card in the captured 800x480 Apple Maps layout. Other
// CarPlay layouts require calibration; this is deliberately observational.
let banner = lines.filter { $0.box[0] > 0.12 && $0.box[0] < 0.62 && $0.box[1] > 0.72 }
                  .map(\.text).joined(separator: " ")
let result = Result(source: url.lastPathComponent, width: cg.width, height: cg.height,
                    bannerText: banner, lines: lines, observedOnly: true)
let encoder = JSONEncoder()
encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
FileHandle.standardOutput.write(try encoder.encode(result))
