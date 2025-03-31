from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import time
import json
import threading
import tempfile
import pandas as pd
import csv
import re
import openpyxl
from werkzeug.utils import secure_filename
from openai import OpenAI
from dotenv import load_dotenv

# Load the environment variable
load_dotenv()

# Initialize Flask server
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure file upload settings
UPLOAD_FOLDER = tempfile.gettempdir()  # Use system temp directory
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv', 'txt'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB limit

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Initialize OpenAI client with proper error handling
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("Warning: OpenAI API key not found in environment variables.")
    api_key = "your-api-key-here"  # Replace with your actual key if needed

client = OpenAI(api_key=api_key)

# Track user threads and assistant ID
user_threads = {}

# Store uploaded course data by session
user_courses = {}

# This should be set to your actual Assistant ID from the OpenAI platform
ASSISTANT_ID = "asst_E8cJRwahq7uuIRJeAeerDk89"  # Replace with your Assistant ID

# Session cleanup settings
SESSION_TIMEOUT = 3600  # Sessions expire after 1 hour of inactivity
CLEANUP_INTERVAL = 300   # Run cleanup every 5 minutes

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_towson_degree_plan(file_path):
    """Extract course information from Towson University CS degree plan format"""
    try:
        # Load with pandas
        # Note: We'll use header=None since the headers are in a specific row
        df = pd.read_excel(file_path, header=None)
        
        # Extract student information first
        student_info = {}
        # Check rows 3-6 for student data (rows 0-indexed)
        for i in range(3, 7):
            if i < len(df):
                row = df.iloc[i]
                # Convert row to string for easier searching
                row_as_str = [str(cell) if pd.notna(cell) else '' for cell in row]
                row_text = ' '.join(row_as_str)
                
                # Extract student name (row 3, column 4)
                if i == 3 and len(row) > 4 and pd.notna(row[4]):
                    student_info['name'] = str(row[4]).strip()
                    
                # Extract student ID (row 3, column 12)
                if i == 3 and len(row) > 12 and pd.notna(row[12]):
                    student_info['student_id'] = str(row[12]).strip()
                    
                # Extract major (row 4, column 4)
                if i == 4 and len(row) > 4 and pd.notna(row[4]):
                    student_info['major'] = str(row[4]).strip()
                    
                # Extract catalog year (row 4, column 12)
                if i == 4 and len(row) > 12 and pd.notna(row[12]):
                    student_info['catalog_year'] = str(row[12]).strip()
                    
                # Extract track/concentration (row 5, column 4)
                if i == 5 and len(row) > 4 and pd.notna(row[4]):
                    student_info['track'] = str(row[4]).strip()
                
                # Extract advisor (row 6, column 4)
                if i == 6 and len(row) > 4 and pd.notna(row[4]):
                    student_info['advisor'] = str(row[4]).strip()
        
        # Extract unit summary (rows 8-9)
        unit_summary = {
            'earned': 0,
            'enrolled': 0,
            'planned': 0,
            'total': 0
        }
        
        if len(df) > 8 and len(df.iloc[8]) > 5 and pd.notna(df.iloc[8][5]):
            try:
                unit_summary['earned'] = float(df.iloc[8][5])
            except (ValueError, TypeError):
                pass
                
        if len(df) > 9 and len(df.iloc[9]) > 5 and pd.notna(df.iloc[9][5]):
            try:
                unit_summary['enrolled'] = float(df.iloc[9][5])
            except (ValueError, TypeError):
                pass
                
        if len(df) > 8 and len(df.iloc[8]) > 9 and pd.notna(df.iloc[8][9]):
            try:
                unit_summary['planned'] = float(df.iloc[8][9])
            except (ValueError, TypeError):
                pass
                
        if len(df) > 9 and len(df.iloc[9]) > 9 and pd.notna(df.iloc[9][9]):
            try:
                unit_summary['total'] = float(df.iloc[9][9])
            except (ValueError, TypeError):
                pass
        
        # Now find all semester sections
        semesters = []
        semester_rows = []
        
        # Search for semester headers (typically in column 1)
        for idx, row in df.iterrows():
            if len(row) > 1 and pd.notna(row[1]):
                cell_value = str(row[1]).strip()
                # Match semester patterns like "Spring 2025"
                if re.search(r'(Spring|Fall|Summer|Winter)\s+20\d{2}', cell_value):
                    semester_rows.append((idx, cell_value))
        
        # Process each semester
        all_courses = []
        for i, (semester_row, semester_name) in enumerate(semester_rows):
            # Determine the end of this semester section
            end_row = df.shape[0]  # Default to end of sheet
            if i < len(semester_rows) - 1:
                end_row = semester_rows[i+1][0]
            
            # Look for course header row (should be 1 row after semester header)
            header_row = semester_row + 1
            if header_row < df.shape[0] and len(df.iloc[header_row]) > 1:
                # Check all columns for course entries
                course_columns = []
                
                # The structure is typically:
                # Column 1: Course code
                # Column 2: Units
                # Column 3: Prerequisites
                # Then repeats at columns 5, 9, and 13
                potential_course_columns = [1, 5, 9, 13]  # B, F, J, N columns (0-indexed)
                
                courses_in_semester = []
                
                # Start processing from 2 rows after semester header (skip the column headers)
                current_row = semester_row + 2
                
                while current_row < end_row:
                    row = df.iloc[current_row]
                    
                    # Check each potential course column
                    for col_idx in potential_course_columns:
                        if col_idx >= len(row):
                            continue
                            
                        if pd.notna(row[col_idx]):
                            course_code = str(row[col_idx]).strip()
                            
                            # Skip "Total" rows
                            if course_code.startswith("Total"):
                                break
                                
                            # Use regex to extract department and number
                            match = re.search(r'([A-Z]{2,4})\s*(\d{3,4}[A-Z]?)', course_code)
                            if match:
                                dept, number = match.groups()
                                
                                # Get credits if available (1 column to the right)
                                credits = None
                                if col_idx + 1 < len(row) and pd.notna(row[col_idx + 1]):
                                    try:
                                        credits = float(row[col_idx + 1])
                                    except (ValueError, TypeError):
                                        pass
                                
                                # Get prerequisites if available (2 columns to the right)
                                prereq = None
                                if col_idx + 2 < len(row) and pd.notna(row[col_idx + 2]):
                                    prereq = str(row[col_idx + 2]).strip()
                                
                                # Add to courses list
                                course = {
                                    'department': dept,
                                    'number': number,
                                    'courseCode': f"{dept} {number}",
                                    'name': '',  # Name not provided in this format
                                    'credits': credits,
                                    'prerequisites': prereq if prereq else 'None',
                                    'semester': semester_name,
                                    'completed': False  # Default to not completed
                                }
                                
                                courses_in_semester.append(course)
                                all_courses.append(course)
                    
                    current_row += 1
                
                # Add this semester to our list
                total_credits = sum(c.get('credits', 0) or 0 for c in courses_in_semester)
                semesters.append({
                    'name': semester_name,
                    'courses': courses_in_semester,
                    'totalCredits': total_credits
                })
        
        # Return the extracted data
        return {
            'courses': all_courses,
            'semesters': semesters,
            'student_info': student_info,
            'unit_summary': unit_summary
        }
        
    except Exception as e:
        print(f"Error parsing Towson degree plan: {str(e)}")
        # Return an empty result rather than raising an exception
        return {
            'courses': [],
            'semesters': [],
            'student_info': {},
            'unit_summary': {}
        }

