import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import GraduationProgressTracker from '../src/components/GraduationProgressTracker';
import { beforeEach, vi } from 'vitest';

// Mock fetch
beforeEach(() => 
  global.fetch = vi.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        summary: {
          studentProgress: {
            completedCourses: ['CS101', 'CS102'],
            graduationProgress: 75,
            estimatedGraduation: 'May 2025',
            missingRequirements: { core: ['ART 101'], major: ['COSC 310'], math: ['MATH 101'], electives: ['COSC 299'] }
          }
        },
        validation: {
          graduationProgress: { totalCreditsEarned: 90, totalCreditsRequired: 120 },
          majorRequirements: { electivesCompleted: 3, electivesNeeded: 4 },
          studentCourses: [
            { courseCode: 'CS101', completed: true, semester: 'Fall', year: '2023' },
            { courseCode: 'CS102', completed: true, semester: 'Spring', year: '2024' }
          ]
        }
      }),
    })
  )
);

afterEach(() => {
  vi.restoreAllMocks();
});

describe('GraduationProgressTracker component', () => {
  it('renders progress information after loading', async () => {
    render(<GraduationProgressTracker sessionId="test-session" onClose={() => {}} />);
    await waitFor(() => {
      expect(screen.getByText(/Graduation Progress Tracker/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/90 of 120 credits completed/)).toBeInTheDocument();
    expect(screen.getByText(/May 2025/)).toBeInTheDocument();
  });
});

describe('GraduationProgressTracker course section tests', () => {
    it('renders completed course classes under "Completed Courses" section', async () => {
      render(<GraduationProgressTracker sessionId="test-session" onClose={() => {}} />);
  
      // Wait for Completed Courses section to appear
      const completedSection = await screen.findByText(/Courses Completed/i);
  
      // Get the parent container of that section
      const container = completedSection.closest('.progress-completed-courses');
      expect(container).toBeInTheDocument();
  
      // Assert each course is inside that container
      const withinCompleted = within(container);
      expect(await withinCompleted.findByText('CS101')).toBeInTheDocument();
      expect(await withinCompleted.findByText('CS102')).toBeInTheDocument();
    });

    it('renders correct counts for missing core, major, math, and electives courses', async () => {
      const { container } = render(<GraduationProgressTracker sessionId="test-session" onClose={() => {}} />);
      await screen.findByText(/Remaining Requirements/i);
      const requirementCategories = container.querySelectorAll('.requirements-section');
    
      // Core Curriculum
      const coreSection = Array.from(requirementCategories).find(section =>
        within(section).getByText(/Core Curriculum/i)
      );
      expect(coreSection).toBeInTheDocument();
      expect(within(coreSection).getByText('1')).toBeInTheDocument();
    
      // Major Requirements
      await waitFor(() => {
        expect(screen.getByText(/Major Requirements/i)).toBeInTheDocument();
      });
      const majorSection = Array.from(container.querySelectorAll('.requirements-section')).find(section =>
        within(section).queryByText(/Major Requirements/i)
      );
      expect(majorSection).toBeInTheDocument();
      expect(within(majorSection).getByText('1')).toBeInTheDocument();

      // Math
      await waitFor(() => {
        expect(screen.getByText(/Math Requirements/i)).toBeInTheDocument();
      });
      const mathSection = Array.from(container.querySelectorAll('.requirements-section')).find(section =>
        within(section).queryByText(/Math Requirements/i)
      );
      expect(mathSection).toBeInTheDocument();
      expect(within(mathSection).getByText('1')).toBeInTheDocument();
    
      // Electives
      await waitFor(() => {
        expect(screen.getByText(/Electives/i)).toBeInTheDocument();
      });
      const electivesSection = Array.from(container.querySelectorAll('.requirements-section')).find(section =>
        within(section).queryByText(/Electives/i)
      );
      expect(electivesSection).toBeInTheDocument();
      expect(within(electivesSection).getByText('1')).toBeInTheDocument();
    });
});