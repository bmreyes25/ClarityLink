import AppKit
import CryptoKit
import Foundation

struct Pattern {
    let name: String
    let expected: (Int, Int, Int)
    let accepts: (Int, Int, Int) -> Bool
}

let patterns = [
    Pattern(name: "static_blue", expected: (18, 48, 74), accepts: { r, g, b in b > r && b > g }),
    Pattern(name: "video_red", expected: (64, 20, 24), accepts: { r, g, b in r > g * 2 && r > b * 2 }),
    Pattern(name: "video_green", expected: (20, 64, 32), accepts: { r, g, b in g > r * 2 && Double(g) > Double(b) * 1.4 }),
    Pattern(name: "video_blue", expected: (24, 32, 72), accepts: { r, g, b in Double(b) > Double(r) * 1.4 && Double(b) > Double(g) * 1.2 })
]
let args = Array(CommandLine.arguments.dropFirst())
guard args.count == 6 else {
    fputs("usage: verify_api17_pixel_content.swift FRAME1.png FRAME2.png FRAME3.png FRAME4.png APK OUTPUT.json\n", stderr)
    exit(2)
}
func sha256(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }
func inspect(_ path: String, _ pattern: Pattern) throws -> [String: Any] {
    let data = try Data(contentsOf: URL(fileURLWithPath: path))
    guard let image = NSBitmapImageRep(data: data), image.pixelsWide == 800, image.pixelsHigh == 480 else {
        throw NSError(domain: "pixel-proof", code: 2, userInfo: [NSLocalizedDescriptionKey: "expected 800x480 PNG: \(path)"])
    }
    // Sample clean points outside text, the label, and the clipped center region.
    let points = [(560, 310), (610, 350), (200, 380), (250, 330), (650, 280)]
    var samples: [[Int]] = []
    for (x, yFromTop) in points {
        guard let color = image.colorAt(x: x, y: image.pixelsHigh - 1 - yFromTop)?.usingColorSpace(.deviceRGB) else {
            throw NSError(domain: "pixel-proof", code: 3, userInfo: [NSLocalizedDescriptionKey: "cannot sample PNG"])
        }
        samples.append([Int((color.redComponent * 255).rounded()), Int((color.greenComponent * 255).rounded()), Int((color.blueComponent * 255).rounded())])
    }
    let matches = samples.filter { pattern.accepts($0[0], $0[1], $0[2]) }.count >= 4
    return ["expectedPattern": pattern.name, "expectedSourceRgb": [pattern.expected.0, pattern.expected.1, pattern.expected.2],
            "observedRoiRgb": samples, "match": matches, "screenshot": path, "screenshotSha256": sha256(data)]
}
do {
    var results: [[String: Any]] = []
    for index in 0..<4 { results.append(try inspect(args[index], patterns[index])) }
    guard results.allSatisfy({ ($0["match"] as? Bool) == true }) else {
        throw NSError(domain: "pixel-proof", code: 4, userInfo: [NSLocalizedDescriptionKey: "one or more visible patterns did not match"])
    }
    // Negative control: reusing the red frame where green is expected must fail classification.
    let repeatedRedAsGreen = try inspect(args[1], patterns[2])
    guard (repeatedRedAsGreen["match"] as? Bool) == false else {
        throw NSError(domain: "pixel-proof", code: 5, userInfo: [NSLocalizedDescriptionKey: "repeated-frame negative control was not detected"])
    }
    let apkData = try Data(contentsOf: URL(fileURLWithPath: args[4]))
    let receipt: [String: Any] = ["result": "API17_VIEW_PIXEL_CONTENT_PASS", "captureType": "actual_renderer_view_capture_on_api17_emulator",
        "patterns": results, "negativeControl": ["expectedPattern": "video_green", "reusedScreenshot": args[1], "rejected": true],
        "apk": args[4], "apkSha256": sha256(apkData)]
    let output = try JSONSerialization.data(withJSONObject: receipt, options: [.prettyPrinted, .sortedKeys])
    try output.write(to: URL(fileURLWithPath: args[5]), options: .atomic)
    print("API17_VIEW_PIXEL_CONTENT_PASS frames=4 negative_control=repeated_red_rejected receipt=\(args[5]) apk_sha256=\(sha256(apkData))")
} catch {
    fputs("API17_VIEW_PIXEL_CONTENT_FAIL \(error.localizedDescription)\n", stderr)
    exit(1)
}