def extract_courses_fallback(df):
    """Fallback method if the standard header detection fails"""
    courses = []
    
    # Look for cells that match course patterns in any cell
    for idx, row in df.iterrows():
        for col_idx, cell in enumerate(row):
            if pd.isna(cell):
                continue
                
            cell_value = str(cell).strip()
            match = re.search(r'([A-Z]{2,4})\s*(\d{3,4}[A-Z]?)', cell_value)
            
            if match:
                dept, number = match.groups()
                
                # Try to find credits in the next column
                credits = None
                if col_idx + 1 < len(row) and pd.notna(row[col_idx + 1]):
                    try:
                        credits = float(row[col_idx + 1])
                    except (ValueError, TypeError):
                        pass
                
                # Add to courses
                courses.append({
                    'department': dept,
                    'number': number,
                    'name': '',
                    'credits': credits,
                    'completed': False
                })
    
    print(f"Fallback extraction found {len(courses)} courses")
    
    return {
        'courses': courses,
        'student_info': {}
    }

def extract_courses_from_excel(file_path):
    """Extract course information from generic Excel files (.xlsx, .xls)"""
    try:
        # Try to read with pandas
        df = pd.read_excel(file_path)
        
        # Look for columns that might contain course information
        possible_course_cols = []
        for col in df.columns:
            col_str = str(col).lower()
            if any(keyword in col_str for keyword in ['course', 'class', 'subject', 'code']):
                possible_course_cols.append(col)
        
        # If no obvious course columns, use the first few columns
        if not possible_course_cols and len(df.columns) >= 2:
            possible_course_cols = df.columns[:2]
        
        # Extract courses based on pattern matching
        courses = []
        for _, row in df.iterrows():
            # Try to find course codes in the row
            for col in possible_course_cols:
                cell_value = str(row[col])
                # Look for patterns like "COSC 101", "CS 350", etc.
                matches = re.findall(r'([A-Z]{2,4})\s*(\d{3,4}[A-Z]?)', cell_value)
                for dept, number in matches:
                    course_name = ""
                    # Try to find a course name in adjacent columns
                    for name_col in df.columns:
                        if name_col != col:
                            name_val = str(row[name_col])
                            if len(name_val) > 3 and not re.match(r'^\d+$', name_val):
                                course_name = name_val
                                break
                    
                    courses.append({
                        'department': dept,
                        'number': number,
                        'name': course_name,
                        'completed': True  # Assume listed courses are completed
                    })
                    break
        
        # Remove duplicates
        unique_courses = []
        seen = set()
        for course in courses:
            key = f"{course['department']}{course['number']}"
            if key not in seen:
                seen.add(key)
                unique_courses.append(course)
        
        return unique_courses
    except Exception as e:
        print(f"Error parsing Excel file: {str(e)}")
        return []

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
                    for dept, number in matches:
                        name = row[name_col_idx] if name_col_idx >= 0 else ""
                        courses.append({
                            'department': dept,
                            'number': number,
                            'name': name,
                            'completed': True
                        })
                        break
        
        return courses
    except Exception as e:
        print(f"Error parsing CSV file: {str(e)}")
        return []

