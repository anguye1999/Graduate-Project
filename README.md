# COSC 880 Graduate Project 

**Introduction**  
Job seekers spend hours tweaking their resumes and hunting for openings. ResumeMatch uses AI to instantly analyze and optimize your resume, match you to top roles, and even draft custom cover letters—saving you time and boosting your chances of landing interviews.

# Team Members
- Andy Nguyen
- Anthony Gilis Jr.

---

## Table of Contents

1. Features 
2. Prerequisites 
3. Installation 
4. Environment Variables
5. Usage  
6. Project Structure 
7. Built With
8. Roadmap  
9. Contributing  
10. License 
11. Contact

---

## Features
  
- **Job Matching**: Real LinkedIn job data via RapidAPI
- **Match Scoring**: Percentage match between your resume and job descriptions
- **Cover Letter Generation**: Tailored cover letters based on your resume and job description
---

## Tech Stack
- Frontend: HTML, CSS, JavaScript, React.js
- Backend: Python Flask
- Model: OpenAI

## Prerequisites

- Python **3.8+**  
- Flask **16+** (for React frontend)
- An **OpenAI** account & API key  

---

## Installation

### Backend
```bash
# Clone
git clone https://github.com/anguye1999/Graduate-Project.git
cd Graduate-Project

# Setup venv
python -m venv venv
source venv/bin/activate    # macOS/Linux
venv\Scripts\activate       # Windows

# Install
pip install -r requirements.txt
```

### Frontend
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Build for production
npm run build
```

## Environment Variables

Create a `.env` file in the project root:

```ini
OPENAI_API_KEY=your_openai_api_key
ASSISTANT_ID =your_assistant_id
```

## Usage

### Development Mode
1. Start the backend server:
   ```bash
   python main.py
   ```

2. In a separate terminal, start the React frontend:
   ```bash
   cd frontend
   npm run dev
   ```

3. Visit `http://localhost:5173`

4. Chat with chatbot about course recommendations

4. Upload your Degree Completiong Plan Text file

5. Explore:
   - Course Schedule for given semester
   - Upload degree plan for recommendation/validation about graduation

## 📂 Project Structure

```
├── backend/
│   ├── main.py/            # Flask API routes
│   ├── validation.py/      # Validation functions
│   ├── course_sequence.py/  # Course Sequence functions
│   └── requirements.txt     # Python dependencies
├── frontend/               # React frontend application
│   ├── assets/             # Degree completion plan template for upload 
│   ├── public/             # Static assets
│   ├──src/                 # React components and logic
│   └── package.json        # Frontend dependencies
├── README.md
└── .env                    # Environment variables (not included in repository)
```

## 🔨 Built With

- **Backend**:
  - [Flask](https://flask.palletsprojects.com/) - Web framework
  - [OpenAI GPT](https://openai.com/) - Natural language processing

- **Frontend**:
  - [React](https://reactjs.org/) - UI framework
  - [React Router](https://reactrouter.com/) - Navigation

## Future Work

This application can be improved in several ways:

1. **PeopleSoft API Integration**: Replace with the official PeopleSoft API to gather available course information.

2. **Enhanced Course Retrieval Algorithm**: Implement more sophisticated course retrieval algorithms beyond OpenAI Assistant API and JSON files.

3. **User Authentication**: Add user authentication for Towson University students and better storing degree completion plan functionality.

## Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feature/name`
3. Commit: `git commit -m "Add feature"`
4. Push: `git push origin feature/name`
5. Open a PR — we'll review the changes!

## 📜 License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.

## Contact

Andy Nguyen – nguyenandy155@gmail.com    
Project Link: [https://github.com/anguye1999/Graduate-Project](https://github.com/anguye1999/Graduate-Project)