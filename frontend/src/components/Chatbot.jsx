import React, { useState, useRef, useEffect } from 'react';
import { MessageCircle, X, Send, Upload, FileText, BarChart, Download, Info } from 'lucide-react';
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
    
    // FIXED: Only clear the session if this is not a page refresh
    const isPageRefresh = performance.navigation ? 
      performance.navigation.type === 1 : // Older browsers
      performance.getEntriesByType('navigation')[0]?.type === 'reload'; // Modern browsers
    
    if (!isPageRefresh) {
      // Clear any existing session only on fresh visits, not refreshes
      fetch('http://localhost:5000/api/clear-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId.current })
      }).catch(err => {
        console.log("Clear session request failed:", err);
      });
    }
    
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

  // Function to open advising information page
  const openAdvisingPage = () => {
    window.open('https://www.towson.edu/fcsm/departments/computerinfosci/resources/advising.html', '_blank');
  };

  // Function to download the conversation transcript
  const downloadConversation = () => {
    // Only download if there are messages
    if (messages.length <= 1) {
      alert("There's not enough conversation to download yet.");
      return;
    }
    
    // Format timestamp for filename
    const timestamp = new Date().toLocaleString().replace(/[/:\\]/g, '-');
    const filename = `course-assistant-transcript-${timestamp}.txt`;
    
    // Format the conversation content
    let content = "COURSE RECOMMENDATION ASSISTANT - CONVERSATION TRANSCRIPT\n";
    content += `Generated: ${new Date().toLocaleString()}\n\n`;
    
    // Add all messages to the content
    messages.forEach(msg => {
      const sender = msg.isBot ? "Assistant" : "You";
      
      // Handle different message types
      if (msg.type === 'progress-tracker') {
        content += `${sender}: [Graduation Progress Tracker was displayed]\n\n`;
      } else {
        content += `${sender}: ${msg.text}\n\n`;
      }
    });
    
    // Create a blob and download it
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    
    // Create a temporary link element to trigger the download
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    
    // Clean up
    URL.revokeObjectURL(url);
    document.body.removeChild(link);
  };

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

    // Check if user is asking about advising
    const advisingKeywords = [
      'advising', 'advisor', 'academic advisor', 'academic advising', 
      'degree completion plan', 'degree planning', 'academic planning',
      'graduation requirements', 'advisor contact', 'advising office',
      'advising help', 'advising resources', 'faculty advisor',
      'advising appointment', 'where to get advising', 'more information'
    ];
    
    // Check if message contains advising keywords
    const isAdvisingRequest = advisingKeywords.some(keyword => 
      trimmedMessage.toLowerCase().includes(keyword.toLowerCase())
    );
    
    if (isAdvisingRequest) {
      setIsLoading(false);
      
      // Add message from bot referencing the info button
      setMessages(prev => [
        ...prev, 
        { 
          text: "For detailed advising information and degree completion planning, you can click the information (i) button in the top-right corner of this chat window. It will take you to Towson University's official advising resources page where you'll find information about academic advising, faculty advisors, and how to schedule appointments.",
          isBot: true,
          type: 'text'
        }
      ]);
      return;
    }

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
          <div className="header-actions">
            {/* Info button for advising information */}
            <button 
              onClick={openAdvisingPage}
              className="info-button"
              title="Advising information"
            >
              <Info size={18} />
            </button>
            
            {/* Download button - only show if there's enough conversation */}
            {messages.length > 1 && (
              <button 
                onClick={downloadConversation}
                className="download-button"
                title="Download conversation transcript"
              >
                <Download size={18} />
              </button>
            )}
            
            <button 
              onClick={() => setIsExpanded(false)}
              className="close-button"
              title="Close chat"
            >
              <X size={20} />
            </button>
          </div>
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