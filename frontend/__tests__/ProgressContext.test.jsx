import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ProgressProvider, useProgress } from '../src/components/ProgressContext';

const TestComponent = () => {
  const { refreshTrigger, refreshProgress } = useProgress();

  return (
    <div>
      <span>Trigger: {refreshTrigger}</span>
      <button onClick={refreshProgress}>Refresh</button>
    </div>
  );
};

describe('ProgressContext', () => {
  it('provides initial trigger value and updates on refresh', () => {
    render(
      <ProgressProvider>
        <TestComponent />
      </ProgressProvider>
    );

    expect(screen.getByText(/Trigger: 0/)).toBeInTheDocument();

    const button = screen.getByText('Refresh');
    fireEvent.click(button);
    expect(screen.getByText(/Trigger: 1/)).toBeInTheDocument();

    fireEvent.click(button);
    expect(screen.getByText(/Trigger: 2/)).toBeInTheDocument();
  });
});