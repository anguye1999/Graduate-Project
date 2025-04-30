import React, { useState, useRef, useEffect } from 'react';
import { MessageCircle, X, Send, Upload, FileText, BarChart } from 'lucide-react';
import '../styles/CourseUpload.css';
import '../styles/Chatbot.css';
import CourseUpload from './CourseUpload';
import GraduationProgressTracker from './GraduationProgressTracker';
import { useProgress } from './ProgressContext';

const Chatbot = () => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([
    { text: 'Hello! How can I help you today? You can ask me questions or upload your course history.', isBot: true, type: 'text' }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [showFileUpload, setShowFileUpload] = useState(false);
  const [uploadedCourses, setUploadedCourses] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);
  const messagesEndRef = useRef(null);

   // Safely use the context
  let refreshProgress = () => console.log("Progress refresh not available");
  try {
    const context = useProgress();
    refreshProgress = context ? context.refreshProgress : refreshProgress;
  } catch (err) {
    console.log("Progress context not available:", err);
  }
  
  // Generate a session ID
  const sessionId = useRef(`user-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`);

  // Store session ID and setup component
  useEffect(() => {
    // Save session ID to storage
    sessionStorage.setItem('chatSessionId', sessionId.current);
    console.log("Chatbot component mounted, session ID:", sessionId.current);
    
    // Clear any existing session
    fetch('http://localhost:5000/api/clear-session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId.current })
    }).catch(err => {
      console.log("Clear session request failed:", err);
    });
    
    // Setup cleanup for page unload
    const handleBeforeUnload = () => {
      navigator.sendBeacon(
        'http://localhost:5000/api/clear-session',
        JSON.stringify({ session_id: sessionId.current })
      );
    };
    
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, []);
  
  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Function to format message text with paragraphs
  const formatMessage = (text) => {
    if (!text) return '';
    
    // Handle paragraphs
    let formattedText = text.split('\n').map((paragraph, index) => {
      if (paragraph.trim() === '') return null;
      return <p key={index}>{paragraph}</p>;
    }).filter(Boolean);
    
    return formattedText.length > 0 ? formattedText : text;
  };

  // Handle file processing after upload
  const handleFileProcessed = (data) => {
    const { extractedCourses, message, success } = data;
    
    if (!success || !extractedCourses) {
      setMessages(prev => [
        ...prev,
        { 
          text: `I encountered an issue processing your file. ${data.message || 'Please try again.'}`, 
          isBot: true,
          type: 'text'
        }
      ]);
    } else {
      // Store uploaded courses and update status
      setUploadedCourses(extractedCourses);
      setUploadStatus({
        count: extractedCourses.length,
        timestamp: new Date().toLocaleString()
      });
      
      // Add bot message about the upload
      setMessages(prev => [
        ...prev,
        { 
          text: message || `I've analyzed your course history and found ${extractedCourses.length} courses. What would you like to know?`, 
          isBot: true,
          type: 'text'
        }
      ]);
    }
    
    // Always hide the upload component after processing
    setShowFileUpload(false);
  };

  // Handle message submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmedMessage = message.trim();
    if (!trimmedMessage) return;
    
    // Add user message and reset input
    setMessages(prev => [...prev, { text: trimmedMessage, isBot: false, type: 'text' }]);
    setMessage('');
    setIsLoading(true);

    // Check if user is asking for progress
    const progressKeywords = [
      'show progress', 'graduation progress', 'degree progress', 
      'track progress', 'view progress', 'my progress', 
      'how am i doing', 'graduation tracker', 'show my courses',
      'progress tracker', 'graduation status', 'credits completed',
      'requirements left', 'progress visualization'
    ];
    
    // Check if message contains progress keywords
    const isProgressRequest = progressKeywords.some(keyword => 
      trimmedMessage.toLowerCase().includes(keyword.toLowerCase())
    );
    
    if (isProgressRequest) {
      setIsLoading(false);
      
      // Add message from bot acknowledging the request
      setMessages(prev => [
        ...prev, 
        { 
          text: "Here's your graduation progress tracker. You can see your completed requirements and what you still need to graduate.", 
          isBot: true,
          type: 'text'
        },
        // Add the progress tracker as a special message
        {
          isBot: true,
          type: 'progress-tracker',
          sessionId: sessionId.current
        }
      ]);
      return;
    }

    try {
      // Send message to backend
      const response = await fetch('http://localhost:5000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: trimmedMessage,
          session_id: sessionId.current
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();
      setMessages(prev => [...prev, { text: data.message, isBot: true, type: 'text' }]);
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, { 
        text: 'Sorry, I encountered an error. Please try again later.', 
        isBot: true,
        type: 'text'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Render chat bubble when collapsed
  if (!isExpanded) {
    return (
      <button
        onClick={() => setIsExpanded(true)}
        className="chat-bubble"
      >
        <MessageCircle size={24} />
      </button>
    );
  }

  // Render full chat interface
  return (
    <div className="chat-window">
      <div className="inner-chat-window">
        <div className="chat-header">
          <div className="header-title-container">
            <MessageCircle className="header-icon" size={24} />
            <h3 className="header-title">Course Recommendation Assistant</h3>
          </div>
          <button 
            onClick={() => setIsExpanded(false)}
            className="close-button"
          >
            <X size={20} />
          </button>
        </div>

        <div className="messages-container">
          {/* Render messages with improved formatting */}
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`message ${msg.isBot ? 'bot' : 'user'}`}
            >
              {msg.type === 'progress-tracker' ? (
                <div className="message-progress-tracker">
                  <GraduationProgressTracker 
                    sessionId={msg.sessionId}
                    onClose={() => {
                      // Optional: if you want to add close functionality
                      setMessages(prev => prev.filter((_, i) => i !== index));
                    }}
                  />
                </div>
              ) : (
                <div className="message-content">
                  {msg.isBot ? formatMessage(msg.text) : msg.text}
                </div>
              )}
            </div>
          ))}
          
          {/* Loading indicator */}
          {isLoading && (
            <div className="message bot">
              <div className="message-content loading">
                <span className="dot"></span>
                <span className="dot"></span>
                <span className="dot"></span>
              </div>
            </div>
          )}
          
          {/* File upload component */}
          {showFileUpload && (
            <div className="file-upload-container">
              <CourseUpload 
                onFileProcessed={handleFileProcessed}
                onCancel={() => setShowFileUpload(false)}
              />
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input form */}
        <form onSubmit={handleSubmit} className="input-container">
          <div className="input-form">
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Ask about course recommendations"
              className="chat-input"
              disabled={isLoading}
            />
            
            {/* Upload button */}
            <button
              type="button"
              className={`upload-button ${uploadedCourses ? 'has-upload' : ''}`}
              onClick={() => setShowFileUpload(true)}
              disabled={isLoading}
              title={uploadedCourses ? "Update course history" : "Upload course history"}
            >
              {uploadedCourses ? <FileText size={20} /> : <Upload size={20} />}
            </button>
            
            {/* Send button */}
            <button
              type="submit"
              className="send-button"
              disabled={isLoading}
            >
              <Send size={20} />
            </button>
          </div>
          
          {/* Upload status indicator */}
          {uploadStatus && (
            <div className="uploaded-status">
              <FileText size={14} />
              <span>{uploadStatus.count} courses uploaded</span>
              <span className="upload-timestamp">{uploadStatus.timestamp}</span>
            </div>
          )}
        </form>
      </div>
    </div>
  );
};

export default Chatbot;