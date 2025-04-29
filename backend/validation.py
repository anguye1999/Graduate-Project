import os 
import json
from datetime import datetime
from collections import defaultdict

def load_course_data(app_directory):
    try:
        course_data = {}
        cosc_major_path = os.path.join(app_directory, 'cosc_major_no_course_title.json')
        software_track_path = os.path.join(app_directory, 'software_track_no_course_title.json')
        core_curriculum_path = os.path.join(app_directory, 'core_curriculum_no_course_title.json')
        math_courses_path = os.path.join(app_directory, 'math_courses_no_course_title.json')

        with open(cosc_major_path, 'r') as f:
            course_data['cosc_courses'] = json.load(f)

        with open(software_track_path, 'r') as f:
            course_data['software_track'] = json.load(f)
        
        with open(core_curriculum_path, 'r') as f:
            course_data['core_curriculum'] = json.load(f)

        with open(math_courses_path ,'r') as f:
            course_data['math_courses'] = json.load(f)
        
        print("Course data loaded successfully")
        return course_data
    except Exception as e:
        print(f"Error loading course data: {str(e)}")
        return None
    
def validate_prerequisites(student_courses, all_courses):
    """Check if student has prerequisites for courses they want to take"""
    validation_results = {
        "valid": True,
        "issues": [],
        "validCourses": []
    }
    
    # Extract course codes the student has already taken
    completed_course_codes = [course['courseCode'] for course in student_courses if course.get('completed', True)]
    
    # Courses the student wants to take next (not yet completed)
    planned_courses = [course for course in student_courses if not course.get('completed', True)]
    
    for course in planned_courses:
        course_code = course.get('courseCode')
        
        # Find course in our database
        course_info = None
        for c in all_courses.get('cosc_courses', {}).get('courses', []):
            if c.get('courseCode') == course_code:
                course_info = c
                break
        
        if not course_info:
            continue  # Skip if course not found
        
        # Check prerequisites
        if 'prerequisites' in course_info and course_info['prerequisites']:
            missing_prereqs = []
            
            for prereq in course_info['prerequisites']:
                # Handle prerequisite groups (where one of several courses is required)
                if isinstance(prereq, list):
                    # Check if at least one course in the list is completed
                    found = False
                    for option in prereq:
                        if option in completed_course_codes:
                            found = True
                            break
                    if not found:
                        missing_prereqs.append(f"one of: {', '.join(prereq)}")
                elif prereq not in completed_course_codes:
                    missing_prereqs.append(prereq)
            
            if missing_prereqs:
                validation_results["valid"] = False
                validation_results["issues"].append({
                    "courseWanted": course_code,
                    "missingPrerequisites": missing_prereqs,
                    "message": f"Cannot take {course_code} without first completing: {', '.join(missing_prereqs)}"
                })
            else:
                validation_results["validCourses"].append(course_code)
        else:
            validation_results["validCourses"].append(course_code)
    
    return validation_results

def validate_core_curriculum(student_courses, core_curriculum):
    """Check if student has completed core curriculum requirements"""
    validation_results = {
        "valid": True,
        "completedCore": [],
        "missingCore": []
    }
    
    # Extract course codes the student has completed
    completed_course_codes = [course['courseCode'] for course in student_courses if course.get('completed', True)]
    
    # Debug log
    print(f"Validating core curriculum with {len(completed_course_codes)} completed courses")
    
    # Check each core category
    for category in core_curriculum.get('core_categories', []):
        category_title = category.get('coreTitle', '')
        category_courses = category.get('courses', [])
        
        # Debug log
        print(f"Checking core category: {category_title} with {len(category_courses)} possible courses")
        
        # Check if student has completed any course in this category
        completed = False
        completed_course = None
        
        for core_course in category_courses:
            # Handle different course data formats
            core_course_code = ""
            if isinstance(core_course, dict):
                core_course_code = core_course.get('courseCode', '')
            elif isinstance(core_course, str):
                core_course_code = core_course
            
            # Debug log
            if core_course_code in completed_course_codes:
                print(f"Found completed core course: {core_course_code} for category {category_title}")
            
            if core_course_code in completed_course_codes:
                completed = True
                completed_course = core_course_code
                break
        
        if completed:
            validation_results["completedCore"].append({
                "category": category_title,
                "courseCode": completed_course,
                "completed": True
            })
        else:
            validation_results["missingCore"].append({
                "category": category_title,
                "completed": False
            })
            validation_results["valid"] = False
    
    return validation_results

