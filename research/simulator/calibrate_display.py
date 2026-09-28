#!/usr/bin/env python3
"""Offline photo registration. Emits numeric evidence only; never image pixels.

Requires local OpenCV/numpy for estimation. A cast quad is inferred in one photo's
coordinates; it is not a calibrated instrument-panel safe area or native ABI proof.
"""
import argparse
import hashlib
import json
import math
import pathlib
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent
CAST_RECT = (0, 24, 584, 191)  # copied meter_civic.xml root + screen_cast padding


def validate_quad(quad, image_size):
    """Reject invalid, degenerate, crossing, or out-of-image extrapolations."""
    if len(quad) != 4 or any(len(p) != 2 for p in quad):
        return False
    width, height = image_size
    if any(not math.isfinite(v) for p in quad for v in p):
        return False
    if any(not (0 <= p[0] <= width and 0 <= p[1] <= height) for p in quad):
        return False
    crosses = []
    for i in range(4):
        a, b, c = quad[i], quad[(i + 1) % 4], quad[(i + 2) % 4]
        crosses.append((b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0]))
    area = abs(sum(quad[i][0]*quad[(i+1)%4][1]-quad[(i+1)%4][0]*quad[i][1]
                   for i in range(4))) / 2
    return area >= 16 and (all(c > 0 for c in crosses) or all(c < 0 for c in crosses))


def estimate_geometry(source_points, photo_points, photo_size, rect=CAST_RECT):
    """Robust registration with support/residual and resampling uncertainty gates."""
    import cv2
    import numpy as np
    src = np.asarray(source_points, dtype=np.float64).reshape(-1, 2)
    dst = np.asarray(photo_points, dtype=np.float64).reshape(-1, 2)
    rejected = {"accepted": False, "evidence": "unknown", "quad": None}
    if len(src) != len(dst) or len(src) < 12 or not np.isfinite(src).all() or not np.isfinite(dst).all():
        return dict(rejected, reason="fewer than 12 finite paired matches")
    cv2.setRNGSeed(20260927)
    matrix, mask = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
    if matrix is None or mask is None:
        return dict(rejected, reason="homography unavailable or degenerate")
    ok = mask.ravel().astype(bool)
    src, dst = src[ok], dst[ok]
    x, y, w, h = rect
    corners = np.float64([[x,y],[x+w,y],[x+w,y+h],[x,y+h]])
    projected = cv2.perspectiveTransform(corners[None], matrix)[0]
    residual = np.linalg.norm(cv2.perspectiveTransform(src[None], matrix)[0] - dst, axis=1)
    coverage = cv2.contourArea(cv2.convexHull(src.astype(np.float32))) / (w*h)
    spread = (np.ptp(src, axis=0) / [w,h]).tolist()
    metrics = {"inliers": int(len(src)), "inlierRatio": round(float(ok.mean()), 4),
               "medianResidualPhotoPx": round(float(np.median(residual)), 4),
               "p95ResidualPhotoPx": round(float(np.quantile(residual,.95)), 4),
               "sourceHullCoverage": round(coverage, 4),
               "sourceAxisCoverage": [round(v,4) for v in spread],
               "sourceInlierBounds": [src.min(0).round(3).tolist(), src.max(0).round(3).tolist()]}
    if (len(src) < 12 or ok.mean() < .5 or coverage < .2 or min(spread) < .35
            or np.quantile(residual,.95) > 3 or not validate_quad(projected.tolist(), photo_size)):
        return dict(rejected, reason="support/residual/projected geometry gate failed", **metrics)
    rng = np.random.default_rng(20260927)
    quads = []
    for _ in range(100):
        subset = rng.choice(len(src), max(8, int(len(src)*.75)), replace=False)
        fitted, _ = cv2.findHomography(src[subset],dst[subset],0)
        if fitted is not None:
            q = cv2.perspectiveTransform(corners[None],fitted)[0]
            if validate_quad(q.tolist(),photo_size):
                quads.append(q)
    if len(quads) < 90:
        return dict(rejected, reason="unstable resampled projected geometry", **metrics)
    bounds = np.quantile(np.asarray(quads),[.025,.975],axis=0)
    return {"accepted": True, "evidence": "inferred from observed image feature correspondences",
            "quad": projected.round(3).tolist(), **metrics,
            "resampling": {"count":len(quads), "corner95PercentIntervalsPhotoPx":bounds.round(3).tolist(),
                           "meaning":"algorithm sensitivity only; not physical-boundary confidence"}}


