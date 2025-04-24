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
SESSION_TIMEOUT = 3600  # Sessions expire after 1 hour
CLEANUP_INTERVAL = 300  # Run cleanup every 5 minutes

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

def extract_courses_from_csv(file_path):
    """Extract course information from CSV files"""
    try:
        courses = []
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            headers = next(reader, [])
            
            # Try to identify course code columns
            code_col_idx = -1
            name_col_idx = -1
            
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if any(keyword in header_lower for keyword in ['course', 'code', 'number']):
                    code_col_idx = i
                elif any(keyword in header_lower for keyword in ['title', 'name', 'description']):
                    name_col_idx = i
            
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
                    name = row[name_col_idx] if name_col_idx >= 0 else ""
                    courses.append({
                        'department': dept,
                        'number': number,
                        'name': name,
                        'courseCode': f"{dept} {number}",
                        'completed': True
                    })
        
        return courses
    except Exception as e:
        print(f"Error parsing CSV file: {str(e)}")
        return []

def extract_courses_from_text(file_path):
    """Extract course information from plain text files"""
    try:
        courses = []
        seen = set()
        
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
            # Print debug info
            print(f"Parsing text file with content:\n{content[:500]}")
            
            # Look for course codes with a more specific pattern
            # This pattern is more strict about what constitutes a course code
            matches = re.findall(r'\b([A-Z]{2,4})\s*(\d{3,4}[A-Z]?)\b', content)
            
            for dept, number in matches:
                key = f"{dept}{number}"
                if key in seen:
                    continue
                    
                seen.add(key)
                
                # Try to find course name near the code
                code_pos = content.find(f"{dept} {number}")
                if code_pos == -1:
                    code_pos = content.find(f"{dept}{number}")
                
                name = ""
                if code_pos >= 0:
                    # Only look for course name AFTER the code, not before
                    name_text = content[code_pos:code_pos+100]
                    
                    # More specific pattern for course names
                    # Looking for text that follows a colon, dash, or space after the course code
                    name_match = re.search(r'(?::|-)?\s+([A-Za-z0-9\s,&\'"\-]+?)(?:\.|$|\n)', name_text)
                    if name_match:
                        name = name_match.group(1).strip()
                
                courses.append({
                    'department': dept,
                    'number': number,
                    'name': name,
                    'courseCode': f"{dept} {number}",
                    'completed': True
                })
        
        # Print for debugging
        print(f"Extracted {len(courses)} courses from text file:")
        for course in courses:
            print(f"  - {course['courseCode']}: {course['name']}")
        
        return courses
    except Exception as e:
        print(f"Error parsing text file: {str(e)}")
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
            
            # New: For new threads, add a clear context message
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content="""SYSTEM CONTEXT: This is a new conversation. 
                The user has NOT uploaded any course files yet. 
                Do not reference any uploaded files until the user actually uploads one.
                The core_curriculum.json and other JSON files are your reference data, 
                NOT files uploaded by the user."""
            )
        
        # New: Check if this is the first message after a file upload
        upload_context = ""
        if session_id in user_has_uploaded and user_has_uploaded[session_id]['has_uploaded']:
            # Include context about the file upload
            filename = user_has_uploaded[session_id]['filename']
            upload_context = f"CONTEXT: The user has previously uploaded a file named '{filename}'. "
        else:
            # Include context that no file has been uploaded
            upload_context = "CONTEXT: The user has NOT uploaded any course files yet. Do not reference any uploaded files or claim to know the user's courses. The core_curriculum.json and other JSON files are reference data only, NOT user uploads. "
        
        # Add user message to thread with context
        full_message = f"{upload_context}USER MESSAGE: {user_message}"
        
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
        
        # New: Set the upload flag
        user_has_uploaded[session_id] = {
            'has_uploaded': True,
            'filename': filename,
            'timestamp': time.time(),
            'course_count': len(courses)
        }
        
        # Add course info to thread if it exists
        if session_id in user_threads:
            thread_id = user_threads[session_id]['thread_id']
            
            # Create a direct message about the upload that prioritizes the user's content
            upload_message = f"""
            SYSTEM NOTIFICATION: The user has just uploaded a file named "{filename}" containing course information.
            
            IMPORTANT INSTRUCTIONS: 
            1. This is a user-uploaded file, NOT a reference file
            2. In all your responses, ALWAYS prioritize discussing these specific courses rather than general program information
            3. When discussing these courses, reference them by their exact codes as found in the file
            
            The raw content of their uploaded file is:
            ---BEGIN USER UPLOADED FILE CONTENT---
            {raw_content}
            ---END USER UPLOADED FILE CONTENT---
            
            The {len(courses)} courses identified in this file are:
            """
            
            # Add specific details about each course
            for course in courses:
                dept = course.get('department', 'Unknown')
                number = course.get('number', 'Unknown')
                name = course.get('name', '') 
                upload_message += f"- {dept} {number}" + (f": {name}" if name else "") + "\n"
                
            # If we have course data available, include validation but with clear prioritization instructions
            if course_data:
                # Add validation data
                track = "Software Engineering"  # Default track
                validation_results = perform_course_validation(courses, course_data, track)
                validation_summary = generate_validation_summary(validation_results)
                
                upload_message += f"""
                
                SUPPLEMENTARY INFORMATION: Below is additional validation data about how these courses relate to 
                degree requirements. This is supplementary information only.
                
                STUDENT_PROGRESS: {json.dumps(validation_summary, indent=2)}
                
                IMPORTANT RESPONSE INSTRUCTIONS: 
                1. In your next response, first acknowledge the specific courses uploaded by the user (e.g., "I see you've uploaded COSC 109, COSC 175, and COMM 131")
                2. Then briefly describe what these specific courses are (by name/title)
                3. Only after that, ask what the user would like to know about these courses
                
                DO NOT make claims about what program the user is in unless they specifically tell you.
                DO NOT reference any courses that were not in this upload.
                """
            else:
                upload_message += """
                
                IMPORTANT RESPONSE INSTRUCTIONS:
                1. In your next response, first acknowledge the specific courses uploaded by the user
                2. Then briefly describe what these specific courses are (by name/title if available)
                3. Only after that, ask what the user would like to know about these courses
                
                DO NOT make assumptions about the user's degree program.
                DO NOT reference any courses that were not in this upload.
                """
            
            # Add to thread
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=upload_message
            )
        
        # Return success response
        return jsonify({
            'message': f"I've analyzed your file and found {len(courses)} courses. What would you like to know?",
            'extractedCourses': courses,
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

            if course_data and student_courses:
                track = data.get('track', 'Software Engineering')
                validation_results = perform_course_validation(student_courses, course_data, track)
                validation_summary = generate_validation_summary(validation_results)
                
                # Generate course sequence
                sequence_results = generate_recommended_sequence(student_courses, course_data, track)
                
                # Add the sequence to the response
                return jsonify({
                    'validation': validation_results,
                    'summary': validation_summary,
                    'sequence': sequence_results,
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

            if course_data and student_courses:
                track = data.get('track', 'Software Engineering')
                sequence_results = generate_recommended_sequence(student_courses, course_data, track)
                
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