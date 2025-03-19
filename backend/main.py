from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import time
import threading
from openai import OpenAI
from dotenv import load_dotenv

# Load the environment variable
load_dotenv()

# Initialize Flask server
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize OpenAI client with proper error handling
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("Warning: OpenAI API key not found in environment variables.")
    api_key = "your-api-key-here"  # Replace with your actual key if needed

client = OpenAI(api_key=api_key)

# Simple in-memory chat history with session expiration
chat_sessions = {}
session_timestamps = {}  # Track when sessions were last accessed

# Session cleanup settings
SESSION_TIMEOUT = 10  # Sessions expire after just 10 seconds of inactivity
CLEANUP_INTERVAL = 5   # Run cleanup every 5 seconds

# Load the CS program information from JSON file
try:
    with open('cosc_major.json', 'r') as file:
        CS_PROGRAM_INFO = json.load(file)
    print("Successfully loaded CS program information from JSON file")
except Exception as e:
    print(f"Error loading CS program JSON: {str(e)}")
    # Fallback in case the file doesn't exist yet
    CS_PROGRAM_INFO = {
        "program": "Computer Science",
        "institution": "Towson University",
        "catalogYear": "2023-2024"
    }

def generate_system_prompt():
    """Generate a structured system prompt using the JSON program information"""
    
    # Basic introduction
    prompt = f"""You are a helpful course recommendation assistant for {CS_PROGRAM_INFO.get('institution', 'Towson University')}'s {CS_PROGRAM_INFO.get('program', 'Computer Science')} program. 
You help students validate what courses they have taken, curate a schedule for the following semester, and 
find suitable courses based on their interests, academic history, and program requirements.

When recommending courses:
1. Consider prerequisites carefully
2. Check when courses are offered (Fall, Spring, Summer)
3. Balance workload considering course difficulty
4. Prioritize required courses before electives
5. Suggest courses that build on the student's interests

Be concise, friendly, and informative in your responses.
"""
    
    # Add course catalog information
    prompt += f"\n## {CS_PROGRAM_INFO.get('program', 'Computer Science')} Program Information (Catalog Year {CS_PROGRAM_INFO.get('catalogYear', '2023-2024')})\n\n"
    
    # Add required courses section
    prompt += "### Required Computer Science Courses\n"
    if 'requiredCourses' in CS_PROGRAM_INFO:
        for course in CS_PROGRAM_INFO['requiredCourses']:
            prereqs = ", ".join(course.get('prerequisites', []))
            offerings = ", ".join(course.get('offerings', []))
            prompt += f"- {course['courseCode']}: {course['title']} ({course['units']} units)\n"
            if prereqs:
                prompt += f"  Prerequisites: {prereqs}\n"
            if offerings:
                prompt += f"  Offered: {offerings}\n"
    
    # Add elective courses sections
    if 'electiveCourses' in CS_PROGRAM_INFO:
        # Group A
        if 'groupA' in CS_PROGRAM_INFO['electiveCourses']:
            prompt += f"\n### Elective Courses - Group A ({CS_PROGRAM_INFO['electiveCourses']['groupA'].get('description', '')})\n"
            for course in CS_PROGRAM_INFO['electiveCourses']['groupA']['courses']:
                prereqs = ", ".join(course.get('prerequisites', []))
                offerings = ", ".join(course.get('offerings', []))
                prompt += f"- {course['courseCode']}: {course['title']} ({course['units']} units)\n"
                if prereqs:
                    prompt += f"  Prerequisites: {prereqs}\n"
                if offerings:
                    prompt += f"  Offered: {offerings}\n"
        
        # Group B
        if 'groupB' in CS_PROGRAM_INFO['electiveCourses']:
            prompt += f"\n### Elective Courses - Group B ({CS_PROGRAM_INFO['electiveCourses']['groupB'].get('description', '')})\n"
            for course in CS_PROGRAM_INFO['electiveCourses']['groupB']['courses']:
                prereqs = ", ".join(course.get('prerequisites', []))
                offerings = ", ".join(course.get('offerings', []))
                prompt += f"- {course['courseCode']}: {course['title']} ({course['units']} units)\n"
                if prereqs:
                    prompt += f"  Prerequisites: {prereqs}\n"
                if offerings:
                    prompt += f"  Offered: {offerings}\n"
    
    # Add required mathematics courses
    if 'requiredMathematics' in CS_PROGRAM_INFO:
        prompt += "\n### Required Mathematics Courses\n"
        for course in CS_PROGRAM_INFO['requiredMathematics']:
            prereqs = ", ".join(course.get('prerequisites', []))
            offerings = ", ".join(course.get('offerings', []))
            prompt += f"- {course['courseCode']}: {course['title']} ({course['units']} units)\n"
            if 'alternateWith' in course:
                prompt += f"  Alternative to: {course['alternateWith']}\n"
            if prereqs:
                prompt += f"  Prerequisites: {prereqs}\n"
            if offerings:
                prompt += f"  Offered: {offerings}\n"
    
    # Add core courses
    if 'requiredCore' in CS_PROGRAM_INFO:
        prompt += "\n### Required Core Courses\n"
        for course in CS_PROGRAM_INFO['requiredCore']:
            prereqs = ", ".join(course.get('prerequisites', []))
            offerings = ", ".join(course.get('offerings', []))
            prompt += f"- {course['courseCode']}: {course['title']} ({course['units']} units)\n"
            if prereqs:
                prompt += f"  Prerequisites: {prereqs}\n"
            if offerings:
                prompt += f"  Offered: {offerings}\n"
    
    return prompt

