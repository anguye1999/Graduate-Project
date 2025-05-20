import unittest
from course_sequence import get_course_level, has_prerequisites_met

class TestCourseSequence(unittest.TestCase):
    
    def test_get_course_level_valid(self):
        self.assertEqual(get_course_level("COSC 236"), 2)
        self.assertEqual(get_course_level("MATH 101"), 1)
        self.assertEqual(get_course_level("ENGL 317"), 3)
    
    def test_get_course_level_invalid(self):
        self.assertEqual(get_course_level("INVALID"), 1)
        self.assertEqual(get_course_level(""), 1)
    
    def test_has_prerequisites_met_all_met(self):
        course_data = {
            "cosc_courses": {
                "courses": [
                    {"courseCode": "COSC 290", "prerequisites": ["COSC 236", "MATH 263"]}
                ]
            }
        }
        completed = ["COSC 236", "MATH 263"]
        self.assertTrue(has_prerequisites_met("COSC 290", completed, course_data))

    def test_has_prerequisites_met_not_met(self):
        course_data = {
            "cosc_courses": {
                "courses": [
                    {"courseCode": "COSC 290", "prerequisites": ["COSC 236", "MATH 263"]}
                ]
            }
        }
        completed = ["COSC 236"]
        self.assertFalse(has_prerequisites_met("COSC 290", completed, course_data))

if __name__ == '__main__':
    unittest.main()
