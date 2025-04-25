import os 
import json
from datetime import datetime

def load_course_data(app_directory):
    try:
        course_data = {}
        cosc_major_path = os.path.join(app_directory, 'cosc_major copy.json')
        software_track_path = os.path.join(app_directory, 'software_track copy.json')
        core_curriculum_path = os.path.join(app_directory, 'core_curriculum copy.json')

        with open(cosc_major_path, 'r') as f:
            course_data['cosc_courses'] = json.load(f)

        with open(software_track_path, 'r') as f:
            course_data['software_track'] = json.load(f)
        
        with open(core_curriculum_path, 'r') as f:
            course_data['core_curriculum'] = json.load(f)
        
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
    
    # Check each core category
    for category in core_curriculum.get('core_categories', []):
        category_title = category.get('coreTitle', '')
        category_courses = category.get('courses', [])
        
        # Check if student has completed any course in this category
        completed = False
        completed_course = None
        
        for core_course in category_courses:
            core_course_code = core_course.get('courseCode', '')
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
    
    # Determine required courses based on track
    if track == "Software Engineering":
        # Get required courses for Software Engineering track
        required_courses = []
        
        # Add required computer science courses
        for course in major_courses.get('software_track', {}).get('courses', {}).get('requiredComputerScience', []):
            required_courses.append(course.get('courseCode'))
            
        # Add required software engineering courses
        for course in major_courses.get('software_track', {}).get('courses', {}).get('requiredSoftwareEngineering', []):
            required_courses.append(course.get('courseCode'))
            
        # Count electives needed
        electives_needed = 1  # Assuming 1 elective is needed for Software Engineering track
        
        # Get elective courses
        elective_courses = []
        for course in major_courses.get('software_track', {}).get('courses', {}).get('electiveSoftwareEngineering', []):
            elective_courses.append(course.get('courseCode'))
        
        # Check required courses
        for course_code in required_courses:
            if course_code in completed_course_codes:
                # Find course details
                course_title = ""
                for c in major_courses.get('cosc_courses', {}).get('courses', []):
                    if c.get('courseCode') == course_code:
                        course_title = c.get('courseTitle', '')
                        break
                
                validation_results["completedRequired"].append({
                    "courseCode": course_code,
                    "courseTitle": course_title,
                    "completed": True
                })
            else:
                validation_results["missingRequired"].append({
                    "courseCode": course_code,
                    "completed": False
                })
                validation_results["valid"] = False
        
        # Check electives
        validation_results["electivesNeeded"] = electives_needed
        for course_code in elective_courses:
            if course_code in completed_course_codes:
                validation_results["electivesCompleted"] += 1
        
        if validation_results["electivesCompleted"] < validation_results["electivesNeeded"]:
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
        
        # Find course in our database to get credit hours
        for c in major_courses.get('cosc_courses', {}).get('courses', []):
            if c.get('courseCode') == course_code:
                # Handle case where units might be a list [min, max] or a string/int
                units = c.get('units', 0)
                if isinstance(units, list):
                    units = units[0]  # Take minimum units
                try:
                    validation_results["totalCreditsEarned"] += int(units)
                except (ValueError, TypeError):
                    # If units can't be converted to int, assume 3 credits (typical)
                    validation_results["totalCreditsEarned"] += 3
                break
    
    # Calculate remaining requirements
    core_validation = validate_core_curriculum(student_courses, core_curriculum)
    major_validation = validate_major_requirements(student_courses, track, major_courses)
    
    validation_results["remainingCategories"]["coreRequirements"] = len(core_validation["missingCore"])
    validation_results["remainingCategories"]["majorRequirements"] = len(major_validation["missingRequired"])
    validation_results["remainingCategories"]["electiveRequirements"] = max(0, major_validation["electivesNeeded"] - major_validation["electivesCompleted"])
    
    # Calculate percentage complete
    if validation_results["totalCreditsRequired"] > 0:
        validation_results["percentageComplete"] = int((validation_results["totalCreditsEarned"] / validation_results["totalCreditsRequired"]) * 100)
    
    # Estimate graduation date based on progress
    # Assuming 15 credits per semester and 2 semesters per year
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    credits_remaining = validation_results["totalCreditsRequired"] - validation_results["totalCreditsEarned"]
    semesters_remaining = max(1, round(credits_remaining / 15))
    years_remaining = semesters_remaining / 2
    
    # Determine whether graduation would be in May or December
    if current_month < 8:  # Before August
        next_graduation_month = "May" if semesters_remaining % 2 == 1 else "December"
    else:  # August or later
        next_graduation_month = "December" if semesters_remaining % 2 == 1 else "May"
    
    graduation_year = current_year + int(years_remaining)
    validation_results["estimatedGraduationDate"] = f"{next_graduation_month} {graduation_year}"
    
    return validation_results

def generate_validation_summary(validation_results):
    """Create a formatted summary of validation results for the Assistant API"""
    summary = {
        "studentProgress": {
            "completedCourses": [course["courseCode"] for course in validation_results["studentCourses"] if course.get("completed", True)],
            "missingRequirements": {
                "major": [course["courseCode"] for course in validation_results["majorRequirements"]["missingRequired"]],
                "core": [category["category"] for category in validation_results["coreRequirements"]["missingCore"]]
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
    validation_results = {
        "studentCourses": student_courses,
        "validationTimestamp": datetime.now().isoformat(),
        "prerequisiteCheck": validate_prerequisites(student_courses, course_data),
        "coreRequirements": validate_core_curriculum(student_courses, course_data.get('core_curriculum', {})),
        "majorRequirements": validate_major_requirements(student_courses, track, course_data),
        "graduationProgress": calculate_graduation_progress(student_courses, course_data.get('core_curriculum', {}), course_data, track)
    }
    
    return validation_results