def extract_courses_from_text(file_path):
    """Extract course information from plain text files"""
    try:
        courses = []
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
            # Look for course codes like "COSC 101", "CS 350", etc.
            matches = re.findall(r'([A-Z]{2,4})\s*(\d{3,4}[A-Z]?)', content)
            
            for dept, number in matches:
                # Try to find course name near the code (within 100 chars)
                code_pos = content.find(f"{dept} {number}")
                if code_pos == -1:
                    code_pos = content.find(f"{dept}{number}")
                
                name = ""
                if code_pos >= 0:
                    # Look for a name after the course code
                    name_text = content[code_pos:code_pos+100]
                    name_match = re.search(r'(?::|-)?\s*([A-Za-z\s,&]+)', name_text)
                    if name_match:
                        name = name_match.group(1).strip()
                
                courses.append({
                    'department': dept,
                    'number': number,
                    'name': name,
                    'completed': True
                })
        
        # Remove duplicates
        unique_courses = []
        seen = set()
        for course in courses:
            key = f"{course['department']}{course['number']}"
            if key not in seen:
                seen.add(key)
                unique_courses.append(course)
        
        return unique_courses
    except Exception as e:
        print(f"Error parsing text file: {str(e)}")
        return []

# Add these after your existing extraction functions
def extract_any_course_like_patterns(file_path):
    """
    Last-resort extractor that tries to find anything that looks like a course code in an Excel file.
    This is more permissive than other extractors and will catch more potential course codes.
    """
    try:
        # Load the file - try different sheet indices if necessary
        sheets_to_try = [0, 1, 'Sheet1', 'Courses', 'Data']
        df = None
        
        for sheet in sheets_to_try:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet, header=None)
                print(f"Successfully loaded sheet: {sheet}")
                break
            except Exception as e:
                print(f"Failed to load sheet {sheet}: {str(e)}")
                continue
        
        if df is None:
            # If we couldn't load any specific sheet, try without specifying
            df = pd.read_excel(file_path, header=None)
        
        # Course pattern - be very permissive
        course_pattern = r'([A-Z]{2,4})\s*(\d{3,4}[A-Z]?)'
        
        # Scan all cells for course patterns
        courses = []
        seen_codes = set()
        
        for i in range(df.shape[0]):
            for j in range(df.shape[1]):
                cell_value = df.iloc[i, j]
                
                # Skip non-string cells
                if not isinstance(cell_value, str):
                    if pd.notna(cell_value):
                        cell_value = str(cell_value)
                    else:
                        continue
                
                # Look for course codes
                matches = re.findall(course_pattern, cell_value)
                
                for dept, number in matches:
                    course_key = f"{dept}{number}"
                    
                    # Skip duplicates
                    if course_key in seen_codes:
                        continue
                    
                    seen_codes.add(course_key)
                    
                    # Try to extract a name for this course
                    name = ""
                    credits = None
                    
                    # Check adjacent cells for potential names or credits
                    for dy, dx in [(0, 1), (0, 2), (1, 0), (0, -1)]:
                        ni, nj = i + dy, j + dx
                        if 0 <= ni < df.shape[0] and 0 <= nj < df.shape[1]:
                            neighbor = df.iloc[ni, nj]
                            
                            # If neighbor is a string, it might be a name
                            if isinstance(neighbor, str) and len(neighbor) > 3 and not re.search(course_pattern, neighbor):
                                name = neighbor
                                break
                            
                            # If neighbor is a number < 10, it might be credits
                            if isinstance(neighbor, (int, float)) and pd.notna(neighbor) and neighbor < 10:
                                credits = float(neighbor)
                    
                    # Create course object
                    course = {
                        'department': dept,
                        'number': number,
                        'courseCode': f"{dept} {number}",
                        'name': name,
                        'credits': credits,
                        'completed': False
                    }
                    
                    courses.append(course)
        
        print(f"Fallback extractor found {len(courses)} potential courses")
        return courses
        
    except Exception as e:
        print(f"Error in fallback extraction: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return []

def standardize_course_format(courses):
    """
    Standardize the format of extracted courses to ensure consistency
    across different extraction methods.
    """
    standardized = []
    
    for course in courses:
        # Create a new standardized course object
        std_course = {
            'department': course.get('department', ''),
            'number': course.get('number', ''),
            'courseCode': '',
            'name': course.get('name', ''),
            'credits': course.get('credits'),
            'prerequisites': course.get('prerequisites', 'None'),
            'completed': course.get('completed', False)
        }
        
        # Ensure courseCode exists
        if not std_course['courseCode'] and std_course['department'] and std_course['number']:
            std_course['courseCode'] = f"{std_course['department']} {std_course['number']}"
        
        # Add any semester information if available
        if 'semester' in course:
            std_course['semester'] = course['semester']
        
        # Add standardized course to list
        standardized.append(course)
    
    # Remove duplicates based on courseCode
    seen = set()
    unique_courses = []
    
    for course in standardized:
        code = course.get('courseCode', '')
        if code and code not in seen:
            seen.add(code)
            unique_courses.append(course)
    
    return unique_courses

def inspect_excel_structure(file_path):
    """Debug function to inspect Excel file structure"""
    try:
        # Load with pandas
        df = pd.read_excel(file_path, header=None)
        
        print(f"Excel file loaded: {file_path}")
        print(f"Shape: {df.shape} (rows × columns)")
        
        # Look at the first 10 rows to understand structure
        print("\nFirst 10 rows preview:")
        for i in range(min(10, df.shape[0])):
            row = df.iloc[i]
            row_preview = []
            for j in range(min(6, df.shape[1])):  # First 6 columns
                cell = row[j]
                if pd.notna(cell):
                    # Truncate long cell values
                    cell_str = str(cell)
                    if len(cell_str) > 20:
                        cell_str = cell_str[:17] + "..."
                    row_preview.append(f"Col{j}: {cell_str}")
            print(f"Row {i}: {' | '.join(row_preview) if row_preview else '(empty)'}")
        
        # Look for potential course codes in the entire sheet
        print("\nSearching for course code patterns:")
        course_patterns = [
            r'[A-Z]{2,4}\s*\d{3,4}[A-Z]?',  # Standard formats like "COSC 101", "CS350"
            r'course.*code|code|course',     # Column headers
            r'\b(fall|spring|summer|winter)\s+\d{4}\b',  # Semester headers
        ]
        
        pattern_matches = []
        for pattern in course_patterns:
            matches = []
            for i in range(df.shape[0]):
                for j in range(df.shape[1]):
                    cell = df.iloc[i, j]
                    if pd.notna(cell) and isinstance(cell, str) and re.search(pattern, cell, re.IGNORECASE):
                        matches.append((i, j, cell))
            if matches:
                pattern_matches.append((pattern, matches))
        
        for pattern, matches in pattern_matches:
            print(f"Pattern '{pattern}' matches:")
            for row, col, value in matches[:10]:  # Show first 10 matches
                print(f"  Row {row}, Col {col}: {value}")
            if len(matches) > 10:
                print(f"  ... and {len(matches) - 10} more matches")
        
        if not pattern_matches:
            print("No recognizable course patterns found in the file")
            
        # Return basic structure info
        return {
            "rows": df.shape[0],
            "columns": df.shape[1],
            "has_course_patterns": len(pattern_matches) > 0
        }
        
    except Exception as e:
        print(f"Error inspecting Excel file: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None

# Function to clean up old threads
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

# Start the cleanup thread when the server starts
cleanup_thread = threading.Timer(CLEANUP_INTERVAL, cleanup_expired_threads)
cleanup_thread.daemon = True  # Make the thread exit when the main program exits
cleanup_thread.start()

@app.route('/api/chat', methods=['POST'])
def chat():
    print("Received chat request")  # Debug log
    data = request.json
    user_message = data.get('message', '')
    session_id = data.get('session_id', 'default')
    
    print(f"Message: {user_message}, Session: {session_id}")  # Debug log
    
    try:
        # Get or create thread for this session
        thread_id = None
        if session_id in user_threads:
            thread_id = user_threads[session_id]['thread_id']
            print(f"Using existing thread: {thread_id}")
        
        # If no thread exists or if it's a new session, create a new thread
        if not thread_id:
            print("Creating new thread")
            thread = client.beta.threads.create()
            thread_id = thread.id
            user_threads[session_id] = {
                'thread_id': thread_id,
                'last_accessed': time.time()
            }
        
        # Add the user message to the thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )
        
        # Run the Assistant on the thread
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )
        
        # Wait for the run to complete (with timeout)
        max_wait_time = 30  # Maximum wait time in seconds
        start_time = time.time()
        
        while True:
            if time.time() - start_time > max_wait_time:
                return jsonify({
                    'message': "I'm taking longer than expected to respond. Please try again.",
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
        
        # Get the latest message from the Assistant
        messages = client.beta.threads.messages.list(
            thread_id=thread_id
        )
        
        # Extract the most recent assistant message
        assistant_messages = [msg for msg in messages.data if msg.role == "assistant"]
        if not assistant_messages:
            return jsonify({
                'message': "No response from assistant",
                'type': 'error',
                'session_id': session_id
            }), 500
        
        # Get the most recent message (first in the list due to ordering)
        latest_message = assistant_messages[0]
        
        # Extract text content
        response_text = ""
        for content_part in latest_message.content:
            if content_part.type == 'text':
                response_text += content_part.text.value
        
        # Update last accessed time
        user_threads[session_id]['last_accessed'] = time.time()
        
        # Return response
        return jsonify({
            'message': response_text,
            'type': 'bot',
            'session_id': session_id
        })
    
    except Exception as e:
        print(f"Error: {str(e)}")  # Debug log
        return jsonify({
            'message': f"Error: {str(e)}",
            'type': 'error',
            'session_id': session_id
        }), 500
        
@app.route('/api/upload-courses', methods=['POST'])
def upload_courses():
    """Handle course history file uploads"""
    print("Received file upload request")
    
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({
            'message': 'No file provided',
            'success': False
        }), 400
    
    file = request.files['file']
    session_id = request.form.get('session_id', 'default')
    
    # Check if a file was selected
    if file.filename == '':
        return jsonify({
            'message': 'No file selected',
            'success': False
        }), 400
    
    # Check if the file type is allowed
    if not allowed_file(file.filename):
        return jsonify({
            'message': 'File type not supported',
            'success': False
        }), 400
    
    try:
        # Save the file temporarily
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        print(f"File saved to {file_path}")
        
        # First, inspect the excel structure to understand what we're working with
        if filename.lower().endswith(('.xlsx', '.xls')):
            file_structure = inspect_excel_structure(file_path)
            print(f"File structure: {file_structure}")
        
        # Extract courses based on file type
        file_ext = filename.rsplit('.', 1)[1].lower()
        
        extracted_data = None
        
        if file_ext in ['xlsx', 'xls']:
            # Try different extraction methods in order
            
            # 1. First try the Towson degree plan extractor
            extracted_data = extract_towson_degree_plan(file_path)
            
            # 2. If no courses found, try generic Excel extraction
            if not extracted_data['courses']:
                print("Towson extractor found no courses, trying generic Excel extractor...")
                generic_courses = extract_courses_from_excel(file_path)
                if generic_courses:
                    extracted_data = {
                        'courses': generic_courses, 
                        'student_info': {},
                        'semesters': [],
                        'unit_summary': {}
                    }
            
            # 3. If still no courses, try fallback extraction
            if not extracted_data['courses']:
                print("Generic extractor found no courses, trying last-resort fallback extractor...")
                fallback_courses = extract_any_course_like_patterns(file_path)
                if fallback_courses:
                    extracted_data = {
                        'courses': fallback_courses,
                        'student_info': {},
                        'semesters': [],
                        'unit_summary': {}
                    }
        elif file_ext == 'csv':
            courses = extract_courses_from_csv(file_path)
            extracted_data = {
                'courses': courses, 
                'student_info': {},
                'semesters': [],
                'unit_summary': {}
            }
        elif file_ext == 'txt':
            courses = extract_courses_from_text(file_path)
            extracted_data = {
                'courses': courses, 
                'student_info': {},
                'semesters': [],
                'unit_summary': {}
            }
        
        # Clean up the temporary file
        try:
            os.remove(file_path)
        except:
            pass
        
        # Check if any courses were found
        if not extracted_data or not extracted_data['courses']:
            return jsonify({
                'message': 'No course information found in the file. Please check the file format or try a different file.',
                'success': False
            }), 400
        
        # Store the extracted data for this session
        user_courses[session_id] = extracted_data
        
        # Add a message to the thread about the uploaded courses
        if session_id in user_threads:
            thread_id = user_threads[session_id]['thread_id']
            
            # Create a summary of the degree plan for the assistant
            message = "The user has uploaded their course history with the following information:\n\n"
            
            # Add student info if available
            student_info = extracted_data.get('student_info', {})
            if student_info:
                message += "## Student Information\n"
                for key, value in student_info.items():
                    if value:
                        message += f"- {key.replace('_', ' ').title()}: {value}\n"
                message += "\n"
            
            # Add courses
            courses = extracted_data['courses']
            message += f"## Courses ({len(courses)} total)\n"
            
            # Group courses by department
            courses_by_dept = {}
            for course in courses:
                dept = course.get('department', 'Unknown')
                if dept not in courses_by_dept:
                    courses_by_dept[dept] = []
                courses_by_dept[dept].append(course)
            
            # List courses by department
            for dept, dept_courses in courses_by_dept.items():
                message += f"\n### {dept} Courses\n"
                for course in dept_courses:
                    # Format course info
                    info = []
                    if course.get('credits'):
                        info.append(f"{course['credits']} credits")
                    if course.get('prerequisites') and course['prerequisites'] != 'None':
                        info.append(f"Prereq: {course['prerequisites']}")
                    if course.get('completed'):
                        info.append("Completed")
                    else:
                        info.append("Not completed")
                    
                    # Add course line
                    number = course.get('number', '')
                    name = course.get('name', '')
                    message += f"- {dept} {number}"
                    if name:
                        message += f": {name}"
                    if info:
                        message += f" ({', '.join(info)})"
                    message += "\n"
            
            # Add guidance request
            message += "\nPlease provide course recommendations and advice for their degree progress."
            
            # Add this information to the thread
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message
            )
        
        # Prepare user-friendly response
        response_message = f"I've analyzed your file and found {len(extracted_data['courses'])} courses. "
        response_message += "What would you like to know about your degree progress?"
        
        # Return success with the extracted course info
        return jsonify({
            'message': response_message,
            'extractedCourses': extracted_data['courses'],
            'success': True
        })
        
    except Exception as e:
        print(f"Error processing upload: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'message': f'Error processing file: {str(e)}',
            'success': False
        }), 500

@app.route('/api/clear-session', methods=['POST'])
def clear_session():
    """Endpoint to explicitly clear a session"""
    data = request.json
    session_id = data.get('session_id', '')
    
    if session_id and session_id in user_threads:
        del user_threads[session_id]
        if session_id in user_courses:
            del user_courses[session_id]
        print(f"Cleared thread for session: {session_id}")
        return jsonify({"status": "success", "message": "Session cleared"})
    
    return jsonify({"status": "error", "message": "Session not found"}), 404

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    print("Starting server...")  # Debug log
    app.run(debug=True)