def register_photo(frame_path, photo_path):
    import cv2
    import numpy as np
    frame = cv2.imread(str(frame_path), cv2.IMREAD_GRAYSCALE)
    photo = cv2.imread(str(photo_path), cv2.IMREAD_GRAYSCALE)
    if frame is None or photo is None:
        raise ValueError("Missing local input image")
    if frame.shape != (480,800):
        raise ValueError("Expected observed 800x480 HDMI frame")
    x,y,w,h = CAST_RECT
    mask = np.zeros_like(frame)
    mask[y:y+h,x:x+w] = 255
    sift = cv2.SIFT_create(nfeatures=8000)
    keypoints, descriptors = sift.detectAndCompute(frame,mask)
    photo_keypoints, photo_descriptors = sift.detectAndCompute(photo,None)
    matches = []
    if descriptors is not None and photo_descriptors is not None and len(photo_descriptors)>=2:
        for pair in cv2.BFMatcher().knnMatch(descriptors,photo_descriptors,k=2):
            if len(pair)==2 and pair[0].distance < .72*pair[1].distance:
                matches.append(pair[0])
    result = estimate_geometry([keypoints[m.queryIdx].pt for m in matches],
                               [photo_keypoints[m.trainIdx].pt for m in matches],
                               (photo.shape[1],photo.shape[0]))
    result.update({"frame":{"source":"assets/"+frame_path.name,"sha256":hashlib.sha256(frame_path.read_bytes()).hexdigest(),"size":[800,480]},
                   "photo":{"source":"assets/"+photo_path.name,"sha256":hashlib.sha256(photo_path.read_bytes()).hexdigest(),"size":[photo.shape[1],photo.shape[0]]},
                   "keypoints":[len(keypoints),len(photo_keypoints)],"ratioMatches":len(matches)})
    return result


def make_calibration():
    import cv2
    config = ROOT/'working-backup/meter_civic.xml'
    android = '{http://schemas.android.com/apk/res/android}'
    layout = ET.parse(config).getroot()
    cast = next(element for element in layout.iter()
                if element.attrib.get(android+'id') == '@id/screen_cast_layout')
    width = int(float(layout.attrib[android+'layout_width'].removesuffix('px')))
    height = int(float(layout.attrib[android+'layout_height'].removesuffix('px')))
    padding = int(float(cast.attrib[android+'paddingTop'].removesuffix('px')))
    if (0,padding,width,height-padding) != CAST_RECT:
        raise ValueError('Copied cast configuration changed; review source rectangle before recalibrating')
    photo_references = []
    for stem in ('cluster','maps','carplay-home','music','honda-home'):
        source = ROOT.parents[1]/'research/captures'/f'20260925T150706Z-physical-{stem}.jpg'
        asset = ROOT/'assets'/f'physical-{stem}-20260925.jpg'
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if hashlib.sha256(asset.read_bytes()).hexdigest() != digest:
            raise ValueError('Saved photo copy mismatch')
        photo_references.append({'source':str(source.relative_to(ROOT.parents[1])),
                                 'asset':'assets/'+asset.name,'sha256':digest,
                                 'bytes':source.stat().st_size,'copyVerified':True})
    pairs = [("maps","cluster-20260925-cast-maps.png","physical-maps-20260925.jpg"),
             ("music","cluster-20260925-cast-music.png","physical-music-20260925.jpg")]
    return {"schemaVersion":1,"method":{"name":"SIFT ratio .72, RANSAC 3 photo pixels; deterministic resampling", "opencv":cv2.__version__,"seed":20260927},
            "sourceCastRectangle":{"xywh":list(CAST_RECT),"evidence":"inferred: copied XML layout/padding agrees with observed HDMI content start", "source":"working-backup/meter_civic.xml","sourceLines":[2,74,75],"sha256":hashlib.sha256((ROOT/'working-backup/meter_civic.xml').read_bytes()).hexdigest()},
            "photoReferences":photo_references,
            "registrations":{name:register_photo(ROOT/'assets'/frame,ROOT/'assets'/photo) for name,frame,photo in pairs},
            "home":{"accepted":False,"quad":None,"evidence":"unknown","reason":"no saved HDMI CarPlay Home frame paired to physical Home photo; shared UI chrome is insufficient"},
            "physicalNavigationSafeBounds":{"rectangle":None,"calibrated":False,"evidence":"unknown: photo registrations locate cast content, not safe edge clearance or panel-native pixel coordinates"},
            "rendererViewport":{"evidence":"synthetic","meaning":"browser schematic uses a proposed viewport; it is not these photo coordinates"},
            "limitations":["Photos and saved frames are not atomic pairs; matched content correspondence is inferred.","Maps support occupies left portion of cast rectangle; right corners extrapolate beyond matched features.","Camera poses differ; quads cannot be combined into one physical panel rectangle.","Resampling excludes camera distortion, crop changes and incorrect boundary semantics.","No physical safety clearance, CarPlay protocol capability or native receiver execution is established."]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=pathlib.Path,default=ROOT/'photo-calibration.json')
    args = parser.parse_args()
    result=make_calibration()
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({name:{key:item[key] for key in ('accepted','inliers','medianResidualPhotoPx','quad')} for name,item in result['registrations'].items()}))
