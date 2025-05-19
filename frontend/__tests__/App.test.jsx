import React from 'react';
import { render, screen } from '@testing-library/react';
import App from '../src/components/App';
import { vi } from 'vitest';

// Mock child components (with default keys)
vi.mock('../src/components/Header.jsx', () => ({
  default: () => <div>Header Component</div>
}));
vi.mock('../src/components/Footer.jsx', () => ({
  default: () => <div>Footer Component</div>
}));
vi.mock('../src/components/Page.jsx', () => ({
  default: () => <div>Page Component</div>
}));
vi.mock('../src/components/Chatbot.jsx', () => ({
  default: () => <div>Chatbot Component</div>
}));

describe('App component', () => {
  it('renders main app layout with header, page, chatbot, and footer', () => {
    render(<App />);
    expect(screen.getByText(/Header Component/)).toBeInTheDocument();
    expect(screen.getByText(/Page Component/)).toBeInTheDocument();
    expect(screen.getByText(/Chatbot Component/)).toBeInTheDocument();
    expect(screen.getByText(/Footer Component/)).toBeInTheDocument();
  });
});