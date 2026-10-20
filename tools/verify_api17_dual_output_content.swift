import AppKit
import CryptoKit
import Foundation

func sha256(_ data: Data) -> String {
    SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
}

let args = Array(CommandLine.arguments.dropFirst())
guard args.count == 2 else {
    fputs("usage: verify_api17_dual_output_content.swift SCREENSHOT RECEIPT.json\n", stderr)
    exit(2)
}
do {
    let data = try Data(contentsOf: URL(fileURLWithPath: args[0]))
    guard let image = NSBitmapImageRep(data: data), image.pixelsWide == 800,
          image.pixelsHigh == 480 else {
        throw NSError(domain: "dual-output-proof", code: 1,
                      userInfo: [NSLocalizedDescriptionKey: "expected 800x480 View proof PNG"])
    }
    func sample(_ x: Int, _ yFromTop: Int) throws -> [Int] {
        guard let color = image.colorAt(x: x, y: yFromTop)?
                .usingColorSpace(.deviceRGB) else {
            throw NSError(domain: "dual-output-proof", code: 2,
                          userInfo: [NSLocalizedDescriptionKey: "could not sample proof PNG"])
        }
        return [Int((color.redComponent * 255).rounded()),
                Int((color.greenComponent * 255).rounded()),
                Int((color.blueComponent * 255).rounded())]
    }
    let red = try sample(400, 100)
    let green = try sample(400, 330)
    let redMatches = red[0] > red[1] * 2 && red[0] > red[2] * 2
    let greenMatches = green[1] > green[0] * 2 && Double(green[1]) > Double(green[2]) * 1.4
    guard redMatches && greenMatches else {
        throw NSError(domain: "dual-output-proof", code: 3,
                      userInfo: [NSLocalizedDescriptionKey: "primary red or secondary green pixels did not match: red=\(red), green=\(green)"])
    }
    let receipt: [String: Any] = [
        "result": "API17_DUAL_OUTPUT_PIXELS_PASS",
        "captureType": "actual_renderer_view_proof_png",
        "dimensions": [image.pixelsWide, image.pixelsHigh],
        "primaryType110Red": ["sample": red, "matches": redMatches],
        "secondaryType111Green": ["sample": green, "matches": greenMatches],
        "screenshot": args[0], "screenshotSha256": sha256(data)
    ]
    let output = try JSONSerialization.data(withJSONObject: receipt, options: [.prettyPrinted, .sortedKeys])
    try output.write(to: URL(fileURLWithPath: args[1]), options: .atomic)
    print("API17_DUAL_OUTPUT_PIXELS_PASS red_type110=true green_type111=true screenshot_sha256=\(sha256(data)) receipt=\(args[1])")
} catch {
    fputs("API17_DUAL_OUTPUT_PIXELS_FAIL \(error.localizedDescription)\n", stderr)
    exit(1)
}
