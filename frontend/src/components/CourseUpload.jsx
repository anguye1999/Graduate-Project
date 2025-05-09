import React, { useState } from 'react';
import { Upload, X, FileText, Check, AlertCircle } from 'lucide-react';
import '../styles/CourseUpload.css';
import DegreeCompletionPlanTextTemplate from "../assets/files/DegreeCompletionPlanTextTemplate.txt"
import { useProgress } from './ProgressContext';

const CourseUpload = ({ onFileProcessed, onCancel }) => {
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [processingStatus, setProcessingStatus] = useState('');

  // Safely use the context
  let refreshProgress = () => console.log("Progress refresh not available");
  try {
    const context = useProgress();
    refreshProgress = context ? context.refreshProgress : refreshProgress;
  } catch (err) {
    console.log("Progress context not available:", err);
  }

  // Get the session ID from parent component or sessionStorage
  const sessionId = sessionStorage.getItem('chatSessionId') || '';

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (selectedFile) => {
    // Reset previous states
    setUploadError(null);

    // Check file extension
    const fileName = selectedFile.name.toLowerCase();
    const validExtensions = ['csv', 'txt']; // Removed Excel extensions
    const fileExt = fileName.split('.').pop();

    if (!validExtensions.includes(fileExt)) {
      setUploadError('Please upload a CSV or text file (.csv, .txt)');
      return;
    }

    // Check file size (5MB max)
    if (selectedFile.size > 5 * 1024 * 1024) {
      setUploadError('File size exceeds 5MB limit');
      return;
    }

    setFile(selectedFile);
  };

  const DownloadTextTemplate = () => {
    const link = document.createElement('a');
    link.href = DegreeCompletionPlanTextTemplate;
    link.download = 'DegreeCompletionPlanTextTemplate.txt';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  const uploadFile = async () => {
    if (!file) return;

    setIsUploading(true);
    setUploadError(null);
    setProcessingStatus('Uploading file...');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', sessionId);

    try {
      // First update status
      setProcessingStatus('Analyzing course data...');

      const response = await fetch('http://localhost:5000/api/upload-courses', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || 'Error uploading file');
      }

      setProcessingStatus('Processing complete!');
      setUploadSuccess(true);

      if (data.success) {
        setUploadSuccess(true);

        // Trigger progress refresh
        refreshProgress();

        // Pass the processed courses to parent component
        if (onFileProcessed) {
          setTimeout(() => {
            onFileProcessed(data);
          }, 1000);
        }
      }
    } catch (error) {
      console.error('Upload error:', error);
      setUploadError(error.message || 'Failed to upload file');
      setProcessingStatus('');
    } finally {
      setIsUploading(false);
    }
  };

  // Function to get a message for the selected file type
  const getFileTypeMessage = () => {
    if (!file) return null;

    const fileName = file.name.toLowerCase();
    const fileExt = fileName.split('.').pop();

    switch (fileExt) {
      case 'csv':
        return "CSV file detected. I'll extract course information from tabular data.";
      case 'txt':
        return "Text file detected. I'll search for course codes and information.";
      default:
        return null;
    }
  };

  return (
    <div className="course-upload">
      <div className="course-upload-header">
        <h3>Upload Course History</h3>
        <button className="course-upload-close-btn" onClick={onCancel}>
          <X size={18} />
        </button>
      </div>

      {!uploadSuccess ? (
        <>
          <div className="course-upload-instructions">
            <p>Upload your course history as a CSV or text file to get personalized course recommendations.</p>
            <a href={DegreeCompletionPlanTextTemplate} download="DegreeCompletionPlanTextTemplate.txt" className="course-download-link">
              Download a template for formatting your degree completion plan
            </a>
            <p className="course-upload-file-types">Supported formats: .csv, .txt</p>
          </div>

          <div
            className={`course-upload-area ${isDragging ? 'dragging' : ''} ${uploadError ? 'error' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => document.getElementById('courseFileInput').click()}
          >
            <input
              type="file"
              id="courseFileInput"
              accept=".csv,.txt"
              onChange={handleFileInput}
              style={{ display: 'none' }}
            />

            {!file ? (
              <>
                <Upload className="course-upload-icon" size={36} />
                <p>Drag and drop your file here, or click to browse</p>
              </>
            ) : (
              <div className="course-selected-file">
                <div className="course-file-header">
                  <FileText size={24} />
                  <span className="course-file-name">{file.name}</span>
                  <span className="course-file-size">({(file.size / 1024).toFixed(1)} KB)</span>
                </div>
                {getFileTypeMessage() && (
                  <p className="course-file-type-message">{getFileTypeMessage()}</p>
                )}
              </div>
            )}
          </div>

          {uploadError && (
            <div className="course-upload-error">
              <AlertCircle size={16} />
              <p>{uploadError}</p>
            </div>
          )}

          {isUploading && processingStatus && (
            <div className="course-upload-processing">
              <div className="processing-spinner"></div>
              <p>{processingStatus}</p>
            </div>
          )}

          <div className="course-upload-actions">
            <button
              className="course-cancel-btn"
              onClick={onCancel}
              disabled={isUploading}
            >
              Cancel
            </button>
            <button
              className={`course-upload-btn ${(!file || isUploading) ? 'disabled' : ''}`}
              disabled={!file || isUploading}
              onClick={uploadFile}
            >
              {isUploading ? 'Processing...' : 'Upload'}
            </button>
          </div>
        </>
      ) : (
        <div className="course-upload-success">
          <div className="course-success-icon">
            <Check size={32} />
          </div>
          <h3>File Uploaded Successfully!</h3>
          <p>Your course history has been processed.</p>
        </div>
      )}
    </div>
  );
};

export default CourseUpload;