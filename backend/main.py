from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import time
import threading
import tempfile
import csv
import re
from werkzeug.utils import secure_filename
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables and initialize app
load_dotenv()
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

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
            
            # Look for course codes
            matches = re.findall(r'([A-Z]{2,4})\s*(\d{3,4}[A-Z]?)', content)
            
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
                    name_text = content[code_pos:code_pos+100]
                    name_match = re.search(r'(?::|-)?\s*([A-Za-z\s,&]+)', name_text)
                    if name_match:
                        name = name_match.group(1).strip()
                
                courses.append({
                    'department': dept,
                    'number': number,
                    'name': name,
                    'courseCode': f"{dept} {number}",
                    'completed': True
                })
        
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
        
        # Add user message to thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
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
    """Handle course history file uploads"""
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
        
        # Add course info to thread if it exists
        if session_id in user_threads:
            thread_id = user_threads[session_id]['thread_id']
            
            # Create a summary for the assistant
            message = f"The user has uploaded their course history with {len(courses)} courses:\n\n"
            
            # Group courses by department
            courses_by_dept = {}
            for course in courses:
                dept = course.get('department', 'Unknown')
                if dept not in courses_by_dept:
                    courses_by_dept[dept] = []
                courses_by_dept[dept].append(course)
            
            # List courses by department
            for dept, dept_courses in courses_by_dept.items():
                message += f"### {dept} Courses\n"
                for course in dept_courses:
                    # Format course line
                    number = course.get('number', '')
                    name = course.get('name', '')
                    completed = "Completed" if course.get('completed') else "Not completed"
                    
                    message += f"- {dept} {number}"
                    if name:
                        message += f": {name}"
                    message += f" ({completed})\n"
                
                message += "\n"
            
            message += "Please provide course recommendations and advice for their degree progress."
            
            # Add to thread
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message
            )
        
        # Return success response
        return jsonify({
            'message': f"I've analyzed your file and found {len(courses)} courses. What would you like to know?",
            'extractedCourses': courses,
            'success': True
        })
        
    except Exception as e:
        print(f"Error processing upload: {str(e)}")
        return jsonify({
            'message': f'Error processing file: {str(e)}',
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
        return jsonify({"status": "success", "message": "Session cleared"})
    
    return jsonify({"status": "error", "message": "Session not found"}), 404

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