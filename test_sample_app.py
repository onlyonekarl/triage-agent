import unittest

from sample_app import average


class TestAverage(unittest.TestCase):
    def test_normal_list(self):
        self.assertEqual(average([1, 2, 3]), 2)


if __name__ == "__main__":
    unittest.main()