import React from 'react';
import Header from './Header.jsx';
import Footer from './Footer.jsx';
import Chatbot from './Chatbot.jsx';
import Page from './Page.jsx';
import '../styles/App.css';

const App = () => {
  return (
    <div className="app">
      <Header />
      <Page />
      <Chatbot />
      <Footer />
    </div>
  );
};

export default App;