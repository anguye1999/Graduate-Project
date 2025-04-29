import React, { useState, useEffect } from 'react';
import { BookOpen, Calendar, AlertCircle, ChevronDown, ChevronRight, CheckCircle, Info } from 'lucide-react';
import '../styles/GraduationProgressTracker.css';
import { useProgress } from './ProgressContext';

// Simplified CoursesCompletedSection Component 
const CoursesCompletedSection = ({ completedCourses, detailedCourses }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  // Filter courses that have completion status = true
  const completedDetailedCourses = detailedCourses.filter(course => course.completed);
  
  // Function to toggle expanded view - only expands, doesn't collapse
  const toggleExpanded = () => {
    setIsExpanded(true);
  };
  
  // Determine which courses to display based on expanded state
  const coursesToDisplay = isExpanded 
    ? completedDetailedCourses 
    : completedDetailedCourses.slice(0, 5);
  
  // Calculate how many more courses there are
  const remainingCount = completedDetailedCourses.length - 5;
  
  return (
    <div className="progress-completed-courses">
      <h3 className="progress-section-title">Courses Completed ({completedCourses.length})</h3>
      
      <div className="course-tags">
        {coursesToDisplay.map((course, index) => (
          <span key={index} className="course-tag">
            <span className="course-code">{course.courseCode}</span>
            {(course.semester && course.year) ? (
              <span className="course-semester-info"> - {course.semester} {course.year}</span>
            ) : null}
          </span>
        ))}
        
        {!isExpanded && remainingCount > 0 && (
          <span 
            className="course-tag more" 
            onClick={toggleExpanded}
          >
            +{remainingCount} more
          </span>
        )}
      </div>
    </div>
  );
};