def validate_major_requirements(student_courses, track, major_courses):
    """Check if student has completed major requirements for their track"""
    validation_results = {
        "valid": True,
        "track": track,
        "completedRequired": [],
        "missingRequired": [],
        "electivesNeeded": 0,
        "electivesCompleted": 0
    }
    
    # Extract course codes the student has completed
    completed_course_codes = [course['courseCode'] for course in student_courses if course.get('completed', True)]
    
    # Debug log
    print(f"Validating major requirements for track: {track} with {len(completed_course_codes)} completed courses")
    
    # Determine required courses based on track
    if track == "Software Engineering":
        # Get required courses for Software Engineering track
        required_courses = []
        
        # Add required computer science courses
        for course in major_courses.get('software_track', {}).get('courses', {}).get('requiredComputerScience', []):
            if isinstance(course, dict) and 'courseCode' in course:
                required_courses.append(course.get('courseCode'))
            elif isinstance(course, str):
                required_courses.append(course)
            
        # Add required software engineering courses
        for course in major_courses.get('software_track', {}).get('courses', {}).get('requiredSoftwareEngineering', []):
            if isinstance(course, dict) and 'courseCode' in course:
                required_courses.append(course.get('courseCode'))
            elif isinstance(course, str):
                required_courses.append(course)
            
        # Count electives needed
        electives_needed = 1  # Assuming 1 elective is needed for Software Engineering track
        validation_results["electivesNeeded"] = electives_needed
        
        # Debug log
        print(f"Required courses: {required_courses}")
        print(f"Electives needed: {electives_needed}")
        
        # Get elective courses
        elective_courses = []
        for course in major_courses.get('software_track', {}).get('courses', {}).get('electiveSoftwareEngineering', []):
            if isinstance(course, dict) and 'courseCode' in course:
                elective_courses.append(course.get('courseCode'))
            elif isinstance(course, str):
                elective_courses.append(course)
        
        # Check required courses
        for course_code in required_courses:
            if course_code in completed_course_codes:
                # Debug log
                print(f"Found completed required course: {course_code}")
                
                validation_results["completedRequired"].append({
                    "courseCode": course_code,
                    "completed": True
                })
            else:
                # Debug log
                print(f"Missing required course: {course_code}")
                
                validation_results["missingRequired"].append({
                    "courseCode": course_code,
                    "completed": False
                })
                validation_results["valid"] = False
        
        # Check electives - count how many electives have been completed
        electives_completed = 0
        for course_code in elective_courses:
            if course_code in completed_course_codes:
                # Debug log
                print(f"Found completed elective course: {course_code}")
                
                electives_completed += 1
        
        validation_results["electivesCompleted"] = electives_completed
        
        # Debug log
        print(f"Electives completed: {electives_completed}")
        
        # Fix: Only set valid to false if electives_completed < electives_needed
        if electives_completed < electives_needed:
            validation_results["valid"] = False
    
    # Add similar logic for other tracks (Cybersecurity, General Computer Science)
    
    return validation_results

