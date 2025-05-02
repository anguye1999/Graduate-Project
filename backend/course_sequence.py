"""
Course sequencing module for Towson University Computer Science program.
This module provides functions to generate a recommended course sequence
based on completed courses and degree requirements.
"""

import json
from collections import defaultdict
from datetime import datetime

def get_course_level(course_code):
    """Determine the course level based on the course number."""
    try:
        # Extract the course number from the course code (e.g., "COSC 236" -> "236")
        parts = course_code.split()
        if len(parts) != 2:
            return 1  # Default to level 1 if format is unexpected
        
        # Get the first digit of the course number to determine level
        number = parts[1]
        level = int(number[0])
        return level
    except (ValueError, IndexError):
        return 1  # Default to level 1 if parsing fails

def has_prerequisites_met(course_code, completed_courses, course_data):
    """
    Check if all prerequisites for a course are met.
    
    Args:
        course_code: The code of the course to check
        completed_courses: List of course codes the student has completed
        course_data: Dictionary of course information
        
    Returns:
        Boolean indicating if prerequisites are met
    """
    # Find the course in the course data
    course_info = None
    for course in course_data.get('cosc_courses', {}).get('courses', []):
        if course.get('courseCode') == course_code:
            course_info = course
            break
    
    if not course_info:
        return True  # If we can't find the course, assume no prerequisites
    
    # Get the prerequisites for the course
    prerequisites = course_info.get('prerequisites', [])
    
    # If no prerequisites, return True
    if not prerequisites:
        return True
    
    # Check each prerequisite
    for prereq in prerequisites:
        if isinstance(prereq, list):
            # This is a "one of" prerequisite group
            # At least one course in the list must be completed
            one_of_met = False
            for option in prereq:
                if option in completed_courses:
                    one_of_met = True
                    break
            
            if not one_of_met:
                return False
        else:
            # This is a required prerequisite
            # Check for "or" conditions in the prerequisite
            if " or " in prereq:
                options = prereq.split(" or ")
                options = [option.strip() for option in options]
                
                or_met = False
                for option in options:
                    if option in completed_courses:
                        or_met = True
                        break
                
                if not or_met:
                    return False
            elif prereq not in completed_courses:
                return False
    
    return True

def has_corequisites_met(course_code, completed_courses, planned_semester, course_data):
    """
    Check if corequisites for a course are met.
    Corequisites can be satisfied by either:
    1. Having already completed the corequisite
    2. Planning to take the corequisite in the same semester
    
    Args:
        course_code: The code of the course to check
        completed_courses: List of course codes the student has completed
        planned_semester: List of courses planned for the current semester
        course_data: Dictionary of course information
        
    Returns:
        Boolean indicating if corequisites are met
    """
    # Find the course in the course data
    course_info = None
    for course in course_data.get('cosc_courses', {}).get('courses', []):
        if course.get('courseCode') == course_code:
            course_info = course
            break
    
    if not course_info:
        return True  # If we can't find the course, assume no corequisites
    
    # Check if course has corequisites
    corequisites = course_info.get('corequisites', [])
    
    if not corequisites:
        return True  # No corequisites, so we're good
    
    # Make sure corequisites are in a list format
    if isinstance(corequisites, str):
        corequisites = [corequisites]
    
    # Check each corequisite
    for coreq in corequisites:
        # Corequisite is met if:
        # 1. It's already completed, or
        # 2. It's planned for the current semester
        if coreq not in completed_courses and coreq not in planned_semester:
            return False
    
    return True

def is_course_available(course_code, semester_season, course_data):
    """
    Check if a course is offered in the given semester.
    
    Args:
        course_code: The code of the course to check
        semester_season: "Fall" or "Spring"
        course_data: Dictionary of course information
        
    Returns:
        Boolean indicating if the course is available
    """
    # Find the course in the course data
    course_info = None
    for course in course_data.get('cosc_courses', {}).get('courses', []):
        if course.get('courseCode') == course_code:
            course_info = course
            break
    
    if not course_info:
        return True  # If we can't find the course, assume it's offered
    
    # Get the offerings for the course
    offerings = course_info.get('offerings', [])
    
    # If no offering information, assume it's offered
    if not offerings:
        return True
    
    # Check if the course is offered in the given semester
    return semester_season in offerings

