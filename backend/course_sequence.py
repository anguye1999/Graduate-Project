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

def calculate_course_priority(course_code, completed_courses, remaining_courses, course_data, current_term=1):
    """
    Calculate a priority score for a course based on:
    1. Course sequence/term in the degree plan
    2. Prerequisites and dependencies
    3. Course level
    4. How many other courses depend on it
    
    Args:
        course_code: The code of the course to check
        completed_courses: List of course codes the student has completed
        remaining_courses: List of courses still to be taken
        course_data: Dictionary of course information
        current_term: The current term being planned (1=Freshman Term 1, etc.)
        
    Returns:
        Priority score (higher means higher priority)
    """
    # Define reference sequence from degree plan
    reference_sequence = {
        # Freshman Term 1 (term 1)
        "COSC 175": {"term": 1, "season": "Fall", "priority": 100},
        "MATH 273": {"term": 1, "season": "Fall", "priority": 100},
        "PHYS 241": {"term": 1, "season": "Fall", "priority": 90},
        "TSEM 102": {"term": 1, "season": "Fall", "priority": 90},
        
        # Freshman Term 2 (term 2)
        "COSC 236": {"term": 2, "season": "Spring", "priority": 100},
        "PHYS 242": {"term": 2, "season": "Spring", "priority": 90},
        "ENGL 102": {"term": 2, "season": "Spring", "priority": 90},
        "MATH 274": {"term": 2, "season": "Spring", "priority": 95},
        
        # Sophomore Term 1 (term 3)
        "COSC 237": {"term": 3, "season": "Fall", "priority": 100},
        "CIS 377": {"term": 3, "season": "Fall", "priority": 90},
        "COMM 131": {"term": 3, "season": "Fall", "priority": 85},
        "MATH 263": {"term": 3, "season": "Fall", "priority": 95},
        "ECON 201": {"term": 3, "season": "Fall", "priority": 80},
        
        # Sophomore Term 2 (term 4)
        "COSC 336": {"term": 4, "season": "Spring", "priority": 100},
        "COSC 290": {"term": 4, "season": "Spring", "priority": 95},
        "MATH 330": {"term": 4, "season": "Spring", "priority": 90},
        "COSC 109": {"term": 4, "season": "Spring", "priority": 85},
        
        # Junior Term 1 (term 5)
        "COSC 412": {"term": 5, "season": "Fall", "priority": 95},
        "COSC 350": {"term": 5, "season": "Fall", "priority": 95},
        "COSC 436": {"term": 5, "season": "Fall", "priority": 90},
        "ENGL 317": {"term": 5, "season": "Fall", "priority": 85},
        "COSC 439": {"term": 5, "season": "Fall", "priority": 90},
        
        # Junior Term 2 (term 6)
        "COSC 455": {"term": 6, "season": "Spring", "priority": 95},
        "COSC 457": {"term": 6, "season": "Spring", "priority": 95},
        "COSC 418": {"term": 6, "season": "Spring", "priority": 90},
        "MATH 275": {"term": 6, "season": "Spring", "priority": 90},
        "FMST 201": {"term": 6, "season": "Spring", "priority": 85},
        
        # Senior Term 1 (term 7)
        "COSC 432": {"term": 7, "season": "Fall", "priority": 95},
        "COSC 435": {"term": 7, "season": "Fall", "priority": 95},
        "HIST 146": {"term": 7, "season": "Fall", "priority": 85},
        "ENGL 241": {"term": 7, "season": "Fall", "priority": 85},
        "CHNS 101": {"term": 7, "season": "Fall", "priority": 80},
        
        # Senior Term 2 (term 8)
        "COSC 442": {"term": 8, "season": "Spring", "priority": 95},
        "COSC 484": {"term": 8, "season": "Spring", "priority": 95},
        "COSC 490": {"term": 8, "season": "Spring", "priority": 100},
        "EMF 210": {"term": 8, "season": "Spring", "priority": 85},
        "ART 161": {"term": 8, "season": "Spring", "priority": 80}
    }
    
    # Check if course exists in reference sequence
    if course_code not in reference_sequence:
        # For unknown courses, estimate term based on course level
        try:
            parts = course_code.split()
            if len(parts) == 2:
                course_level = int(parts[1][0])  # First digit of course number
                estimated_term = max(1, min(8, course_level * 2))
                term_priority = 50  # Default medium priority for unknown courses
            else:
                term_priority = 50
                estimated_term = 4  # Default to middle of program
        except:
            term_priority = 50
            estimated_term = 4
    else:
        # Use reference sequence for known courses
        term_priority = reference_sequence[course_code]["priority"]
        estimated_term = reference_sequence[course_code]["term"]
    
    # Find course in course data
    course_info = None
    for course in course_data.get('cosc_courses', {}).get('courses', []):
        if course.get('courseCode') == course_code:
            course_info = course
            break
    
    # Check prerequisites
    has_prereq_issue = False
    if course_info and course_info.get('prerequisites'):
        prerequisites = course_info.get('prerequisites', [])
        
        for prereq in prerequisites:
            if isinstance(prereq, list):
                # This is a "one of" prerequisite - at least one must be completed
                prereq_met = False
                for option in prereq:
                    if option in completed_courses:
                        prereq_met = True
                        break
                if not prereq_met:
                    has_prereq_issue = True
            elif " or " in prereq:
                # "or" condition in prerequisite
                prereq_options = prereq.split(" or ")
                prereq_met = False
                for option in prereq_options:
                    if option.strip() in completed_courses:
                        prereq_met = True
                        break
                if not prereq_met:
                    has_prereq_issue = True
            elif prereq not in completed_courses:
                has_prereq_issue = True
    
    # If prerequisites are not met, give this course a very low priority
    if has_prereq_issue:
        return -100
    
    # Term distance factor - prioritize courses from terms closer to current term
    # This ensures we follow the natural curriculum progression
    term_distance = estimated_term - current_term
    
    if term_distance < 0:
        # This course belongs to a previous term - high priority to catch up
        term_factor = 50
    elif term_distance == 0:
        # This course is right on track - highest priority
        term_factor = 100
    elif term_distance == 1:
        # Next term course - good priority
        term_factor = 60
    elif term_distance == 2:
        # Two terms ahead - lower priority
        term_factor = 30
    else:
        # Too far ahead - very low priority
        term_factor = max(0, 50 - term_distance * 10)
    
    # Calculate dependency factor - courses that other courses depend on get higher priority
    dependency_factor = 0
    for course in course_data.get('cosc_courses', {}).get('courses', []):
        if course.get('courseCode') not in remaining_courses:
            continue
            
        prerequisites = course.get('prerequisites', [])
        
        # Check direct prerequisites
        if course_code in prerequisites:
            dependency_factor += 20
            continue
            
        # Check prerequisites that are lists ("one of" options)
        for prereq in prerequisites:
            if isinstance(prereq, list) and course_code in prereq:
                dependency_factor += 10
                break
    
    # Course level factor - lower level courses generally come first
    level_factor = 0
    try:
        parts = course_code.split()
        if len(parts) == 2:
            course_level = int(parts[1][0])  # First digit of course number
            level_factor = 100 - (course_level * 15)  # Higher level = lower priority
    except:
        level_factor = 50  # Default if we can't determine level
    
    # Final priority calculation (weighted sum of factors)
    priority = (
        (term_priority * 0.3) +       # Base priority from reference sequence
        (term_factor * 0.4) +         # Term sequencing factor (highest weight)
        (dependency_factor * 0.2) +   # How many courses depend on this
        (level_factor * 0.1)          # Course level factor (lowest weight)
    )
    
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
    
    # Identify required courses
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
    
    # Add math courses
    for course in course_data.get('software_track', {}).get('courses', {}).get('requiredMath', []):
        if isinstance(course, dict) and 'courseCode' in course:
            required_courses.add(course['courseCode'])
        elif isinstance(course, str):
            required_courses.add(course)
    
    # Add elective courses
    elective_courses = set()
    for course in course_data.get('software_track', {}).get('courses', {}).get('electiveSoftwareEngineering', []):
        if isinstance(course, dict) and 'courseCode' in course:
            elective_courses.add(course['courseCode'])
        elif isinstance(course, str):
            elective_courses.add(course)
    
    # Filter out courses that have already been completed
    remaining_required = [course for course in required_courses if course not in completed_courses]
    remaining_electives = [course for course in elective_courses if course not in completed_courses]
    
    # We need at least two electives for the Software Engineering track
    electives_needed = 2
    electives_to_add = min(electives_needed, len(remaining_electives))
    if electives_to_add > 0:
        # Add the most appropriate electives based on curriculum sequence
        sorted_electives = sorted(remaining_electives, key=lambda e: 
                                 calculate_course_priority(e, completed_courses, 
                                                         remaining_required + remaining_electives, 
                                                         course_data), 
                                 reverse=True)
        remaining_required.extend(sorted_electives[:electives_to_add])
    
    # Start building the semester plan
    semesters = []
    current_semester_season = start_semester
    remaining_courses = remaining_required.copy()
    current_term = 1  # Start with term 1 (Freshman Term 1)
    
    # Determine current term based on completed courses
    term_mapping = {
        # Course code -> term mapping based on the reference sequence
        "COSC 175": 1, "MATH 273": 1, "PHYS 241": 1, "TSEM 102": 1,  # Term 1
        "COSC 236": 2, "PHYS 242": 2, "ENGL 102": 2, "MATH 274": 2,  # Term 2
        "COSC 237": 3, "CIS 377": 3, "COMM 131": 3, "MATH 263": 3, "ECON 201": 3,  # Term 3
        "COSC 336": 4, "COSC 290": 4, "MATH 330": 4, "COSC 109": 4,  # Term 4
        "COSC 412": 5, "COSC 350": 5, "COSC 436": 5, "ENGL 317": 5, "COSC 439": 5,  # Term 5
        "COSC 455": 6, "COSC 457": 6, "COSC 418": 6, "MATH 275": 6, "FMST 201": 6,  # Term 6
        "COSC 432": 7, "COSC 435": 7, "HIST 146": 7, "ENGL 241": 7, "CHNS 101": 7,  # Term 7
        "COSC 442": 8, "COSC 484": 8, "COSC 490": 8, "EMF 210": 8, "ART 161": 8  # Term 8
    }
    
    # Get the highest term from completed courses to set the current term
    for course in completed_courses:
        if course in term_mapping:
            term = term_mapping[course]
            current_term = max(current_term, term + 1)  # Move to the next term
    
    # Continue planning until all required courses are scheduled
    while remaining_courses:
        current_semester = []
        
        # Calculate priorities for all remaining courses
        course_priorities = []
        for course in remaining_courses:
            priority = calculate_course_priority(course, completed_courses, 
                                                remaining_courses, course_data, 
                                                current_term)
            course_priorities.append((course, priority))
        
        # Sort by priority (highest first)
        course_priorities.sort(key=lambda x: x[1], reverse=True)
        
        # Check if any courses can be taken this semester
        viable_courses = []
        for course, priority in course_priorities:
            if priority > -50:  # Course is viable if priority is above threshold
                viable_courses.append((course, priority))
        
        # If no viable courses found, we might have prerequisite issues
        if not viable_courses:
            # Try the next term
            current_term += 1
            if current_term > 8:  # Reset if we've reached the end of the program
                current_term = 1
            
            # Toggle semester season
            current_semester_season = "Spring" if current_semester_season == "Fall" else "Fall"
            continue
        
        # Add courses to the current semester until full
        while viable_courses and len(current_semester) < max_courses_per_semester:
            course_to_add = viable_courses.pop(0)[0]
            current_semester.append(course_to_add)
            remaining_courses.remove(course_to_add)
            
            # Update completed courses for prerequisite checking
            completed_courses.append(course_to_add)
            
            # Recalculate priorities for remaining courses
            viable_courses = []
            for course in remaining_courses:
                priority = calculate_course_priority(course, completed_courses, 
                                                    remaining_courses, course_data, 
                                                    current_term)
                if priority > -50:  # Course is viable
                    viable_courses.append((course, priority))
            
            # Sort again
            viable_courses.sort(key=lambda x: x[1], reverse=True)
        
        # Add the current semester to the plan
        if current_semester:
            semesters.append({
                "semester": len(semesters) + 1,
                "season": current_semester_season,
                "term": current_term,  # Add term number for reference
                "courses": current_semester.copy()
            })
        
        # Advance to next term and toggle semester season
        current_term += 1
        current_semester_season = "Spring" if current_semester_season == "Fall" else "Fall"
        
        # Reset term counter if we've gone through all 8 terms
        if current_term > 8:
            current_term = 1
    
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