// Main GraduationProgressTracker Component
const GraduationProgressTracker = ({ sessionId, onClose }) => {
  const [progressData, setProgressData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Expanded sections state
  const [expandedSections, setExpandedSections] = useState({
    core: false,
    major: false,
    electives: false
  });
  
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
          body: JSON.stringify({ 
            session_id: sessionId, 
            track: 'Software Engineering' // Hardcoded value
          })
        });
        
        if (!response.ok) {
          throw new Error('Failed to fetch graduation progress');
        }
        
        const data = await response.json();
        console.log("Progress data loaded:", data);
        setProgressData(data);
      } catch (err) {
        setError(err.message);
        console.error('Error fetching graduation progress:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchProgressData();
  }, [sessionId, refreshTrigger]);

  // Toggle section expansion
  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
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
  
  // Ensure electives remaining is never negative
  const electivesNeeded = progressData.validation?.majorRequirements?.electivesNeeded || 0;
  const electivesCompleted = progressData.validation?.majorRequirements?.electivesCompleted || 0;
  const electivesRemaining = Math.max(0, electivesNeeded - electivesCompleted);
  
  const totalRemaining = coreRemaining + majorRemaining + electivesRemaining;
  
  // Calculate total credits earned
  const totalCredits = progressData.validation?.graduationProgress?.totalCreditsRequired || 120;
  const earnedCredits = progressData.validation?.graduationProgress?.totalCreditsEarned || 0;
  const creditsRemaining = totalCredits - earnedCredits;

  // Get the detailed course information with semester/year if available
  const detailedCourses = progressData.validation?.studentCourses || [];
  
  // Get detailed missing requirements
  const missingCoreRequirements = progressData.validation?.coreRequirements?.missingCore || [];
  const missingMajorRequirements = progressData.validation?.majorRequirements?.missingRequired || [];

  return (
    <div className="progress-tracker-container">
      <div className="progress-tracker-header">
        <h2 className="progress-title">Graduation Progress Tracker</h2>
        <button onClick={onClose} className="progress-close-btn">×</button>
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
      
      <div className="progress-details-container">
        <div className="progress-detail-item">
          <Calendar size={18} />
          <span>Estimated graduation: <strong>{estimatedGraduation}</strong></span>
        </div>
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
      
      <h3 className="progress-section-title">Remaining Requirements</h3>
      
      {/* Core Curriculum Requirements */}
      <div className="requirements-section">
        <div 
          className="requirements-header" 
          onClick={() => toggleSection('core')}
        >
          {expandedSections.core ? 
            <ChevronDown size={20} className="expand-icon" /> : 
            <ChevronRight size={20} className="expand-icon" />
          }
          <div className="requirements-header-content">
            <BookOpen size={18} />
            <span className="requirement-label">Core Curriculum</span>
            <span className={`requirement-count ${coreRemaining > 0 ? 'missing' : 'complete'}`}>
              {coreRemaining}
            </span>
          </div>
        </div>
        
        {expandedSections.core && (
          <div className="requirements-detail">
            {coreRemaining > 0 ? (
              <div className="missing-requirements">
                <h4>Missing Core Requirements:</h4>
                <ul className="missing-list">
                  {missingCoreRequirements.map((requirement, index) => (
                    <li key={index} className="missing-item">
                      <span className="missing-category">{requirement.category}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <div className="complete-requirements">
                <CheckCircle size={18} />
                <span>All core curriculum requirements completed</span>
              </div>
            )}
          </div>
        )}
      </div>
      
      {/* Major Requirements */}
      <div className="requirements-section">
        <div 
          className="requirements-header" 
          onClick={() => toggleSection('major')}
        >
          {expandedSections.major ? 
            <ChevronDown size={20} className="expand-icon" /> : 
            <ChevronRight size={20} className="expand-icon" />
          }
          <div className="requirements-header-content">
            <BookOpen size={18} />
            <span className="requirement-label">Major Requirements</span>
            <span className={`requirement-count ${majorRemaining > 0 ? 'missing' : 'complete'}`}>
              {majorRemaining}
            </span>
          </div>
        </div>
        
        {expandedSections.major && (
          <div className="requirements-detail">
            {majorRemaining > 0 ? (
              <div className="missing-requirements">
                <h4>Missing Major Courses:</h4>
                <ul className="missing-list">
                  {missingMajorRequirements.map((requirement, index) => (
                    <li key={index} className="missing-item">
                      <span className="missing-course">{requirement.courseCode}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <div className="complete-requirements">
                <CheckCircle size={18} />
                <span>All major requirements completed</span>
              </div>
            )}
          </div>
        )}
      </div>
      
      {/* Electives */}
      <div className="requirements-section">
        <div 
          className="requirements-header" 
          onClick={() => toggleSection('electives')}
        >
          {expandedSections.electives ? 
            <ChevronDown size={20} className="expand-icon" /> : 
            <ChevronRight size={20} className="expand-icon" />
          }
          <div className="requirements-header-content">
            <BookOpen size={18} />
            <span className="requirement-label">Electives</span>
            <span className={`requirement-count ${electivesRemaining > 0 ? 'missing' : 'complete'}`}>
              {electivesRemaining}
            </span>
          </div>
        </div>
        
        {expandedSections.electives && (
          <div className="requirements-detail">
            {electivesRemaining > 0 ? (
              <div className="missing-requirements">
                <h4>Elective Requirements:</h4>
                <p className="elective-info">
                  You need to complete {electivesRemaining} more elective course{electivesRemaining > 1 ? 's' : ''}.
                </p>
                
                {/* Display available elective options */}
                {progressData.validation?.majorRequirements?.track === "Software Engineering" && (
                  <div className="elective-recommendations">
                    <h5>Recommended Software Engineering Electives:</h5>
                    <ul className="missing-list">
                      {progressData.validation?.software_track_electives?.length > 0 ? (
                        progressData.validation.software_track_electives.map((elective, index) => (
                          <li key={index} className="elective-option">
                            <span className="elective-course">{elective.courseCode}</span>
                          </li>
                        ))
                      ) : (
                        <p>No specific elective options available. Check with your academic advisor.</p>
                      )}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <div className="complete-requirements">
                <CheckCircle size={18} />
                <span>All elective requirements completed</span>
              </div>
            )}
          </div>
        )}
      </div>
      
      {totalRemaining > 0 && (
        <div className="progress-warning">
          <AlertCircle size={16} />
          <p>You have {totalRemaining} remaining course requirements to complete.</p>
        </div>
      )}
      
      {/* Simplified Courses Completed Section */}
      <CoursesCompletedSection 
        completedCourses={completedCourses}
        detailedCourses={detailedCourses}
      />
      
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