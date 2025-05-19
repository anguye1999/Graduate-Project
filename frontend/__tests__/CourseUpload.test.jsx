import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import CourseUpload from '../src/components/CourseUpload';

describe('CourseUpload component', () => {
  it('renders upload instructions and template link', () => {
    render(<CourseUpload onCancel={() => {}} onFileProcessed={() => {}} />);
    expect(screen.getByText(/Upload your course history as a CSV or text file/i)).toBeInTheDocument();
    expect(screen.getByText(/Download a template/i)).toBeInTheDocument();
  });

  it('displays error for invalid file type', async () => {
    render(<CourseUpload onCancel={() => {}} onFileProcessed={() => {}} />);

    const fileInput = screen.getByTestId('file-input');

    const invalidFile = new File(['dummy content'], 'invalid.pdf', { type: 'application/pdf' });

    fireEvent.change(fileInput, { target: { files: [invalidFile] } });

    expect(await screen.findByText(/Please upload a CSV or text file/)).toBeInTheDocument();
  });
});