def calculate_course_priority(course_code, remaining_courses, course_data):
    """
    Calculate a priority score for a course based on:
    1. How many other courses depend on it
    2. Course level (lower-level courses get higher priority)
    
    Args:
        course_code: The code of the course to check
        remaining_courses: List of courses still to be taken
        course_data: Dictionary of course information
        
    Returns:
        Priority score (higher means higher priority)
    """
    # Calculate how many other courses depend on this course
    dependent_courses = 0
    
    for course in course_data.get('cosc_courses', {}).get('courses', []):
        if course.get('courseCode') not in remaining_courses:
            continue
            
        prerequisites = course.get('prerequisites', [])
        
        # Check if this course is a direct prerequisite
        if course_code in prerequisites:
            dependent_courses += 1
            continue
            
        # Check if this course is part of a "one of" prerequisite group
        for prereq in prerequisites:
            if isinstance(prereq, list) and course_code in prereq:
                dependent_courses += 0.5  # Lower weight for "one of" prerequisites
                break
    
    # Get course level (1-4)
    course_level = get_course_level(course_code)
    
    # Priority formula: dependent courses + (5 - level)
    # This prioritizes courses with more dependents and lower level courses
    priority = dependent_courses + (5 - course_level)
    
    # Boost priority for key courses in the curriculum
    key_courses = {
        "COSC 175": 10,  # Starting CS course
        "COSC 236": 9,   # Intro to CS I
        "COSC 237": 8,   # Intro to CS II
        "COSC 336": 7,   # Data Structures (gateway to many courses)
        "COSC 290": 6,   # Computer Organization
        "MATH 273": 5,   # Calculus I
        "COSC 350": 4,   # Data Communications and Networking
        "COSC 412": 3,   # Software Engineering
    }
    
    if course_code in key_courses:
        priority += key_courses[course_code]
    
    # Check if it's a required course for the software engineering track
    software_track_required = []
    for course in course_data.get('software_track', {}).get('courses', {}).get('requiredComputerScience', []):
        if isinstance(course, dict) and 'courseCode' in course:
            software_track_required.append(course['courseCode'])
    
    for course in course_data.get('software_track', {}).get('courses', {}).get('requiredSoftwareEngineering', []):
        if isinstance(course, dict) and 'courseCode' in course:
            software_track_required.append(course['courseCode'])
        elif isinstance(course, str):
            software_track_required.append(course)
    
    if course_code in software_track_required:
        priority += 2  # Boost priority for required courses
    
    return priority

def generate_course_sequence(student_courses, course_data, start_semester="Fall", max_courses_per_semester=5):
    """
    Generate a semester-by-semester plan for completing a degree.
    
    Args:
        student_courses: List of courses the student has taken
        course_data: Dictionary of course information
        start_semester: Which semester to start with ("Fall" or "Spring")
        max_courses_per_semester: Maximum number of courses per semester
        
    Returns:
        List of semester plans, each containing a list of courses
    """
    # Extract completed courses
    completed_courses = [course['courseCode'] for course in student_courses if course.get('completed', True)]
    
    # Identify major courses requirements
    required_courses = set()
    
    # Add required Computer Science courses
    for course in course_data.get('software_track', {}).get('courses', {}).get('requiredComputerScience', []):
        if isinstance(course, dict) and 'courseCode' in course:
            required_courses.add(course['courseCode'])
        elif isinstance(course, str):
            required_courses.add(course)
    
    # Add required Software Engineering courses
    for course in course_data.get('software_track', {}).get('courses', {}).get('requiredSoftwareEngineering', []):
        if isinstance(course, dict) and 'courseCode' in course:
            required_courses.add(course['courseCode'])
        elif isinstance(course, str):
            required_courses.add(course)
    
    # Add elective Software Engineering courses (we'll need some of these)
    elective_courses = set()
    for course in course_data.get('software_track', {}).get('courses', {}).get('electiveSoftwareEngineering', []):
        if isinstance(course, dict) and 'courseCode' in course:
            elective_courses.add(course['courseCode'])
        elif isinstance(course, str):
            elective_courses.add(course)
    
    # Filter out courses that have already been completed
    remaining_required = [course for course in required_courses if course not in completed_courses]
    remaining_electives = [course for course in elective_courses if course not in completed_courses]
    
    # We need at least one elective for the Software Engineering track
    if len(remaining_electives) > 0 and all(course not in completed_courses for course in elective_courses):
        remaining_required.append(remaining_electives[0])
    
    # Start building the semester plan
    semesters = []
    current_semester = []
    current_semester_season = start_semester
    remaining_courses = remaining_required.copy()
    
    # Continue planning until all required courses are scheduled
    while remaining_courses:
        # Find courses that can be taken this semester
        available_courses = []
        
        for course in remaining_courses:
            # Check if prerequisites and corequisites are met
            if has_prerequisites_met(course, completed_courses, course_data) and \
               has_corequisites_met(course, completed_courses, current_semester, course_data) and \
               is_course_available(course, current_semester_season, course_data):
                available_courses.append(course)
        
        # If no courses can be taken, we might have a prerequisite loop or missing data
        if not available_courses:
            # Force add the remaining courses to finish the plan
            # This shouldn't happen with well-formed data, but provides a fallback
            current_semester.extend(remaining_courses[:max_courses_per_semester - len(current_semester)])
            remaining_courses = remaining_courses[max_courses_per_semester - len(current_semester):]
            
            if current_semester:
                semesters.append({
                    "semester": len(semesters) + 1,
                    "season": current_semester_season,
                    "courses": current_semester.copy()
                })
                
            # Reset for next semester
            current_semester = []
            current_semester_season = "Spring" if current_semester_season == "Fall" else "Fall"
            
            if not remaining_courses:
                break
                
            continue
        
        # Calculate priority for each available course
        course_priorities = [(course, calculate_course_priority(course, remaining_courses, course_data)) 
                           for course in available_courses]
        
        # Sort by priority (highest first)
        course_priorities.sort(key=lambda x: x[1], reverse=True)
        
        # Add courses to the current semester until it's full
        while course_priorities and len(current_semester) < max_courses_per_semester:
            course_to_add = course_priorities.pop(0)[0]
            current_semester.append(course_to_add)
            remaining_courses.remove(course_to_add)
            
            # Update the list of completed courses
            completed_courses.append(course_to_add)
            
            # Recalculate which courses are available
            available_courses = []
            for course in remaining_courses:
                if has_prerequisites_met(course, completed_courses, course_data) and \
                   has_corequisites_met(course, completed_courses, current_semester, course_data) and \
                   is_course_available(course, current_semester_season, course_data):
                    available_courses.append(course)
            
            # Recalculate priorities
            course_priorities = [(course, calculate_course_priority(course, remaining_courses, course_data)) 
                               for course in available_courses]
            course_priorities.sort(key=lambda x: x[1], reverse=True)
        
        # Add the current semester to the plan
        if current_semester:
            semesters.append({
                "semester": len(semesters) + 1,
                "season": current_semester_season,
                "courses": current_semester.copy()
            })
        
        # Reset for next semester
        current_semester = []
        current_semester_season = "Spring" if current_semester_season == "Fall" else "Fall"
    
    return semesters

