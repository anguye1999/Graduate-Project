from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import time
import threading
import tempfile
import csv
import re
import json
from werkzeug.utils import secure_filename
from openai import OpenAI
from dotenv import load_dotenv
import os
from validation import load_course_data, perform_course_validation, generate_validation_summary
from course_sequence import generate_recommended_sequence

# Load environment variables and initialize app
load_dotenv()
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

app_directory = os.path.dirname(os.path.abspath(__file__))
course_data = load_course_data(app_directory)
if not course_data:
    print("Warning: Could not load course data. Validation will not work properly.")

# Configuration constants
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'csv', 'txt'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB limit
SESSION_TIMEOUT = 1800  # Sessions expire after 30 minutes
CLEANUP_INTERVAL = 180  # Run cleanup every 3 minutes

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")
client = OpenAI(api_key=api_key)

# Assistant configuration
ASSISTANT_ID = "asst_E8cJRwahq7uuIRJeAeerDk89"  

# Storage for sessions and course data
user_threads = {}
user_courses = {}
# New: Add a dictionary to track file upload status
user_has_uploaded = {}

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_course_recommendations(completed_courses, recommendations):
    """Validate that recommended courses respect prerequisites"""
    valid_recommendations = []
    
    # Define prerequisite rules
    prerequisites = {
        "COSC 236": ["COSC 175"],
        "COSC 237": ["COSC 236"],
        "COSC 290": ["COSC 236", "MATH 263 OR MATH 267"],
        "COSC 336": ["COSC 237"],
        "PHYS 242": ["PHYS 241"],
        "COSC 412": ["COSC 336"],
        "COSC 350": ["COSC 336"],
        "COSC 436": ["COSC 336"],
        "COSC 439": ["COSC 336"],
        "COSC 455": ["COSC 350"],
        "COSC 457": ["COSC 412"],
        "COSC 418": ["COSC 336"],
        # Add more course prerequisites as needed
    }
    
    for course in recommendations:
        # Check if course has prerequisites
        if course in prerequisites:
            prereqs = prerequisites[course]
            all_prereqs_met = True
            
            for prereq in prereqs:
                if "OR" in prereq:
                    # Handle "OR" conditions
                    options = [opt.strip() for opt in prereq.split("OR")]
                    one_option_met = any(opt in completed_courses for opt in options)
                    if not one_option_met:
                        all_prereqs_met = False
                        break
                elif prereq not in completed_courses:
                    all_prereqs_met = False
                    break
            
            if all_prereqs_met:
                valid_recommendations.append(course)
        else:
            # No prerequisites or prerequisites unknown
            valid_recommendations.append(course)
    
    return valid_recommendations

def extract_course_mentions(text):
    """Extract course codes mentioned in text"""
    course_codes = []
    # Pattern for course codes like COSC 175, MATH 273, etc.
    matches = re.findall(r'\b([A-Z]{2,4})\s*(\d{3}[A-Z]?)\b', text)
    
    for dept, number in matches:
        course_code = f"{dept} {number}"
        if course_code not in course_codes:
            course_codes.append(course_code)
    
    return course_codes

