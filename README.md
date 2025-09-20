# Excel Interviewer AI

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![Gemini AI](https://img.shields.io/badge/Gemini-AI-orange.svg)](https://ai.google.dev/)

An AI-powered conversational interviewer that assesses Excel proficiency through structured technical interviews. Built as a proof-of-concept to demonstrate scalable, automated technical skill evaluation.

## 🎯 Problem Statement

Traditional Excel technical interviews are:
- **Time-intensive**: Senior analysts spend 2-3 hours per candidate
- **Inconsistent**: Different interviewers apply varying evaluation standards
- **Scalable bottleneck**: Manual process limits hiring velocity
- **Quality vs. speed trade-off**: Pressure compromises thorough assessment

## 🚀 Solution Overview

This AI-driven system conducts structured Excel interviews through natural conversation, evaluates responses in real-time using LLM-powered assessment, and generates comprehensive performance reports.

### Key Features

- **🤖 Conversational AI Interviewer**: Natural dialogue that adapts to candidate responses
- **📊 Intelligent Evaluation**: Structured rubric-based assessment with confidence scoring
- **🔄 Adaptive Difficulty**: Questions scale based on demonstrated proficiency
- **📈 Performance Analytics**: Detailed feedback reports with specific improvement recommendations
- **🔧 Modular Architecture**: Pluggable AI adapters supporting multiple LLM providers
- **💾 Local Persistence**: Complete transcript storage with metadata preservation

## 🏗️ Architecture

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit UI  │────│   Core Bridge   │────│   AI Adapter    │
│                 │    │  (Protocol)     │    │  (Gemini/Claude)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Session State  │    │   Data Models   │    │   Prompts       │
│  Management     │    │   (Pydantic)    │    │   & Evaluation  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Transcripts   │    │ Question Bank   │    │   Config        │
│   (JSONL)       │    │   (JSON)        │    │   & Logging     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Core Components

#### 🎨 User Interface (Streamlit)
- Clean, professional chat interface
- Real-time conversation display
- Session controls and transcript download
- Performance summary visualization

#### 🔌 AI Adapter System
- **Protocol-based design** for easy provider switching
- **Function calling** for structured question retrieval
- **Structured outputs** for consistent evaluation
- **Fallback mechanisms** for error handling

#### 📚 Question Bank Management
- **Curated questions** covering core Excel competencies
- **Dynamic generation** using LLM when bank is exhausted
- **Duplicate prevention** within interview sessions
- **Metadata tagging** by capability and difficulty

#### 💽 Storage Layer
- **JSONL transcripts** for efficient streaming writes
- **Session-based organization** with full metadata
- **Event logging** for analytics and debugging
- **Local persistence** for offline operation

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Frontend** | Streamlit | Web UI and session management |
| **AI Engine** | Google Gemini | Conversational AI and evaluation |
| **Backend** | Python 3.8+ | Core application logic |
| **Data Models** | Pydantic | Type-safe data structures |
| **Storage** | JSON/JSONL | Local data persistence |
| **Configuration** | Python-dotenv | Environment management |

### Design Decisions

- **Adapter Pattern**: Enables easy swapping between AI providers (Gemini, OpenAI, Claude)
- **Protocol-Based Architecture**: Ensures interface consistency across implementations
- **Local-First Storage**: Simplifies deployment and enables offline operation
- **Streaming Transcripts**: JSONL format for efficient append operations

## 📋 Prerequisites

- Python 3.8 or higher
- Google Gemini API key
- Virtual environment (recommended)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd ExcelInterviewerAI
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
MODEL=gemini-1.5-flash  # or gemini-1.5-pro
```

### 3. Run the Application

```bash
streamlit run main.py
```

The application will be available at `http://localhost:8501`

## 🎯 Usage

### Interview Flow

1. **Self-Assessment**: Candidates start by describing their Excel experience
2. **Question Selection**: AI chooses appropriate questions from the bank or generates new ones
3. **Conversational Assessment**: Natural dialogue with follow-up questions based on responses
4. **Real-time Evaluation**: LLM evaluates answers using structured rubrics
5. **Performance Summary**: Comprehensive feedback report at interview conclusion

### Question Categories

The system covers core Excel competencies:

- **📊 Formulas & Functions**: Cell references, array formulas, advanced functions
- **📈 Data Analysis**: Pivot tables, data cleaning, analysis tools
- **📉 Visualization**: Charts, conditional formatting, dashboards
- **⚡ Automation**: Macros, Power Query, data connections
- **🔧 Advanced Features**: Power Pivot, VBA concepts, external integrations

## 📊 Evaluation Framework

### Scoring Methodology

- **Defined Criteria**: Fixed criteria for each question
- **Confidence Assessment**: AI self-evaluation of assessment certainty
- **Follow-up Logic**: Clarifying questions when confidence is low
- **Bias Mitigation**: Standardized criteria reduce subjective variance

### Performance Report

Generated reports include:
- **Overall Proficiency Level**: Beginner → Expert classification based on the fixed criteria
- **Strength Analysis**: Areas of demonstrated competence
- **Improvement Areas**: Specific skills needing development
- **Technical Accuracy**: Detailed evaluation of responses
- **Communication Assessment**: Clarity and problem-solving approach

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | Required |
| `MODEL` | Gemini model version | `gemini-2.5-flash` |

### Question Bank

Located at `data/question_bank.json`, contains:
- Curated Excel interview questions
- Evaluation criteria for each question
- Capability and difficulty metadata
- Expansion through LLM generation

## 📁 Project Structure

```
ExcelInterviewerAI/
├── main.py                 # Streamlit application entry point
├── config.py              # Configuration and path management
├── core/                  # Core business logic
│   ├── bridge.py         # AI adapter protocol and loading
│   ├── models.py         # Pydantic data models
│   └── utils.py          # Utility functions
├── ai/                    # AI-specific components
│   ├── adapter.py        # Gemini AI adapter implementation
│   └── prompts.py        # LLM prompt templates
├── storage/               # Data persistence layer
│   ├── question_bank.py  # Question bank management
│   └── transcripts.py    # Transcript storage
├── data/                  # Static data files
│   └── question_bank.json # Question database
├── logs/                  # Application logs
├── transcripts/           # Interview transcripts
├── DESIGN_DOCUMENT.md     # Technical design document
└── README.md             # This file
```

## 🔍 Key Design Patterns

### Adapter Protocol
```python
class AIAdapter(Protocol):
    @property
    def name(self) -> str: ...
    def generate_reply(self, messages: List[Message], state: Optional[Dict]) -> AIResponseWrapped: ...
    def generate_performance_summary(self, messages: List[Message]) -> str: ...
```

### Structured Evaluation
```python
class Evaluation(BaseModel):
    question_id: str
    criteria_scores: Dict[str, int]  # 0-5 scale per criterion
    total_score: float
    confidence: float  # 0-1 scale
    feedback: str
```
