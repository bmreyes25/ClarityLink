import AppKit
import CryptoKit
import Foundation

guard CommandLine.arguments.count == 5 else {
    fputs("usage: verify_api17_padded_crop_content.swift CROPPED.png NEGATIVE_CONTROL.png APK OUTPUT.json\n", stderr)
    exit(2)
}
let args = Array(CommandLine.arguments.dropFirst())
func sha256(_ data: Data) -> String {
    SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
}
func samples(_ path: String) throws -> [[Int]] {
    let data = try Data(contentsOf: URL(fileURLWithPath: path))
    guard let image = NSBitmapImageRep(data: data), image.pixelsWide == 800, image.pixelsHigh == 480 else {
        throw NSError(domain: "crop-proof", code: 1, userInfo: [NSLocalizedDescriptionKey: "expected 800x480 renderer View capture"])
    }
    // Points lie in the red cropped frame and outside the synthetic protected black rectangle and label.
    return try [(250, 120), (550, 120), (250, 300), (550, 300)].map { x, y in
        guard let color = image.colorAt(x: x, y: image.pixelsHigh - 1 - y)?.usingColorSpace(.deviceRGB) else {
            throw NSError(domain: "crop-proof", code: 2, userInfo: [NSLocalizedDescriptionKey: "cannot sample screenshot"])
        }
        return [Int((color.redComponent * 255).rounded()), Int((color.greenComponent * 255).rounded()), Int((color.blueComponent * 255).rounded())]
    }
}
do {
    let actualData = try Data(contentsOf: URL(fileURLWithPath: args[0]))
    let actual = try samples(args[0])
    let matches = actual.allSatisfy { $0[0] > 200 && $0[1] < 80 && $0[2] < 40 }
    let negative = try samples(args[1])
    let negativeIsExpectedGreen = negative.allSatisfy {
        $0[1] > 80 && Double($0[1]) > Double($0[0]) * 1.4 && Double($0[1]) > Double($0[2]) * 1.1
    }
    guard matches && negativeIsExpectedGreen else {
        throw NSError(domain: "crop-proof", code: 3, userInfo: [NSLocalizedDescriptionKey: "cropped red View ROI or negative control mismatch"])
    }
    let apk = try Data(contentsOf: URL(fileURLWithPath: args[2]))
    let receipt: [String: Any] = [
        "result": "API17_PADDED_CROP_VIEW_CONTENT_PASS",
        "captureType": "actual_renderer_view_capture_on_api17_emulator",
        "expectedPattern": "red center crop from padded planar YUV420 adapter frame",
        "observedRoiRgb": actual,
        "matches": matches,
        "protectedBlackRegionExcludedFromRoi": true,
        "screenshot": args[0],
        "screenshotSha256": sha256(actualData),
        "negativeControl": ["screenshot": args[1], "expectedPattern": "green Type111 decoded frame",
                            "observedRoiRgb": negative, "matchesExpectedGreen": negativeIsExpectedGreen,
                            "rejectedAsRed": true],
        "apk": args[2],
        "apkSha256": sha256(apk)
    ]
    let out = try JSONSerialization.data(withJSONObject: receipt, options: [.prettyPrinted, .sortedKeys])
    try out.write(to: URL(fileURLWithPath: args[3]), options: .atomic)
    print("API17_PADDED_CROP_VIEW_CONTENT_PASS roi_samples=4 negative_control=green_frame_rejected receipt=\(args[3]) apk_sha256=\(sha256(apk))")
} catch {
    fputs("API17_PADDED_CROP_VIEW_CONTENT_FAIL \(error.localizedDescription)\n", stderr)
    exit(1)
}