def extract_courses_from_csv(file_path):
    """Extract course information from CSV files"""
    try:
        courses = []
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            headers = next(reader, [])
            
            # Try to identify course code columns and time information
            code_col_idx = -1
            name_col_idx = -1
            semester_col_idx = -1
            year_col_idx = -1
            term_col_idx = -1
            status_col_idx = -1  # Add column for completion status
            
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if any(keyword in header_lower for keyword in ['course', 'code', 'number']):
                    code_col_idx = i
                elif any(keyword in header_lower for keyword in ['title', 'name', 'description']):
                    name_col_idx = i
                elif any(keyword in header_lower for keyword in ['semester', 'term', 'season']):
                    if 'semester' in header_lower or 'season' in header_lower:
                        semester_col_idx = i
                    else:
                        term_col_idx = i  # Could be "Fall 2024" format
                elif any(keyword in header_lower for keyword in ['year', 'date']):
                    year_col_idx = i
                elif any(keyword in header_lower for keyword in ['status', 'complete', 'completed', 'in progress']):
                    status_col_idx = i
            
            # If no obvious columns found, use first columns
            if code_col_idx == -1 and len(headers) >= 1:
                code_col_idx = 0
            if name_col_idx == -1 and len(headers) >= 2:
                name_col_idx = 1
            
            # Process rows
            for row in reader:
                if len(row) <= max(code_col_idx, name_col_idx):
                    continue
                
                # Extract course code
                course_code = row[code_col_idx] if code_col_idx >= 0 else ""
                matches = re.findall(r'([A-Z]{2,4})\s*(\d{3,4}[A-Z]?)', course_code)
                
                if matches:
                    dept, number = matches[0]  # Take first match only
                    name = row[name_col_idx] if name_col_idx >= 0 and name_col_idx < len(row) else ""
                    
                    # Get semester and year information
                    semester = ""
                    year = ""
                    
                    # Check for term column that might have "Fall 2024" format
                    if term_col_idx >= 0 and term_col_idx < len(row):
                        term_value = row[term_col_idx]
                        term_match = re.search(r'(Spring|Fall|Summer|Winter)\s*(20\d\d)', term_value)
                        if term_match:
                            semester = term_match.group(1)
                            year = term_match.group(2)
                    
                    # If not found in term, look for separate semester and year columns
                    if not semester and semester_col_idx >= 0 and semester_col_idx < len(row):
                        semester_value = row[semester_col_idx]
                        if semester_value:
                            # Try to normalize semester values
                            semester_value = semester_value.lower()
                            if 'fall' in semester_value:
                                semester = 'Fall'
                            elif 'spring' in semester_value:
                                semester = 'Spring'
                            elif 'summer' in semester_value:
                                semester = 'Summer'
                            elif 'winter' in semester_value:
                                semester = 'Winter'
                            else:
                                semester = semester_value.capitalize()
                    
                    if not year and year_col_idx >= 0 and year_col_idx < len(row):
                        year_value = row[year_col_idx]
                        # Try to extract year from various formats
                        year_match = re.search(r'(20\d\d)', year_value)
                        if year_match:
                            year = year_match.group(1)
                    
                    # Determine completed status
                    completed = True  # Default to completed
                    if status_col_idx >= 0 and status_col_idx < len(row):
                        status_value = row[status_col_idx].lower()
                        if any(term in status_value for term in ['in progress', 'current', 'enrolled', 'pending', 'not complete', 'incomplete']):
                            completed = False
                    
                    # Create the course object with semester/year info
                    courses.append({
                        'department': dept,
                        'number': number,
                        'name': name,
                        'courseCode': f"{dept} {number}",
                        'semester': semester,
                        'year': year,
                        'completed': completed
                    })
        
        # Add debug logging
        print(f"Extracted {len(courses)} courses from CSV file:")
        for course in courses:
            semester_info = ""
            if course.get('semester') and course.get('year'):
                semester_info = f"{course['semester']} {course['year']}"
            completed_status = "Completed" if course.get('completed', True) else "In Progress"
            print(f"  - {course['courseCode']}: {course['name']} ({semester_info}) - {completed_status}")
        
        return courses
    except Exception as e:
        print(f"Error parsing CSV file: {str(e)}")
        return []