def cleanup_expired_sessions():
    """Remove expired chat sessions to free up memory"""
    current_time = time.time()
    expired_sessions = []
    
    for session_id, timestamp in list(session_timestamps.items()):
        if current_time - timestamp > SESSION_TIMEOUT:
            expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        if session_id in chat_sessions:
            del chat_sessions[session_id]
        if session_id in session_timestamps:
            del session_timestamps[session_id]
    
    if expired_sessions:
        print(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    # Schedule the next cleanup
    threading.Timer(CLEANUP_INTERVAL, cleanup_expired_sessions).start()

# Start the cleanup thread when the server starts
cleanup_thread = threading.Timer(CLEANUP_INTERVAL, cleanup_expired_sessions)
cleanup_thread.daemon = True  # Make the thread exit when the main program exits
cleanup_thread.start()

@app.route('/api/chat', methods=['POST'])
def chat():
    print("Received chat request")  # Debug log
    data = request.json
    user_message = data.get('message', '')
    session_id = data.get('session_id', 'default')
    
    print(f"Message: {user_message}, Session: {session_id}")  # Debug log
    
    # Force a new session for each request by checking if the session ID starts with a specific prefix
    # This is a simple way to detect new browser sessions from our frontend
    if session_id.startswith('user-') and '-' in session_id:
        # Extract the timestamp portion from the session ID
        try:
            timestamp_part = session_id.split('-')[1]
            # If this timestamp is within a few seconds of the current time, treat it as a new session
            if abs(time.time() - float(timestamp_part)/1000) < 5:  # 5 second window
                print(f"Detected new browser session, clearing history for: {session_id}")
                if session_id in chat_sessions:
                    chat_sessions[session_id] = []
        except (IndexError, ValueError):
            pass  # If we can't parse the timestamp, just continue
    
    # Initialize or get chat history for this session
    if session_id not in chat_sessions:
        print(f"Creating new session: {session_id}")
        chat_sessions[session_id] = []
    
    # Update the session timestamp
    session_timestamps[session_id] = time.time()
    
    # Add user message to chat history
    chat_sessions[session_id].append({"role": "user", "content": user_message})
    
    # Generate the system prompt from the JSON data
    system_content = generate_system_prompt()
    
    # Set up messages for OpenAI
    messages = [{"role": "system", "content": system_content}]
    
    # Add conversation history
    messages.extend(chat_sessions[session_id])
    
    # Get response from OpenAI
    try:
        print("Sending message to OpenAI")  # Debug log
        
        response = client.chat.completions.create(
            model="gpt-4",  # Using GPT-4 for better recommendations
            messages=messages,
            temperature=0.7,
            max_tokens=800
        )
        
        bot_response = response.choices[0].message.content
        print(f"Received response: {bot_response[:50]}...")  # Debug log (first 50 chars)
        
        # Add bot response to chat history
        chat_sessions[session_id].append({"role": "assistant", "content": bot_response})
        
        # Return response
        return jsonify({
            'message': bot_response,
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

@app.route('/api/clear-session', methods=['POST'])
def clear_session():
    """Endpoint to explicitly clear a session"""
    data = request.json
    session_id = data.get('session_id', '')
    
    if session_id and session_id in chat_sessions:
        del chat_sessions[session_id]
        if session_id in session_timestamps:
            del session_timestamps[session_id]
        print(f"Cleared session: {session_id}")
        return jsonify({"status": "success", "message": "Session cleared"})
    
    return jsonify({"status": "error", "message": "Session not found"}), 404

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    print("Starting server...")  # Debug log
    app.run(debug=True)