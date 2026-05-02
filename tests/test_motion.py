import unittest

from wavehome.motion import MotionDetector


class MotionDetectorTests(unittest.TestCase):
    def test_detects_swipe_right(self):
        detector = MotionDetector(min_distance=0.10)

        self.assertIsNone(detector.update((0.20, 0.50), 0.0))
        self.assertIsNone(detector.update((0.26, 0.51), 0.1))
        self.assertEqual(detector.update((0.36, 0.51), 0.2), "SWIPE_RIGHT")

    def test_detects_swipe_left(self):
        detector = MotionDetector(min_distance=0.10)

        self.assertIsNone(detector.update((0.50, 0.50), 0.0))
        self.assertIsNone(detector.update((0.42, 0.50), 0.1))
        self.assertEqual(detector.update((0.32, 0.50), 0.2), "SWIPE_LEFT")

    def test_ignores_small_motion(self):
        detector = MotionDetector(min_distance=0.20)

        self.assertIsNone(detector.update((0.50, 0.50), 0.0))
        self.assertIsNone(detector.update((0.55, 0.50), 0.1))
        self.assertIsNone(detector.update((0.60, 0.50), 0.2))


if __name__ == "__main__":
    unittest.main()