def extract_courses_from_text(file_path):
    """Extract course information from plain text files with improved section detection"""
    try:
        courses = []
        seen = set()
        
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            lines = content.split('\n')
            
            # Track the current section to determine completion status
            current_section = "unknown"
            
            for i, line in enumerate(lines):
                line_lower = line.lower().strip()
                
                # Debug output to help diagnose parsing issues
                print(f"Processing line: '{line}'")
                
                # First check specific section headers
                if "not taken classes" in line_lower:
                    current_section = "planned"
                    print(f"  Detected section: planned")
                    continue
                elif "completed classes" in line_lower:
                    current_section = "completed"
                    print(f"  Detected section: completed")
                    continue
                elif "current classes" in line_lower:
                    current_section = "current"
                    print(f"  Detected section: current")
                    continue
                
                # Process term-based course listings like "Freshman Term 1: COSC 175 - Fall 2021"
                term_match = re.search(r'(\w+)\s+Term\s+\d+:\s+', line)
                if term_match:
                    # This format is for completed courses in a term
                    term_section = "completed"
                    print(f"  Detected term format in section: {term_section}")
                    
                    # Process the rest of the line for courses
                    course_part = line[term_match.end():]
                    # Split multiple courses on commas
                    course_entries = course_part.split(',')
                    
                    for entry in course_entries:
                        entry = entry.strip()
                        print(f"  Processing course entry: '{entry}'")
                        
                        # Extract course code, semester, and year
                        course_match = re.search(r'([A-Z]{2,4}\s*\d{3}[A-Z]?)\s*-\s*(Fall|Spring|Summer|Winter)\s*(20\d\d)', entry)
                        if course_match:
                            dept_code = course_match.group(1).strip()
                            semester = course_match.group(2)
                            year = course_match.group(3)
                            
                            # Extract department and number
                            dept_num_match = re.search(r'([A-Z]{2,4})\s*(\d{3}[A-Z]?)', dept_code)
                            if dept_num_match:
                                dept = dept_num_match.group(1)
                                number = dept_num_match.group(2)
                                course_code = f"{dept} {number}"
                                key = f"{dept}{number}"
                                
                                if key not in seen:
                                    seen.add(key)
                                    is_completed = term_section == "completed"
                                    print(f"  Adding course: {course_code} - {semester} {year} (Completed: {is_completed})")
                                    
                                    courses.append({
                                        'department': dept,
                                        'number': number,
                                        'courseCode': course_code,
                                        'semester': semester,
                                        'year': year,
                                        'completed': is_completed
                                    })
                    continue
                
                # Look for standalone course codes in the current section
                course_matches = re.findall(r'\b([A-Z]{2,4})\s*(\d{3}[A-Z]?)\b', line)
                for dept, number in course_matches:
                    course_code = f"{dept} {number}"
                    key = f"{dept}{number}"
                    
                    if key in seen:
                        continue
                    
                    seen.add(key)
                    
                    # Set completion status based on section
                    is_completed = (current_section == "completed")
                    
                    # Extract semester/year information if available
                    semester = ""
                    year = ""
                    semester_match = re.search(r'\b(Spring|Fall|Summer|Winter)\s+(20\d\d)\b', line, re.IGNORECASE)
                    if semester_match:
                        semester = semester_match.group(1).capitalize()
                        year = semester_match.group(2)
                    
                    print(f"  Adding course from section {current_section}: {course_code} (Completed: {is_completed})")
                    
                    courses.append({
                        'department': dept,
                        'number': number,
                        'name': '',
                        'courseCode': course_code,
                        'semester': semester,
                        'year': year,
                        'completed': is_completed
                    })
        
        # Log the extracted courses with their status
        print(f"Extracted {len(courses)} courses from text file:")
        for course in courses:
            status = "Completed" if course['completed'] else "In Progress"
            print(f"  - {course['courseCode']} - {course.get('semester', '')} {course.get('year', '')} ({status})")
        
        return courses
    except Exception as e:
        print(f"Error parsing text file: {str(e)}")
        import traceback
        traceback.print_exc()  # Print the full stack trace for better debugging
        return []

