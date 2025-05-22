import unittest
from unittest.mock import patch
from validation import validate_prerequisites, validate_core_curriculum, perform_course_validation

class TestValidation(unittest.TestCase):

    def test_validate_prerequisites_missing(self):
        student_courses = [{'courseCode': 'COSC 290', 'completed': False}]
        all_courses = {
            'cosc_courses': {
                'courses': [{'courseCode': 'COSC 290', 'prerequisites': ['COSC 236']}]
            }
        }
        result = validate_prerequisites(student_courses, all_courses)
        self.assertFalse(result['valid'])

    def test_validate_core_curriculum(self):
        student_courses = [{'courseCode': 'TSEM 102', 'completed': True}]
        core_curriculum = {
            'core_categories': [
                {'coreTitle': 'First-Year Seminar', 'courses': ['TSEM 102']},
                {'coreTitle': 'Math', 'courses': ['MATH 273']}
            ]
        }
        result = validate_core_curriculum(student_courses, core_curriculum)
        self.assertFalse(result['valid'])
        self.assertEqual(len(result['completedCore']), 1)

    @patch('validation.load_course_data')
    def test_perform_course_validation_with_mock(self, mock_load_data):
        mock_data = {
            'cosc_courses': {'courses': [{'courseCode': 'COSC 236'}]},
            'math_courses': {'courses': [{'courseCode': 'MATH 273'}]},
            'software_track': {
                'courses': {
                    'requiredComputerScience': [{'courseCode': 'COSC 236'}],
                    'requiredSoftwareEngineering': [],
                    'requiredMath': [{'courseCode': 'MATH 273'}],
                    'electiveSoftwareEngineering': [],
                }
            },
            'core_curriculum': {
                'core_categories': [{
                    'coreTitle': 'Mathematics',
                    'courses': ['MATH 273']
                }]
            }
        }
        mock_load_data.return_value = mock_data
        student_courses = [
            {'courseCode': 'COSC 236', 'completed': True},
            {'courseCode': 'MATH 273', 'completed': True}
        ]
        result = perform_course_validation(student_courses, mock_data)
        self.assertTrue(result["coreRequirements"]["valid"])
        self.assertTrue(result["majorRequirements"]["valid"])