def calculate_graduation_progress(student_courses, core_curriculum, major_courses, track="Software Engineering"):
    """Calculate overall graduation progress"""
    validation_results = {
        "totalCreditsEarned": 0,
        "totalCreditsRequired": 120,  # Typical for a bachelor's degree
        "percentageComplete": 0,
        "estimatedGraduationDate": "",
        "remainingCategories": {
            "coreRequirements": 0,
            "majorRequirements": 0,
            "electiveRequirements": 0
        }
    }
    
    # Extract completed courses
    completed_courses = [course for course in student_courses if course.get('completed', True)]
    
    # Calculate credits earned
    for course in completed_courses:
        course_code = course.get('courseCode')
        
        # Attempt to find the course across all collections
        course_found = False
        credit_value = 3  # Default fallback value
        
        # Search in COSC courses
        for c in major_courses.get('cosc_courses', {}).get('courses', []):
            if c.get('courseCode') == course_code:
                course_found = True
                # Handle case where units might be a list [min, max] or a string/int
                units = c.get('units', 3)
                if isinstance(units, list):
                    units = units[0]  # Take minimum units
                try:
                    credit_value = int(units)
                except (ValueError, TypeError):
                    credit_value = 3  # Fallback to 3 credits
                break
        
        # If not found in COSC, search in math courses
        if not course_found:
            for c in major_courses.get('math_courses', {}).get('courses', []):
                if c.get('courseCode') == course_code:
                    course_found = True
                    units = c.get('units', 3)
                    if isinstance(units, list):
                        units = units[0]
                    try:
                        credit_value = int(units)
                    except (ValueError, TypeError):
                        credit_value = 3
                    break
        
        # If still not found, check other collections from the software track
        if not course_found:
            collections = [
                'requiredComputerScience',
                'requiredSoftwareEngineering',
                'electiveSoftwareEngineering',
                'requiredMath',
                'scienceRequirement'
            ]
            
            for collection_name in collections:
                collection = major_courses.get('software_track', {}).get('courses', {}).get(collection_name, [])
                for c in collection:
                    if isinstance(c, dict) and c.get('courseCode') == course_code:
                        course_found = True
                        units = c.get('units', 3)
                        if isinstance(units, list):
                            units = units[0]
                        try:
                            credit_value = int(units)
                        except (ValueError, TypeError):
                            credit_value = 3
                        break
                
                if course_found:
                    break
        
        # Check if the course is part of core curriculum
        if not course_found:
            for category in core_curriculum.get('core_categories', []):
                for c in category.get('courses', []):
                    if isinstance(c, dict) and c.get('courseCode') == course_code:
                        course_found = True
                        units = c.get('units', 3)
                        if isinstance(units, list):
                            units = units[0]
                        try:
                            credit_value = int(units)
                        except (ValueError, TypeError):
                            credit_value = 3
                        break
                
                if course_found:
                    break
        
        # Estimate credits based on course level if still not found
        if not course_found:
            # Try to determine course level from code
            try:
                parts = course_code.split()
                if len(parts) == 2:
                    course_num = parts[1]
                    if course_num.isdigit() and len(course_num) >= 3:
                        # Higher level courses might have more credits
                        level = int(course_num[0])
                        if level >= 3:
                            credit_value = 4  # Upper division courses often have 4 credits
            except (ValueError, IndexError):
                pass  # Keep default 3 credits
        
        # Add the credits to total
        validation_results["totalCreditsEarned"] += credit_value
    
    # Calculate remaining requirements
    core_validation = validate_core_curriculum(student_courses, core_curriculum)
    major_validation = validate_major_requirements(student_courses, track, major_courses)
    
    validation_results["remainingCategories"]["coreRequirements"] = len(core_validation["missingCore"])
    validation_results["remainingCategories"]["majorRequirements"] = len(major_validation["missingRequired"])
    validation_results["remainingCategories"]["electiveRequirements"] = max(0, major_validation["electivesNeeded"] - major_validation["electivesCompleted"])
    
    # Calculate percentage complete
    if validation_results["totalCreditsRequired"] > 0:
        validation_results["percentageComplete"] = int((validation_results["totalCreditsEarned"] / validation_results["totalCreditsRequired"]) * 100)
    
    # Improved graduation date estimation
    # Assuming 15 credits per semester and 2 semesters per year normally
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    credits_remaining = validation_results["totalCreditsRequired"] - validation_results["totalCreditsEarned"]
    
    # If student has a consistent enrollment pattern, use that
    # For example, detect how many credits they typically take per semester
    typical_credits_per_term = 15  # Default
    
    # Calculate average credits per semester from completed courses if possible
    semester_credits = defaultdict(int)
    semester_count = 0
    
    for course in completed_courses:
        semester = course.get('semester')
        year = course.get('year')
        if semester and year:
            semester_key = f"{semester} {year}"
            # Get credit value using same logic as above
            # This is simplified for brevity - in a real implementation, reuse the credit finding logic
            credits = 3
            semester_credits[semester_key] += credits
    
    if semester_credits:
        avg_credits = sum(semester_credits.values()) / len(semester_credits)
        if avg_credits > 0:
            typical_credits_per_term = avg_credits
    
    # Calculate remaining semesters based on typical enrollment
    semesters_remaining = max(1, round(credits_remaining / typical_credits_per_term))
    
    # More accurate graduation month determination
    # Standard academic calendar: Fall (Aug-Dec), Spring (Jan-May), Summer (May/Jun-Aug)
    if current_month >= 1 and current_month <= 5:
        # Spring semester
        current_semester = "Spring"
    elif current_month >= 8 and current_month <= 12:
        # Fall semester
        current_semester = "Fall"
    else:
        # Summer
        current_semester = "Summer"
    
    # Calculate graduation term
    remaining_terms = []
    next_semester = current_semester
    next_year = current_year
    
    for i in range(semesters_remaining):
        if next_semester == "Fall":
            next_semester = "Spring"
            next_year += 1
        elif next_semester == "Spring":
            if credits_remaining <= 9:  # Summer graduation for light load
                next_semester = "Summer"
            else:
                next_semester = "Fall"
        else:  # Summer
            next_semester = "Fall"
    
    # Convert semester to month
    if next_semester == "Fall":
        graduation_month = "December"
    elif next_semester == "Spring":
        graduation_month = "May"
    else:  # Summer
        graduation_month = "August"
    
    validation_results["estimatedGraduationDate"] = f"{graduation_month} {next_year}"
    
    # Include more details
    validation_results["typicalCreditsPerTerm"] = typical_credits_per_term
    validation_results["creditsRemaining"] = credits_remaining
    validation_results["semestersRemaining"] = semesters_remaining
    
    return validation_results