def cleanup_expired_threads():
    """Remove expired chat threads to free up resources"""
    current_time = time.time()
    expired_threads = []
    
    for session_id, thread_info in list(user_threads.items()):
        if current_time - thread_info['last_accessed'] > SESSION_TIMEOUT:
            expired_threads.append(session_id)
    
    for session_id in expired_threads:
        if session_id in user_threads:
            del user_threads[session_id]
        if session_id in user_courses:
            del user_courses[session_id]
        # New: Also clean up upload status 
        if session_id in user_has_uploaded:
            del user_has_uploaded[session_id]
    
    if expired_threads:
        print(f"Cleaned up {len(expired_threads)} expired threads")
    
    # Schedule the next cleanup
    threading.Timer(CLEANUP_INTERVAL, cleanup_expired_threads).start()

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat interactions with the OpenAI assistant"""
    data = request.json
    user_message = data.get('message', '')
    session_id = data.get('session_id', 'default')
    
    print(f"Received chat request - Message: {user_message[:50]}... Session: {session_id}")
    
    try:
        # Get or create thread for this session
        if session_id in user_threads:
            thread_id = user_threads[session_id]['thread_id']
        else:
            # Create new thread
            thread = client.beta.threads.create()
            thread_id = thread.id
            user_threads[session_id] = {
                'thread_id': thread_id,
                'last_accessed': time.time()
            }
            
            # For new threads, add a clear context message
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content="""SYSTEM CONTEXT: This is a new conversation. 
                The user has NOT uploaded any course files yet. 
                Do not reference any uploaded files until the user actually uploads one.
                The core_curriculum.json and other JSON files are your reference data, 
                NOT files uploaded by the user."""
            )
        
        # NEW: Parse user message for course mentions
        course_mentions = extract_course_mentions(user_message)
        completed_courses = []
        
        # If user is talking about courses they've completed
        if course_mentions and (
            "completed" in user_message.lower() or 
            "taken" in user_message.lower() or
            "finished" in user_message.lower() or
            "passed" in user_message.lower()
        ):
            print(f"Detected course mentions: {course_mentions}")
            
            # Initialize user courses if needed
            if session_id not in user_courses:
                user_courses[session_id] = {'courses': [], 'student_info': {}, 'semesters': []}
            
            # Add mentioned courses to the session
            for course_code in course_mentions:
                # Check if course already exists in session
                existing = False
                for course in user_courses[session_id]['courses']:
                    if course['courseCode'] == course_code:
                        course['completed'] = True  # Mark as completed
                        existing = True
                        break
                
                if not existing:
                    # Extract department and number
                    parts = course_code.split()
                    if len(parts) == 2:
                        dept = parts[0]
                        number = parts[1]
                        
                        # Add new course
                        user_courses[session_id]['courses'].append({
                            'department': dept,
                            'number': number,
                            'courseCode': course_code,
                            'completed': True,
                            'name': ''  # No name available
                        })
            
            # Get complete list of completed courses
            completed_courses = [c['courseCode'] for c in user_courses[session_id]['courses'] 
                               if c.get('completed', True)]
        
        # Add context about file upload
        upload_context = ""
        if session_id in user_has_uploaded and user_has_uploaded[session_id]['has_uploaded']:
            # Include context about the file upload
            filename = user_has_uploaded[session_id]['filename']
            upload_context = f"CONTEXT: The user has previously uploaded a file named '{filename}'. "
        else:
            # Include context that no file has been uploaded
            upload_context = "CONTEXT: The user has NOT uploaded any course files yet. Do not reference any uploaded files or claim to know the user's courses. The core_curriculum.json and other JSON files are reference data only, NOT user uploads. "
        
        # NEW: Add prerequisite context to the message
        prerequisite_context = ""
        if completed_courses:
            prerequisite_context = f"""
            COURSE INFORMATION: The user has mentioned completing these courses: {', '.join(completed_courses)}
            
            STRICT PREREQUISITE RULES:
            1. NEVER recommend COSC 290 unless the student has already completed BOTH:
               - COSC 236
               - MATH 263 or MATH 267
               
            2. COURSE SEQUENCE MUST FOLLOW THIS EXACT ORDER:
               - Freshman Term 1: COSC 175, MATH 273, PHYS 241, TSEM 102
               - Freshman Term 2: COSC 236, PHYS 242, ENGL 102, MATH 274
               - Sophomore Term 1: COSC 237, CIS 377, COMM 131, MATH 263, ECON 201
               - Sophomore Term 2: COSC 336, COSC 290, MATH 330, COSC 109
               
            3. PREREQUISITE DEPENDENCY CHAIN:
               - COSC 175 -> COSC 236 -> COSC 237 -> COSC 336
               - MATH 273 -> MATH 274
               - PHYS 241 -> PHYS 242
               - COSC 236 + (MATH 263 or MATH 267) -> COSC 290
            
            4. When recommending courses, ALWAYS verify prerequisites have been completed.
               If prerequisites for a course are not met, DO NOT recommend that course.
            """
        
        # Add user message to thread with context
        full_message = f"{upload_context}{prerequisite_context}USER MESSAGE: {user_message}"
        
        print(f"Sending message to assistant: {full_message[:100]}...")
        
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=full_message
        )
                
        # Run the Assistant
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )
        
        # Wait for completion with timeout
        max_wait_time = 30
        start_time = time.time()
        
        while True:
            if time.time() - start_time > max_wait_time:
                return jsonify({
                    'message': "Response is taking longer than expected. Please try again.",
                    'type': 'error',
                    'session_id': session_id
                }), 408
            
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            if run_status.status == 'completed':
                break
            elif run_status.status in ['failed', 'cancelled', 'expired']:
                return jsonify({
                    'message': f"Error: Assistant run {run_status.status}",
                    'type': 'error',
                    'session_id': session_id
                }), 500
            
            # Sleep before polling again
            time.sleep(1)
        
        # Get latest assistant message
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        assistant_messages = [msg for msg in messages.data if msg.role == "assistant"]
        
        if not assistant_messages:
            return jsonify({
                'message': "No response from assistant",
                'type': 'error',
                'session_id': session_id
            }), 500
        
        # Extract text from the latest message
        latest_message = assistant_messages[0]
        response_text = "".join(
            content_part.text.value 
            for content_part in latest_message.content 
            if content_part.type == 'text'
        )
        
        # Update last accessed time
        user_threads[session_id]['last_accessed'] = time.time()
        
        return jsonify({
            'message': response_text,
            'type': 'bot',
            'session_id': session_id
        })
    
    except Exception as e:
        print(f"Error in chat: {str(e)}")
        return jsonify({
            'message': f"Error: {str(e)}",
            'type': 'error',
            'session_id': session_id
        }), 500
        
@app.route('/api/upload-courses', methods=['POST'])
def upload_courses():
    """Handle course history file uploads and validate courses"""
    # Check for file in request
    if 'file' not in request.files:
        return jsonify({'message': 'No file provided', 'success': False}), 400
    
    file = request.files['file']
    session_id = request.form.get('session_id', 'default')
    
    # Validate file
    if file.filename == '':
        return jsonify({'message': 'No file selected', 'success': False}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'message': 'File type not supported', 'success': False}), 400
    
    try:
        # Save file temporarily
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # IMPORTANT: Reset previous course data for this session
        print(f"Uploading new file: clearing previous course data for session {session_id}")
        if session_id in user_courses:
            user_courses[session_id] = {'courses': [], 'student_info': {}, 'semesters': []}
        
        # Extract courses based on file type
        file_ext = filename.rsplit('.', 1)[1].lower()
        
        if file_ext == 'csv':
            courses = extract_courses_from_csv(file_path)
        elif file_ext == 'txt':
            courses = extract_courses_from_text(file_path)
        else:
            courses = []
        
        # Read the raw file content for reference
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()
            
        # Clean up temporary file
        try:
            os.remove(file_path)
        except:
            pass
        
        # Ensure courses were found
        if not courses:
            return jsonify({
                'message': 'No course information found in the file. Please check the format.',
                'success': False
            }), 400
        
        # Store extracted data
        extracted_data = {
            'courses': courses, 
            'student_info': {},
            'semesters': []
        }
        
        user_courses[session_id] = extracted_data
        
        # Set the upload flag
        user_has_uploaded[session_id] = {
            'has_uploaded': True,
            'filename': filename,
            'timestamp': time.time(),
            'course_count': len(courses)
        }
        
        # Format courses with semester/year for display
        formatted_courses = []
        for course in courses:
            course_code = course.get('courseCode', '')
            semester = course.get('semester', '')
            year = course.get('year', '')
            completed = course.get('completed', True)
            status = "Completed" if completed else "In Progress"
            
            if semester and year:
                formatted_courses.append(f"{course_code} - {semester} {year} ({status})")
            else:
                formatted_courses.append(f"{course_code} ({status})")
        
        # Add course info to thread if it exists
        if session_id in user_threads:
            thread_id = user_threads[session_id]['thread_id']
            
            # IMPORTANT: Reset the conversation thread when uploading a new file
            # Create a new thread and store its ID
            new_thread = client.beta.threads.create()
            user_threads[session_id] = {
                'thread_id': new_thread.id,
                'last_accessed': time.time()
            }
            thread_id = new_thread.id
            
            # Create a direct message about the upload that prioritizes the user's content
            upload_message = f"""
            SYSTEM NOTIFICATION: The user has just uploaded a file named "{filename}" containing course information.

            IMPORTANT INSTRUCTIONS: 
            1. This is a user-uploaded file, NOT a reference file
            2. In all your responses, ALWAYS prioritize discussing these specific courses rather than general program information
            3. When discussing these courses, reference them by their exact codes as found in the file
            4. When listing courses, use the format "COSC 175 - Fall 2024 (Completed)" when semester information is available
            5. DO NOT include course descriptions when initially listing the courses after file upload
            6. Organize courses by department and semester

            STRICT PREREQUISITE RULES:
            1. NEVER recommend COSC 290 unless the student has already completed BOTH:
               - COSC 236
               - MATH 263 or MATH 267
               
            2. COURSE SEQUENCE MUST FOLLOW THIS EXACT ORDER:
               - Freshman Term 1: COSC 175, MATH 273, PHYS 241, TSEM 102
               - Freshman Term 2: COSC 236, PHYS 242, ENGL 102, MATH 274
               - Sophomore Term 1: COSC 237, CIS 377, COMM 131, MATH 263, ECON 201
               - Sophomore Term 2: COSC 336, COSC 290, MATH 330, COSC 109
               
            3. PREREQUISITE DEPENDENCY CHAIN:
               - COSC 175 -> COSC 236 -> COSC 237 -> COSC 336
               - MATH 273 -> MATH 274
               - PHYS 241 -> PHYS 242
               - COSC 236 + (MATH 263 or MATH 267) -> COSC 290
            
            4. When recommending courses, ALWAYS verify prerequisites have been completed.
               If prerequisites for a course are not met, DO NOT recommend that course.

            The raw content of their uploaded file is:
            ---BEGIN USER UPLOADED FILE CONTENT---
            {raw_content}
            ---END USER UPLOADED FILE CONTENT---

            The {len(courses)} courses identified in this file are:
            """

            # Add specific details about each course with improved formatting
            for formatted_course in formatted_courses:
                upload_message += f"- {formatted_course}\n"
                
            # If we have course data available, include validation but with clear prioritization instructions
            if course_data:
                # Add validation data
                track = "Software Engineering"  # Default track
                validation_results = perform_course_validation(courses, course_data, track)
                validation_summary = generate_validation_summary(validation_results)
                
                # For debugging - Print validation details to server console
                print("\n=== VALIDATION RESULTS ===")
                print(f"Total courses: {len(courses)}")
                print(f"Completed courses: {len([c for c in courses if c.get('completed', True)])}")
                print(f"In progress courses: {len([c for c in courses if not c.get('completed', True)])}")
                print(f"Major requirements - Required: {len(validation_results['majorRequirements']['completedRequired'])} completed, {len(validation_results['majorRequirements']['missingRequired'])} missing")
                print(f"Electives - Needed: {validation_results['majorRequirements']['electivesNeeded']}, Completed: {validation_results['majorRequirements']['electivesCompleted']}")
                print(f"Core requirements - Completed: {len(validation_results['coreRequirements']['completedCore'])}, Missing: {len(validation_results['coreRequirements']['missingCore'])}")
                
                upload_message += f"""
                
                SUPPLEMENTARY INFORMATION: Below is additional validation data about how these courses relate to 
                degree requirements. This is supplementary information only.
                
                STUDENT_PROGRESS: {json.dumps(validation_summary, indent=2)}
                
                IMPORTANT RESPONSE INSTRUCTIONS: 
                1. In your next response, first acknowledge the specific courses uploaded by the user
                2. List the courses by department and semester using the format "COSC 175 - Fall 2024 (Completed)" 
                3. Do NOT include course descriptions in your initial response listing
                4. Group the courses by completion status first (Completed vs. In Progress)
                5. Then group the courses by semester (Fall 2024, Spring 2025, etc.)
                6. Only include descriptions if the user specifically asks about what a course covers
                7. Ask what the user would like to know about these courses
                
                DO NOT make claims about what program the user is in unless they specifically tell you.
                DO NOT reference any courses that were not in this upload.
                """
            else:
                upload_message += """
                
                IMPORTANT RESPONSE INSTRUCTIONS:
                1. In your next response, first acknowledge the specific courses uploaded by the user
                2. List the courses by department and semester using the format "COSC 175 - Fall 2024 (Completed)"
                3. Do NOT include course descriptions in your initial response listing
                4. Group the courses by completion status first (Completed vs. In Progress)
                5. Then group the courses by semester (Fall 2024, Spring 2025, etc.)
                6. Only include descriptions if the user specifically asks about what a course covers
                7. Ask what the user would like to know about these courses
                
                DO NOT make assumptions about the user's degree program.
                DO NOT reference any courses that were not in this upload.
                """
            
            # Add a system message with explicit prerequisite verification instructions
            upload_message += """
            
            CRITICAL INSTRUCTION UPDATE:
            
            When recommending courses, you MUST verify prerequisites are satisfied.
            
            Specifically, DO NOT recommend:
            1. COSC 290 unless the student has completed BOTH:
               - COSC 236
               - Either MATH 263 or MATH 267
               
            2. COSC 336 unless the student has completed COSC 237
            
            3. COSC 237 unless the student has completed COSC 236
            
            4. COSC 236 unless the student has completed COSC 175
            
            Check both 'completed' and 'in progress' courses when verifying prerequisites.
            If a prerequisite course is in progress, you can recommend courses that require it for the NEXT semester only.
            """
            
            # Add to thread
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=upload_message
            )
        
        # Return success response with formatted courses
        return jsonify({
            'message': f"I've analyzed your file and found {len(courses)} courses. What would you like to know?",
            'extractedCourses': courses,
            'formattedCourses': formatted_courses,
            'success': True
        })
        
    except Exception as e:
        print(f"Error processing upload: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'message': f'Error processing file: {str(e)}',
            'success': False
        }), 500

@app.route('/api/validate-courses', methods=['POST'])
def validate_courses():
    data = request.json
    session_id = data.get('session_id', 'default')

    try:
        if session_id in user_courses:
            student_courses = user_courses[session_id].get('courses', [])

            if not student_courses:
                return jsonify({
                    'message': 'No courses found for validation',
                    'success': False
                }), 400

            if course_data:
                track = data.get('track', 'Software Engineering')
                
                # Debug log the courses before validation
                print(f"Validating {len(student_courses)} courses for session {session_id}")
                completed_count = len([c for c in student_courses if c.get('completed', True)])
                in_progress_count = len([c for c in student_courses if not c.get('completed', True)])
                print(f"Completed courses: {completed_count}")
                print(f"In progress courses: {in_progress_count}")
                
                # IMPORTANT: Use the simplified validation function that's much faster
                # This avoids the timeout issues
                start_time = time.time()
                try:
                    validation_result = perform_course_validation(student_courses, course_data, track)
                    print(f"Validation completed in {time.time() - start_time:.2f} seconds")
                except Exception as e:
                    print(f"Error in validation: {str(e)}")
                    return jsonify({
                        'message': f'Error during validation: {str(e)}',
                        'success': False
                    }), 500
                
                # Generate summary from validation results
                validation_summary = generate_validation_summary(validation_result)
                
                # Skip sequence generation for now - can be added back later if needed
                sequence_result = None
                
                # Return the results
                return jsonify({
                    'validation': validation_result,
                    'summary': validation_summary,
                    'sequence': sequence_result,
                    'success': True
                })
            else:
                return jsonify({
                    'message': 'No course data available for validation',
                    'success': False
                }), 400
        else:
            return jsonify({
                'message': 'No courses found for this session',
                'success': False
            }), 404
    
    except Exception as e:
        print(f"Error validating courses: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'message': f'Error validating courses: {str(e)}',
            'success': False
        }), 500

@app.route('/api/course-sequence', methods=['POST'])
def get_course_sequence():
    data = request.json
    session_id = data.get('session_id', 'default')

    try:
        if session_id in user_courses:
            student_courses = user_courses[session_id].get('courses', [])
            completed_course_codes = [c['courseCode'] for c in student_courses if c.get('completed', True)]

            if course_data and student_courses:
                track = data.get('track', 'Software Engineering')
                sequence_results = generate_recommended_sequence(student_courses, course_data, track)
                
                # Validate the recommended sequences
                for semester in sequence_results.get('semesterPlan', []):
                    semester['courses'] = validate_course_recommendations(
                        completed_course_codes, 
                        semester.get('courses', [])
                    )
                
                # Update the detailed plan to match
                detailed_plan = []
                for old_sem in sequence_results.get('detailedPlan', []):
                    # Create new semester with valid courses only
                    valid_course_codes = set()
                    for semester in sequence_results.get('semesterPlan', []):
                        if semester.get('semester') == old_sem.get('semester'):
                            valid_course_codes = set(semester.get('courses', []))
                            break
                    
                    # Filter courses in detailed plan
                    new_sem = old_sem.copy()
                    new_sem['courses'] = [c for c in old_sem.get('courses', []) 
                                          if c.get('code') in valid_course_codes]
                    detailed_plan.append(new_sem)
                
                sequence_results['detailedPlan'] = detailed_plan
                
                return jsonify({
                    'sequence': sequence_results,
                    'success': True
                })
            else:
                return jsonify({
                    'message': 'No course data available for sequencing',
                    'success': False
                }), 400
        else:
            return jsonify({
                'message': 'No courses found for this session',
                'success': False
            }), 404
    
    except Exception as e:
        print(f"Error generating course sequence: {str(e)}")
        return jsonify({
            'message': f'Error generating course sequence: {str(e)}',
            'success': False
        }), 500

@app.route('/api/clear-session', methods=['POST'])
def clear_session():
    """Clear a user session"""
    session_id = request.json.get('session_id', '')
    
    if session_id and session_id in user_threads:
        del user_threads[session_id]
        if session_id in user_courses:
            del user_courses[session_id]
        # New: Also clear upload status
        if session_id in user_has_uploaded:
            del user_has_uploaded[session_id]
        return jsonify({"status": "success", "message": "Session cleared"})
    
    return jsonify({"status": "error", "message": "Session not found"}), 404

@app.route('/api/has-uploaded', methods=['GET'])
def check_upload_status():
    """Check if a user has uploaded a file"""
    session_id = request.args.get('session_id', '')
    
    if not session_id:
        return jsonify({"status": "error", "message": "No session ID provided"}), 400
        
    has_uploaded = False
    filename = None
    course_count = 0
    
    if session_id in user_has_uploaded:
        has_uploaded = user_has_uploaded[session_id]['has_uploaded']
        filename = user_has_uploaded[session_id]['filename']
        course_count = user_has_uploaded[session_id].get('course_count', 0)
    
    return jsonify({
        "status": "success", 
        "has_uploaded": has_uploaded,
        "filename": filename,
        "course_count": course_count
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "ok"})

# Start the cleanup thread when the server starts
cleanup_thread = threading.Timer(CLEANUP_INTERVAL, cleanup_expired_threads)
cleanup_thread.daemon = True
cleanup_thread.start()

if __name__ == '__main__':
    print("Starting server...")
    app.run(debug=True)