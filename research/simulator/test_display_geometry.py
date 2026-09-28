import math
import unittest

from calibrate_display import validate_quad, estimate_geometry

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = np = None


class GeometryContractTest(unittest.TestCase):
    def test_valid_projected_rectangle_and_rotated_quad(self):
        self.assertTrue(validate_quad([[2,2],[60,5],[58,40],[1,38]],(80,60)))
        self.assertTrue(validate_quad([[2,2],[2,40],[60,40],[60,2]],(80,60)))

    def test_invalid_geometry_cannot_be_advertised(self):
        for points in ([[0,0],[1,0],[1,1],[0,1]],  # collapsed region
                       [[0,0],[40,40],[0,40],[40,0]],  # crossing
                       [[0,0],[40,0],[40,40],[-1,40]],  # outside photo
                       [[0,0],[40,0],[40,math.inf],[0,40]],
                       [[0,0],[40,0],[10,10],[0,40]],  # concave
                       [[0,0],[40,0],[40,40]]):
            self.assertFalse(validate_quad(points,(80,60)))


@unittest.skipIf(cv2 is None, 'Optional local OpenCV/numpy environment required')
class RegistrationTest(unittest.TestCase):
    def test_recovers_known_projective_transform_despite_outliers(self):
        rng=np.random.default_rng(91)
        src=rng.uniform([0,24],[584,215],size=(150,2))
        matrix=np.array([[.8,.015,210],[.01,.8,180],[.0001,.00005,1.]])
        dst=cv2.perspectiveTransform(src[None],matrix)[0]
        noisy=dst+rng.normal(0,.18,dst.shape)
        noisy[:25]=rng.uniform([0,0],[1280,960],size=(25,2))
        result=estimate_geometry(src,noisy,(1280,960))
        self.assertTrue(result['accepted'])
        self.assertGreaterEqual(result['inliers'],120)
        truth=cv2.perspectiveTransform(np.float64([[[0,24],[584,24],[584,215],[0,215]]]),matrix)[0]
        self.assertLess(np.max(np.linalg.norm(np.asarray(result['quad'])-truth,axis=1)),1)
        self.assertLess(result['p95ResidualPhotoPx'],1)

    def test_missing_matches_are_unknown(self):
        result=estimate_geometry([],[],(1280,960))
        self.assertFalse(result['accepted'])
        self.assertIsNone(result['quad'])

    def test_collinear_matches_are_unknown(self):
        src=[[x,24] for x in range(0,584,20)]
        result=estimate_geometry(src,[[x+200,y+100] for x,y in src],(1280,960))
        self.assertFalse(result['accepted'])
        self.assertIsNone(result['quad'])

    def test_small_local_patch_does_not_calibrate_full_screen(self):
        rng=np.random.default_rng(9)
        src=rng.uniform([20,30],[45,50],size=(60,2))
        result=estimate_geometry(src,src+[300,400],(1280,960))
        self.assertFalse(result['accepted'])
        self.assertIsNone(result['quad'])

    def test_projection_outside_photo_rejected(self):
        rng=np.random.default_rng(8)
        src=rng.uniform([0,24],[584,215],size=(60,2))
        result=estimate_geometry(src,src+[1100,800],(1280,960))
        self.assertFalse(result['accepted'])
        self.assertIsNone(result['quad'])

    def test_nonfinite_pairs_rejected(self):
        result=estimate_geometry([[math.nan,3]]*15,[[5,6]]*15,(1280,960))
        self.assertFalse(result['accepted'])
        self.assertIsNone(result['quad'])


if __name__=='__main__':
    unittest.main()