def get_course_details(course_code, course_data):
    """Get course details for display in the UI."""
    # Look in COSC courses first
    for course in course_data.get('cosc_courses', {}).get('courses', []):
        if course.get('courseCode') == course_code:
            return {
                'code': course_code,
                'credits': course.get('units', 3),
                'description': course.get('description', '')
            }
    
    # Check other course collections if not found
    course_collections = [
        course_data.get('software_track', {}).get('courses', {}).get('requiredComputerScience', []),
        course_data.get('software_track', {}).get('courses', {}).get('requiredSoftwareEngineering', []),
        course_data.get('software_track', {}).get('courses', {}).get('electiveSoftwareEngineering', []),
        course_data.get('software_track', {}).get('courses', {}).get('requiredMath', []),
        course_data.get('software_track', {}).get('courses', {}).get('scienceRequirement', []),
    ]
    
    for collection in course_collections:
        for course in collection:
            if isinstance(course, dict) and course.get('courseCode') == course_code:
                return {
                    'code': course_code,
                    'credits': course.get('units', 3),
                    'description': course.get('description', '')
                }
    
    # Return basic info if course not found
    return {
        'code': course_code,
        # 'title': 'Unknown Course',
        'credits': 3,
        'description': ''
    }

def get_detailed_semester_plan(semester_plan, course_data):
    """
    Enhance the semester plan with detailed course information.
    
    Args:
        semester_plan: List of semesters with course codes
        course_data: Dictionary of course information
        
    Returns:
        Detailed semester plan with course information
    """
    detailed_plan = []
    
    for semester in semester_plan:
        semester_number = semester.get('semester', 0)
        season = semester.get('season', 'Fall')
        courses = semester.get('courses', [])
        
        detailed_courses = []
        for course_code in courses:
            course_details = get_course_details(course_code, course_data)
            detailed_courses.append(course_details)
        
        # Calculate year and season for display
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # Determine starting point based on current date
        start_year = current_year
        
        # If we're past spring semester already, start next fall
        if current_month > 5 and season == "Fall":
            pass
        elif current_month > 5:
            start_year += 1
        
        # Calculate which year this semester would be in
        semester_offset = semester_number - 1
        year_offset = semester_offset // 2
        this_semester_year = start_year + year_offset
        
        detailed_plan.append({
            'semester': semester_number,
            'season': season,
            'year': this_semester_year,
            'name': f"{season} {this_semester_year}",
            'courses': detailed_courses
        })
    
    return detailed_plan

def generate_recommended_sequence(student_courses, course_data, track="Software Engineering"):
    """
    Main function to generate a recommended course sequence.
    
    Args:
        student_courses: List of courses the student has taken
        course_data: Dictionary of course information
        track: Degree track (default: "Software Engineering")
        
    Returns:
        Dictionary with recommended course sequence
    """
    # Determine which semester we're currently in (Fall or Spring)
    current_month = datetime.now().month
    start_semester = "Fall" if current_month >= 8 or current_month <= 1 else "Spring"
    next_semester = "Spring" if start_semester == "Fall" else "Fall"
    
    # Generate basic semester plan
    semester_plan = generate_course_sequence(
        student_courses, 
        course_data,
        start_semester=next_semester,  # Start with next semester
        max_courses_per_semester=5
    )
    
    # Generate detailed plan with course information
    detailed_plan = get_detailed_semester_plan(semester_plan, course_data)
    
    # Return both the high-level plan and detailed information
    return {
        "track": track,
        "semesterPlan": semester_plan,
        "detailedPlan": detailed_plan
    }