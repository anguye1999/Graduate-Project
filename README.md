# COSC 880 Graduate Project 

**Introduction**  
This project is a specialized course recommendation assistant initially targeting Towson University's Computer Science program. It helps students navigate their academic journey by providing personalized course recommendations based on their completed coursework, program requirements, and validating graduation progress.

# Team Members
- Andy Nguyen
- Anthony Gilis Jr.

---

## Table of Contents

1. Features 
2. Tech Stack
3. Prerequisites 
4. Installation 
5. Environment Variables
6. Usage  
7. Project Structure 
8. Built With 
9. Future Work
10. Contributing  
11. License 
12. Contact

---

## Features
  
- **Course History Upload**: Students can upload their completed courses through CSV or text files
- **Personalized Recommendations**: System suggests appropriate next courses based on prerequisites and program requirements
- **Prerequisite Validation**: Checks that students meet all requirements before recommending courses
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
   python app.py
   ```

2. In a separate terminal, start the React frontend:
   ```bash
   cd frontend
   npm run dev
   ```

3. Visit `http://localhost:5173`

4. Chat with chatbot about course recommendations

5. Download Degree Completion Plan Template 

6. Upload your Degree Completion Plan Text file

7. Explore:
   - Course Schedule for given semester
   - Upload degree plan for recommendation/validation about graduation/show degree status

## Project Structure

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

## Built With

- **Backend**:
  - [Flask](https://flask.palletsprojects.com/) - Web framework
  - [OpenAI](https://platform.openai.com) - Natural language processing

- **Frontend**:
  - [React](https://reactjs.org/) - UI framework

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

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.

## Contact

Andy Nguyen – nguyenandy155@gmail.com    
Project Link: [https://github.com/anguye1999/Graduate-Project](https://github.com/anguye1999/Graduate-Project)