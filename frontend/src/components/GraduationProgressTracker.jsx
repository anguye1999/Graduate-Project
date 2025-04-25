import React, { useState, useEffect } from 'react';
import { BookOpen, Calendar, AlertCircle } from 'lucide-react';
import '../styles/GraduationProgressTracker.css';
import { useProgress } from './ProgressContext';

const GraduationProgressTracker = ({ sessionId, onClose }) => {
  const [progressData, setProgressData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [track, setTrack] = useState('Software Engineering');
  
  // Safely use the context - handle case when context might not be available
  let refreshTrigger = 0;
  try {
    const context = useProgress();
    refreshTrigger = context ? context.refreshTrigger : 0;
  } catch (err) {
    console.log("Progress context not available:", err);
  }

  useEffect(() => {
    // Fetch graduation progress data from the server
    const fetchProgressData = async () => {
      setIsLoading(true);
      try {
        const response = await fetch('http://localhost:5000/api/validate-courses', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId, track: track })
        });
        
        if (!response.ok) {
          throw new Error('Failed to fetch graduation progress');
        }
        
        const data = await response.json();
        setProgressData(data);
      } catch (err) {
        setError(err.message);
        console.error('Error fetching graduation progress:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchProgressData();
  }, [sessionId, track, refreshTrigger]);

  // Handle track change
  const handleTrackChange = (e) => {
    setTrack(e.target.value);
  };

  if (isLoading) {
    return (
      <div className="progress-tracker-container loading">
        <div className="progress-loading">
          <div className="progress-spinner"></div>
          <p>Loading graduation progress...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="progress-tracker-container error">
        <div className="progress-error">
          <AlertCircle size={24} />
          <p>Failed to load graduation progress: {error}</p>
          <button onClick={onClose} className="progress-close-btn">Close</button>
        </div>
      </div>
    );
  }

  if (!progressData || !progressData.summary || !progressData.summary.studentProgress) {
    return (
      <div className="progress-tracker-container error">
        <div className="progress-error">
          <AlertCircle size={24} />
          <p>No graduation progress data available. Have you uploaded your course history?</p>
          <button onClick={onClose} className="progress-close-btn">Close</button>
        </div>
      </div>
    );
  }

  const { studentProgress } = progressData.summary;
  const {
    completedCourses,
    graduationProgress,
    estimatedGraduation,
    missingRequirements
  } = studentProgress;

  // Calculate total remaining requirements
  const coreRemaining = missingRequirements.core.length;
  const majorRemaining = missingRequirements.major.length;
  const electivesRemaining = progressData.validation?.majorRequirements?.electivesNeeded - 
                           progressData.validation?.majorRequirements?.electivesCompleted || 0;
  
  const totalRemaining = coreRemaining + majorRemaining + electivesRemaining;
  
  // Calculate total credits earned
  const totalCredits = progressData.validation?.graduationProgress?.totalCreditsRequired || 120;
  const earnedCredits = progressData.validation?.graduationProgress?.totalCreditsEarned || 0;

  return (
    <div className="progress-tracker-container">
      <div className="progress-tracker-header">
        <h2 className="progress-title">Graduation Progress Tracker</h2>
        <button onClick={onClose} className="progress-close-btn">×</button>
      </div>
      
      <div className="progress-track-selector">
        <label htmlFor="track-select">Degree Track:</label>
        <select 
          id="track-select" 
          value={track} 
          onChange={handleTrackChange}
          className="track-select"
        >
          <option value="Software Engineering">Software Engineering</option>
          <option value="Cybersecurity">Cybersecurity</option>
          <option value="General">General Computer Science</option>
        </select>
      </div>
      
      <div className="progress-credits">
        <span className="credits-text">{earnedCredits} of {totalCredits} credits completed</span>
        <span className="progress-percentage">{graduationProgress}%</span>
      </div>
      
      <div className="progress-bar-container">
        <div 
          className="progress-bar-fill" 
          style={{ width: `${graduationProgress}%` }}
        ></div>
      </div>
      
      <div className={`progress-status ${graduationProgress >= 85 ? 'excellent' : 
                                         graduationProgress >= 60 ? 'good' : 
                                         graduationProgress >= 30 ? 'fair' : 
                                         'poor'}`}>
        <p>
          {graduationProgress >= 85 ? 'Excellent progress! You\'re almost there.' :
           graduationProgress >= 60 ? 'You\'re making good progress toward your degree.' :
           graduationProgress >= 30 ? 'You\'re making fair progress. Keep going!' :
           'You have a ways to go, but every course counts!'}
        </p>
      </div>
      
      <div className="progress-graduation-date">
        <Calendar size={18} />
        <span>Estimated graduation: <strong>{estimatedGraduation}</strong></span>
      </div>
      
      <h3 className="progress-section-title">Remaining Requirements</h3>
      
      <div className="progress-requirements-container">
        <div className="progress-requirement-category">
          <BookOpen size={18} />
          <span className="requirement-label">Core Curriculum</span>
          <span className="requirement-count">{coreRemaining}</span>
        </div>
        
        <div className="progress-requirement-category">
          <BookOpen size={18} />
          <span className="requirement-label">Major Requirements</span>
          <span className="requirement-count">{majorRemaining}</span>
        </div>
        
        <div className="progress-requirement-category">
          <BookOpen size={18} />
          <span className="requirement-label">Electives</span>
          <span className="requirement-count">{electivesRemaining}</span>
        </div>
      </div>
      
      {totalRemaining > 0 && (
        <div className="progress-warning">
          <AlertCircle size={16} />
          <p>You have {totalRemaining} remaining course requirements to complete.</p>
        </div>
      )}
      
      <div className="progress-completed-courses">
        <h3 className="progress-section-title">Courses Completed ({completedCourses.length})</h3>
        <div className="course-tags">
          {completedCourses.slice(0, 5).map((course, index) => (
            <span key={index} className="course-tag">{course}</span>
          ))}
          {completedCourses.length > 5 && (
            <span className="course-tag more">+{completedCourses.length - 5} more</span>
          )}
        </div>
      </div>
      
      <div className="progress-actions">
        <button 
          className="progress-action-btn view-recommended"
          onClick={() => window.location.href = '/recommended-courses'}
        >
          View Recommended Courses
        </button>
      </div>
    </div>
  );
};

export default GraduationProgressTracker;