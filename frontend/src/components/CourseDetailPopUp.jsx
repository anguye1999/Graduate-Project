import React from 'react';
import { X, AlertCircle, BookOpen, Clock } from 'lucide-react';
import '../styles/CourseDetailPopup.css';

const CourseDetailPopup = ({ course, onClose }) => {
  if (!course) return null;

  return (
    <div className="course-detail-overlay">
      <div className="course-detail-popup">
        <div className="course-detail-header">
          <h3 className="course-detail-title">{course.courseCode}</h3>
          <button 
            className="course-detail-close-btn"
            onClick={onClose}
          >
            <X size={18} />
          </button>
        </div>

        <div className="course-detail-body">
          {course.name && (
            <div className="course-detail-section">
              <h4 className="course-detail-section-title">Course Name</h4>
              <p className="course-detail-text">{course.name}</p>
            </div>
          )}

          {course.description && (
            <div className="course-detail-section">
              <h4 className="course-detail-section-title">Description</h4>
              <p className="course-detail-text">{course.description}</p>
            </div>
          )}

          {course.credits && (
            <div className="course-detail-info">
              <BookOpen size={16} />
              <span>{course.credits} {course.credits === 1 ? 'Credit' : 'Credits'}</span>
            </div>
          )}

          {course.prerequisites && course.prerequisites.length > 0 && (
            <div className="course-detail-section">
              <h4 className="course-detail-section-title">Prerequisites</h4>
              <ul className="course-detail-list">
                {Array.isArray(course.prerequisites) ? 
                  course.prerequisites.map((prereq, index) => {
                    if (Array.isArray(prereq)) {
                      // This is a "one of" prerequisite group
                      return (
                        <li key={index} className="course-detail-list-item">
                          One of: {prereq.join(' or ')}
                        </li>
                      );
                    } else {
                      // This is a single course prerequisite
                      return (
                        <li key={index} className="course-detail-list-item">
                          {prereq}
                        </li>
                      );
                    }
                  }) : (
                    <li className="course-detail-list-item">{course.prerequisites}</li>
                  )
                }
              </ul>
            </div>
          )}

          {course.offerings && course.offerings.length > 0 && (
            <div className="course-detail-section">
              <h4 className="course-detail-section-title">Typically Offered</h4>
              <div className="course-detail-offerings">
                {course.offerings.map((offering, index) => (
                  <span key={index} className="course-detail-offering">
                    <Clock size={14} />
                    {offering}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="course-detail-note">
            <AlertCircle size={16} />
            <p>This is general information about the course. Always check with your academic advisor for the most up-to-date requirements.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CourseDetailPopup;