import unittest
from app import allowed_file, extract_course_mentions, validate_course_recommendations

class TestApp(unittest.TestCase):

    def test_allowed_file(self):
        self.assertTrue(allowed_file("test.csv"))
        self.assertTrue(allowed_file("doc.txt"))
        self.assertFalse(allowed_file("image.png"))

    def test_extract_course_mentions(self):
        text = "I've taken COSC 236 and MATH 263."
        mentions = extract_course_mentions(text)
        self.assertIn("COSC 236", mentions)
        self.assertIn("MATH 263", mentions)

    def test_validate_course_recommendations(self):
        completed = ["COSC 175", "COSC 236", "COSC 237", "MATH 263"]
        recs = ["COSC 290", "COSC 336", "COSC 437"]
        result = validate_course_recommendations(completed, recs)
        self.assertIn("COSC 290", result)
        self.assertIn("COSC 336", result)

if __name__ == '__main__':
    unittest.main()
