import React, { useState } from 'react';
import { MessageCircle, X, Send } from 'lucide-react';
import '../styles/Chatbot.css';

const Chatbot = () => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([
    { text: 'How can I help you find the right courses?', isBot: true }
  ]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!message.trim()) return;
    
    setMessages([...messages, { text: message, isBot: false }]);
    setMessage('');
    // Here you would typically make an API call to your Flask backend
  };

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

  return (
    <div className="chat-window">
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
      </div>

      <form onSubmit={handleSubmit} className="input-container">
        <div className="input-form">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Ask about course recommendations..."
            className="chat-input"
          />
          <button
            type="submit"
            className="send-button"
          >
            <Send size={20} />
          </button>
        </div>
      </form>
    </div>
  );
};

export default Chatbot;