import React from 'react';
import '../styles/Footer.css';

const Footer = () => (
  <footer className="footer">
    <p className="footer-text">© {new Date().getFullYear()} Towson University. All rights reserved.</p>
  </footer>
);

export default Footer;