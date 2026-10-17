import unittest
from sample_app import average

class TestAverage(unittest.TestCase):
    def test_average_empty_list(self):
        # Ensure that calling average with an empty list does not raise ZeroDivisionError
        try:
            average([])
        except ZeroDivisionError:
            self.fail("average([]) raised ZeroDivisionError")

if __name__ == "__main__":
    unittest.main()
