import React, { useState, useRef, useEffect } from 'react';
import { MessageCircle, X, Send } from 'lucide-react';
import '../styles/Chatbot.css';

const Chatbot = () => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([
    { text: 'Hello! How can I help you?', isBot: true }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  
  // Generate a timestamp-based session ID to ensure freshness
  const sessionId = useRef(`user-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`);

  // Force reset session on component mount
  useEffect(() => {
    console.log("Chatbot component mounted, new session ID:", sessionId.current);
    
    // Explicitly clear the session on the server
    fetch('http://localhost:5000/api/clear-session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId.current })
    }).catch(err => {
      // Ignore errors - if this fails, the session will be created fresh anyway
      console.log("Clear session request failed, but that's okay:", err);
    });
    
    // Function to handle page unload/refresh
    const handleBeforeUnload = () => {
      // Try to clear the session when the page unloads
      navigator.sendBeacon(
        'http://localhost:5000/api/clear-session',
        JSON.stringify({ session_id: sessionId.current })
      );
    };
    
    // Add event listener for page unload
    window.addEventListener('beforeunload', handleBeforeUnload);
    
    // Clean up event listener on component unmount
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);
  
  // Scroll to bottom of messages whenever messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e) => {
    console.log("Form submitted"); // Log when form is submitted
    e.preventDefault();
    if (!message.trim()) {
      console.log("Empty message, not sending");
      return;
    }
    
    console.log("Preparing to send message:", message);
    
    // Add user message to UI
    setMessages(prev => [...prev, { text: message, isBot: false }]);
    
    // Clear input field and show loading state
    const userMessage = message;
    setMessage('');
    setIsLoading(true);

    try {
      console.log("Making API call to backend");
      // Make API call to backend
      const response = await fetch('http://localhost:5000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
          session_id: sessionId.current
        }),
      });

      console.log("Response received, status:", response.status);
      
      if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
      }

      const data = await response.json();
      console.log("Response data:", data);
      
      // Add bot response to messages
      setMessages(prev => [...prev, { text: data.message, isBot: true }]);
    } catch (error) {
      console.error('Error sending message:', error);
      // Show error message in chat
      setMessages(prev => [...prev, { 
        text: 'Sorry, I encountered an error. Please try again later.', 
        isBot: true 
      }]);
    } finally {
      setIsLoading(false);
      console.log("Request completed");
    }
  };

  if (!isExpanded) {
    return (
      <button
        onClick={() => {
          console.log("Expanding chat window");
          setIsExpanded(true);
        }}
        className="chat-bubble"
      >
        <MessageCircle size={24} />
      </button>
    );
  }

  return (
    <div className="chat-window">
      <div className="chat-header">
        <div className="header-title-container">
          <MessageCircle className="header-icon" size={24} />
          <h3 className="header-title">Course Recommendation Assistant</h3>
        </div>
        <button 
          onClick={() => {
            console.log("Collapsing chat window");
            setIsExpanded(false);
          }}
          className="close-button"
        >
          <X size={20} />
        </button>
      </div>

      <div className="messages-container">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`message ${msg.isBot ? 'bot' : 'user'}`}
          >
            <div className="message-content">
              {msg.text}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="message bot">
            <div className="message-content loading">
              <span className="dot"></span>
              <span className="dot"></span>
              <span className="dot"></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form 
        onSubmit={(e) => {
          console.log("Form onSubmit triggered");
          handleSubmit(e);
        }} 
        className="input-container"
      >
        <div className="input-form">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Ask about course recommendations..."
            className="chat-input"
            disabled={isLoading}
          />
          <button
            type="submit"
            className="send-button"
            disabled={isLoading}
            onClick={() => console.log("Submit button clicked")}
          >
            <Send size={20} />
          </button>
        </div>
      </form>
    </div>
  );
};

export default Chatbot;