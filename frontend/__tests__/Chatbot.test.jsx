import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Chatbot from '../src/components/Chatbot';

// Mock scrollIntoView
window.HTMLElement.prototype.scrollIntoView = vi.fn();

// Mock fetch
global.fetch = vi.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ message: 'Test response from server' }),
  })
);

describe('Chatbot component', () => {
  beforeEach(() => {
    sessionStorage.clear();
    fetch.mockClear();
  });

  it('renders chatbot bubble initially', () => {
    render(<Chatbot />);
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('expands chat window on bubble click', () => {
    render(<Chatbot />);
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText(/Course Recommendation Assistant/i)).toBeInTheDocument();
  });

  it('sends user message and receives bot reply', async () => {
    render(<Chatbot />);
    fireEvent.click(screen.getByRole('button'));

    const input = screen.getByPlaceholderText(/Ask about course recommendations/i);
    fireEvent.change(input, { target: { value: 'Hello bot!' } });

    fireEvent.submit(input.closest('form'));

    await waitFor(() => {
      expect(screen.getByText(/Test response from server/)).toBeInTheDocument();
    });
  });
});