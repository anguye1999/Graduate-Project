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
        "completedMath": [],
        "missingMath": [],
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
        electives_needed = 2  # Assuming 2 elective is needed for Software Engineering track
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
        
        # Get math courses
        math_courses = []
        for course in major_courses.get('software_track', {}).get('courses', {}).get('requiredMath', []):
            if isinstance(course, dict) and 'courseCode' in course:
                math_courses.append(course.get('courseCode'))
            elif isinstance(course, str):
                math_courses.append(course)
        
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
        
        # Check math courses
        for course_code in math_courses:
            if course_code in completed_course_codes:
                # Debug log
                print(f"Found completed math course: {course_code}")
                
                validation_results["completedMath"].append({
                    "courseCode": course_code,
                    "completed": True
                })
            else:
                # Debug log
                print(f"Missing math course: {course_code}")
                
                validation_results["missingMath"].append({
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
        # Cap at 100% if it exceeds
        if validation_results["percentageComplete"] > 100:
            validation_results["percentageComplete"] = 100
    
    # Check for 100% completion
    total_remaining = (
        validation_results["remainingCategories"]["coreRequirements"] + 
        validation_results["remainingCategories"]["majorRequirements"] + 
        validation_results["remainingCategories"]["electiveRequirements"]
    )
    
    # Current semester/season detection
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # Determine current semester
    if current_month >= 1 and current_month <= 5:
        current_semester = "Spring"
    elif current_month >= 8 and current_month <= 12:
        current_semester = "Fall"
    else:
        current_semester = "Summer"
    
    # If all requirements complete, set graduation to current/next semester
    if total_remaining == 0 and validation_results["percentageComplete"] >= 100:
        # If we're in a semester, graduate at the end of this semester
        if current_semester == "Fall":
            graduation_month = "December"
            graduation_year = current_year
        elif current_semester == "Spring":
            graduation_month = "May"
            graduation_year = current_year
        else:  # Summer
            graduation_month = "August"
            graduation_year = current_year
            
        validation_results["estimatedGraduationDate"] = f"{graduation_month} {graduation_year}"
    else:
        # Regular graduation date calculation for incomplete degrees
        credits_remaining = validation_results["totalCreditsRequired"] - validation_results["totalCreditsEarned"]
        
        # Calculate average credits per semester from completed courses if possible
        typical_credits_per_term = 15  # Default
        semester_credits = defaultdict(int)
        
        for course in completed_courses:
            semester = course.get('semester')
            year = course.get('year')
            if semester and year:
                semester_key = f"{semester} {year}"
                # Simplified - in real implementation, reuse credit finding logic
                credits = 3
                semester_credits[semester_key] += credits
        
        if semester_credits:
            avg_credits = sum(semester_credits.values()) / len(semester_credits)
            if avg_credits > 0:
                typical_credits_per_term = avg_credits
        
        # Calculate remaining semesters
        semesters_remaining = max(1, round(credits_remaining / typical_credits_per_term))
        
        # Calculate graduation term
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
    validation_results["typicalCreditsPerTerm"] = typical_credits_per_term if 'typical_credits_per_term' in locals() else 15
    validation_results["creditsRemaining"] = validation_results["totalCreditsRequired"] - validation_results["totalCreditsEarned"]
    validation_results["semestersRemaining"] = semesters_remaining if 'semesters_remaining' in locals() else 0
    
    return validation_results

def generate_validation_summary(validation_results):
    """Create a formatted summary of validation results for the Assistant API"""
    # Get missing requirements from major requirements
    major_missing = [course["courseCode"] for course in validation_results["majorRequirements"]["missingRequired"]]
    
    # Get missing math requirements
    math_missing = [course["courseCode"] for course in validation_results["majorRequirements"]["missingMath"]]
    
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
    print(f"Generating summary: Major missing: {major_missing}, Math missing: {math_missing}, Core missing: {core_missing}, Electives: {electives_completed}/{electives_needed}")
    
    summary = {
        "studentProgress": {
            "completedCourses": [course["courseCode"] for course in validation_results["studentCourses"] if course.get("completed", True)],
            "missingRequirements": {
                "major": major_missing,
                "math": math_missing,
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
    """A more efficient validation that uses existing course data"""
    try:
        # Start with basic data structure
        validation_results = {
            "studentCourses": student_courses,
            "validationTimestamp": datetime.now().isoformat(),
            "prerequisiteCheck": {
                "valid": True,
                "issues": [],
                "validCourses": []
            },
            "coreRequirements": {
                "valid": True,
                "completedCore": [],
                "missingCore": []
            },
            "majorRequirements": {
                "valid": True,
                "track": track,
                "completedRequired": [],
                "missingRequired": [],
                "completedMath": [],
                "missingMath": [],
                "electivesNeeded": 2,
                "electivesCompleted": 0
            }
        }
        
        # Extract completed course codes
        completed_course_codes = [course['courseCode'] for course in student_courses if course.get('completed', True)]
        in_progress_codes = [course['courseCode'] for course in student_courses if not course.get('completed', True)]
        
        print(f"Validation - Completed: {len(completed_course_codes)}, In Progress: {len(in_progress_codes)}")
        
        # Create a course lookup function to find course details in any collection
        def find_course_details(course_code):
            # Look in COSC courses
            for c in course_data.get('cosc_courses', {}).get('courses', []):
                if c.get('courseCode') == course_code:
                    return c
            
            # Look in math courses
            for c in course_data.get('math_courses', {}).get('courses', []):
                if c.get('courseCode') == course_code:
                    return c
            
            # Check other collections
            collections = [
                course_data.get('software_track', {}).get('courses', {}).get('requiredComputerScience', []),
                course_data.get('software_track', {}).get('courses', {}).get('requiredSoftwareEngineering', []),
                course_data.get('software_track', {}).get('courses', {}).get('electiveSoftwareEngineering', []),
                course_data.get('software_track', {}).get('courses', {}).get('requiredMath', [])
            ]
            
            for collection in collections:
                for c in collection:
                    if isinstance(c, dict) and c.get('courseCode') == course_code:
                        return c
            
            # Return a default if not found
            return {'courseCode': course_code, 'units': 3}
        
        # Accurate credit calculation using course data
        credits_completed = 0
        for course_code in completed_course_codes:
            course_info = find_course_details(course_code)
            units = course_info.get('units', 3)
            
            # Handle units that might be a list [min, max]
            if isinstance(units, list):
                units = units[0]  # Take minimum value
            
            try:
                credits_completed += int(units)
            except (ValueError, TypeError):
                credits_completed += 3  # Default to 3 if conversion fails
        
        # Core curriculum validation
        core_categories = course_data.get('core_curriculum', {}).get('core_categories', [])
        
        for category in core_categories:
            category_title = category.get('coreTitle', '')
            category_courses = category.get('courses', [])
            
            # Check if student has completed any course in this category
            completed = False
            completed_course = None
            
            for core_course in category_courses:
                core_course_code = ""
                if isinstance(core_course, dict):
                    core_course_code = core_course.get('courseCode', '')
                elif isinstance(core_course, str):
                    core_course_code = core_course
                
                if core_course_code in completed_course_codes:
                    completed = True
                    completed_course = core_course_code
                    break
            
            if completed:
                validation_results["coreRequirements"]["completedCore"].append({
                    "category": category_title,
                    "courseCode": completed_course,
                    "completed": True
                })
            else:
                validation_results["coreRequirements"]["missingCore"].append({
                    "category": category_title,
                    "completed": False
                })
                validation_results["coreRequirements"]["valid"] = False
        
        # Major requirements validation
        if track == "Software Engineering":
            # Get required courses list
            required_courses = []
            
            # Add required CS courses
            for course in course_data.get('software_track', {}).get('courses', {}).get('requiredComputerScience', []):
                if isinstance(course, dict) and 'courseCode' in course:
                    required_courses.append(course.get('courseCode'))
                elif isinstance(course, str):
                    required_courses.append(course)
            
            # Add required SE courses
            for course in course_data.get('software_track', {}).get('courses', {}).get('requiredSoftwareEngineering', []):
                if isinstance(course, dict) and 'courseCode' in course:
                    required_courses.append(course.get('courseCode'))
                elif isinstance(course, str):
                    required_courses.append(course)
            
            # Add math courses
            math_courses = []
            for course in course_data.get('software_track', {}).get('courses', {}).get('requiredMath', []):
                if isinstance(course, dict) and 'courseCode' in course:
                    math_courses.append(course.get('courseCode'))
                elif isinstance(course, str):
                    math_courses.append(course)
            
            # Check required courses
            for course_code in required_courses:
                if course_code in completed_course_codes:
                    validation_results["majorRequirements"]["completedRequired"].append({
                        "courseCode": course_code,
                        "completed": True
                    })
                else:
                    validation_results["majorRequirements"]["missingRequired"].append({
                        "courseCode": course_code,
                        "completed": False
                    })
                    validation_results["majorRequirements"]["valid"] = False
            
            # Check math courses - with proper handling of OR conditions
            for course_code in math_courses:
                if " or " in course_code:
                    # This is an "OR" condition
                    options = course_code.split(" or ")
                    options = [option.strip() for option in options]
                    
                    or_met = False
                    completed_option = None
                    for option in options:
                        if option in completed_course_codes:
                            or_met = True
                            completed_option = option
                            break
                    
                    if or_met:
                        validation_results["majorRequirements"]["completedMath"].append({
                            "courseCode": completed_option,
                            "completed": True
                        })
                    else:
                        validation_results["majorRequirements"]["missingMath"].append({
                            "courseCode": course_code,  # Keep the original "X or Y" format
                            "completed": False
                        })
                        validation_results["majorRequirements"]["valid"] = False
                elif course_code in completed_course_codes:
                    validation_results["majorRequirements"]["completedMath"].append({
                        "courseCode": course_code,
                        "completed": True
                    })
                else:
                    validation_results["majorRequirements"]["missingMath"].append({
                        "courseCode": course_code,
                        "completed": False
                    })
                    validation_results["majorRequirements"]["valid"] = False
            
            # Electives
            elective_courses = []
            for course in course_data.get('software_track', {}).get('courses', {}).get('electiveSoftwareEngineering', []):
                if isinstance(course, dict) and 'courseCode' in course:
                    elective_courses.append(course.get('courseCode'))
                elif isinstance(course, str):
                    elective_courses.append(course)
            
            # Count electives completed
            electives_completed = 0
            for course_code in elective_courses:
                if course_code in completed_course_codes:
                    electives_completed += 1
            
            validation_results["majorRequirements"]["electivesCompleted"] = electives_completed
            
            # Add elective options for the selected track
            validation_results["software_track_electives"] = []
            for course_code in elective_courses:
                if course_code not in completed_course_codes:
                    course_info = find_course_details(course_code)
                    validation_results["software_track_electives"].append({
                        'courseCode': course_code,
                        'description': course_info.get('description', '')
                    })
        
        # Graduation progress calculation
        total_credits_required = 120
        percentage_complete = int((credits_completed / total_credits_required) * 100)
        
        # Cap at 100%
        if percentage_complete > 100:
            percentage_complete = 100
        
        # Calculate remaining requirements
        remaining_credits = max(0, total_credits_required - credits_completed)
        
        # Check if all requirements are completed
        core_missing = len(validation_results["coreRequirements"]["missingCore"])
        major_missing = len(validation_results["majorRequirements"]["missingRequired"])
        math_missing = len(validation_results["majorRequirements"]["missingMath"])
        electives_needed = validation_results["majorRequirements"]["electivesNeeded"]
        electives_completed = validation_results["majorRequirements"]["electivesCompleted"]
        electives_missing = max(0, electives_needed - electives_completed)
        
        all_requirements_met = (
            core_missing == 0 and
            major_missing == 0 and
            math_missing == 0 and
            electives_missing == 0
        )
        
        # Determine graduation date
        if remaining_credits <= 0 and all_requirements_met:
            # All requirements met and enough credits - already graduated or graduating now
            current_year = datetime.now().year
            current_month = datetime.now().month
            
            if current_month >= 1 and current_month <= 5:
                grad_date = f"May {current_year}"
            elif current_month >= 8 and current_month <= 12:
                grad_date = f"December {current_year}"
            else:  # Summer
                grad_date = f"August {current_year}"
                
            semesters_remaining = 0
        else:
            # Still have requirements or credits to complete
            current_year = datetime.now().year
            current_month = datetime.now().month
            semesters_remaining = max(1, round(remaining_credits / 15))
            
            if current_month >= 8:  # Fall
                if semesters_remaining == 1:
                    grad_date = f"May {current_year + 1}"
                else:
                    grad_date = f"December {current_year + (semesters_remaining // 2)}"
            else:  # Spring
                if semesters_remaining == 1:
                    grad_date = f"December {current_year}"
                else:
                    grad_date = f"May {current_year + ((semesters_remaining + 1) // 2)}"
        
        validation_results["graduationProgress"] = {
            "totalCreditsEarned": credits_completed,
            "totalCreditsRequired": total_credits_required,
            "percentageComplete": percentage_complete,
            "estimatedGraduationDate": grad_date,
            "creditsRemaining": remaining_credits,
            "semestersRemaining": semesters_remaining
        }
        
        print("Validation completed successfully")
        return validation_results
        
    except Exception as e:
        print(f"Error in validation: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return minimal validation results on error
        return {
            "studentCourses": student_courses,
            "validationTimestamp": datetime.now().isoformat(),
            "error": str(e),
            "prerequisiteCheck": {"valid": True, "issues": []},
            "coreRequirements": {"valid": False, "completedCore": [], "missingCore": []},
            "majorRequirements": {"valid": False, "completedRequired": [], "missingRequired": [], "completedMath": [], "missingMath": [], "electivesNeeded": 0, "electivesCompleted": 0},
            "graduationProgress": {"totalCreditsEarned": 0, "totalCreditsRequired": 120, "percentageComplete": 0, "estimatedGraduationDate": "Unknown"}
        }

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