def generate_validation_summary(validation_results):
    """Create a formatted summary of validation results for the Assistant API"""
    # Get missing requirements from major requirements
    major_missing = [course["courseCode"] for course in validation_results["majorRequirements"]["missingRequired"]]
    
    # Get missing core requirements
    core_missing = [category["category"] for category in validation_results["coreRequirements"]["missingCore"]]
    
    # Calculate electives needed
    electives_needed = validation_results["majorRequirements"]["electivesNeeded"]
    electives_completed = validation_results["majorRequirements"]["electivesCompleted"]
    electives_remaining = max(0, electives_needed - electives_completed)  # Ensure non-negative
    
    # If we've completed more electives than needed, set to zero
    if electives_completed >= electives_needed:
        electives_remaining = 0
    
    # Debug log
    print(f"Generating summary: Major missing: {major_missing}, Core missing: {core_missing}, Electives: {electives_completed}/{electives_needed}")
    
    summary = {
        "studentProgress": {
            "completedCourses": [course["courseCode"] for course in validation_results["studentCourses"] if course.get("completed", True)],
            "missingRequirements": {
                "major": major_missing,
                "core": core_missing,
                "electives": electives_remaining
            },
            "prerequisiteIssues": [{
                "wantedCourse": issue["courseWanted"],
                "needs": issue["missingPrerequisites"]
            } for issue in validation_results["prerequisiteCheck"]["issues"]],
            "graduationProgress": validation_results["graduationProgress"]["percentageComplete"],
            "estimatedGraduation": validation_results["graduationProgress"]["estimatedGraduationDate"]
        }
    }
    
    return summary

def perform_course_validation(student_courses, course_data, track="Software Engineering"):
    """Run all validation functions and combine results"""
    # Extract completed course codes
    completed_course_codes = [course['courseCode'] for course in student_courses if course.get('completed', True)]
    
    validation_results = {
        "studentCourses": student_courses,
        "validationTimestamp": datetime.now().isoformat(),
        "prerequisiteCheck": validate_prerequisites(student_courses, course_data),
        "coreRequirements": validate_core_curriculum(student_courses, course_data.get('core_curriculum', {})),
        "majorRequirements": validate_major_requirements(student_courses, track, course_data),
        "graduationProgress": calculate_graduation_progress(student_courses, course_data.get('core_curriculum', {}), course_data, track)
    }
    
    # Add elective options for the selected track
    if track == "Software Engineering":
        validation_results["software_track_electives"] = get_track_electives(
            track, 
            course_data, 
            completed_course_codes
        )
    
    return validation_results

def get_track_electives(track, major_courses, completed_courses):
    """Get available elective options for the given track"""
    elective_options = []
    
    if track == "Software Engineering":
        # Get elective options from software engineering track
        for course in major_courses.get('software_track', {}).get('courses', {}).get('electiveSoftwareEngineering', []):
            course_code = ""
            
            if isinstance(course, dict) and 'courseCode' in course:
                course_code = course.get('courseCode')
                
                # Only include if not already completed
                if course_code not in completed_courses:
                    elective_options.append({
                        'courseCode': course_code,
                        'description': course.get('description', '')
                    })
            elif isinstance(course, str) and course not in completed_courses:
                # Handle case where course is just a string
                # Try to find its details in cosc_courses
                course_code = course
                course_details = None
                
                for c in major_courses.get('cosc_courses', {}).get('courses', []):
                    if c.get('courseCode') == course_code:
                        course_details = c
                        break
                
                if course_details:
                    elective_options.append({
                        'courseCode': course_code,
                        'description': course_details.get('description', '')
                    })
                else:
                    # If we can't find details, still include the code
                    elective_options.append({
                        'courseCode': course_code,
                        'description': ''
                    })
    
    # Add similar logic for other tracks
    
    return elective_options