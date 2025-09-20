# Excel Interviewer AI

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![Gemini AI](https://img.shields.io/badge/Gemini-AI-orange.svg)](https://ai.google.dev/)

An AI-powered conversational interviewer that assesses Excel proficiency through structured technical interviews. Built as a proof-of-concept to demonstrate scalable, automated technical skill evaluation.

## Problem Statement

Traditional Excel technical interviews are:
- **Time-intensive**: Senior analysts spend 2-3 hours per candidate
- **Inconsistent**: Different interviewers apply varying evaluation standards
- **Scalable bottleneck**: Manual process limits hiring velocity
- **Quality vs. speed trade-off**: Pressure compromises thorough assessment

## Solution Overview

This AI-driven system conducts structured Excel interviews through natural conversation, evaluates responses in real-time using LLM-powered assessment, and generates comprehensive performance reports.

## Core Interview Loop

The interview process follows a structured, adaptive flow:

1. **Self-Assessment**: Interviewee provides initial self-assessment of their Excel proficiency level
2. **Question Selection**: Agent fetches appropriate questions from the question bank based on target difficulty and capability to test
3. **Adaptive Response Handling**:
   - Based on interviewee response quality, agent either asks follow-up questions or selects new questions with adjusted difficulty/capability levels
4. **Dynamic Question Generation**: When no suitable questions exist in the bank, agent generates new questions matching the intended difficulty and style
5. **Comprehensive Evaluation**: Agent analyzes all responses to create a detailed performance report with strengths, areas for improvement, and proficiency assessment

## Example LLM Loop
2025-09-20 23:29:51,101 | LLM CALL<br>
2025-09-20 23:29:53,148 | TOOL: get_next_question<br>
2025-09-20 23:29:53,149 | QUESTION RETRIEVED<br>
2025-09-20 23:30:32,079 | LLM CALL<br>
2025-09-20 23:30:58,123 | LLM CALL<br>
2025-09-20 23:31:01,734 | TOOL: get_next_question<br>
2025-09-20 23:31:01,734 | QUESTION RETRIEVED<br>
2025-09-20 23:31:13,965 | LLM CALL<br>
2025-09-20 23:31:29,968 | LLM CALL<br>
2025-09-20 23:31:33,010 | TOOL: generate_question<br>
2025-09-20 23:31:33,010 | LLM CALL<br>
2025-09-20 23:31:33,010 | TOOL: generate_performance_summary<br>
2025-09-20 23:31:33,010 | LLM CALL<br>

### Key Features

- **Conversational AI Interviewer**: Natural dialogue that adapts to candidate responses
- **Intelligent Evaluation**: Conversational assessment with adaptive questioning
- **Adaptive Difficulty**: Questions scale based on demonstrated proficiency
- **Performance Analytics**: Detailed feedback reports with specific improvement recommendations
- **Modular Architecture**: Pluggable AI agents supporting multiple LLM providers
- **Local Persistence**: Complete transcript storage with metadata preservation

## Architecture

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit UI  │────│   Core Bridge   │────│   AI Agent      │
│                 │    │  (Protocol)     │    │  (Gemini)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Session State  │    │   Data Models   │    │   Prompts       │
│  Management     │    │   (Pydantic)    │    │   & Assessment  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Transcripts   │    │ Question Bank   │    │   Config        │
│   (JSONL)       │    │   (JSON)        │    │   & Logging     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Core Components

#### User Interface (Streamlit)
- Clean, professional chat interface
- Real-time conversation display
- Session controls and transcript download
- Performance summary visualization

#### AI Agent System
- **Protocol-based design** for easy provider switching
- **Function calling** for structured question retrieval
- **Conversational responses** with natural dialogue flow
- **Fallback mechanisms** for error handling

#### Question Bank Management
- **Curated questions** covering core Excel competencies
- **Dynamic generation** using LLM when bank is exhausted
- **Duplicate prevention** within interview sessions
- **Metadata tagging** by capability and difficulty

#### Storage Layer
- **JSONL transcripts** for efficient streaming writes
- **Session-based organization** with full metadata
- **Event logging** for analytics and debugging
- **Local persistence** for offline operation

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Frontend** | Streamlit | Web UI and session management |
| **AI Engine** | Google Gemini | Conversational AI and evaluation |
| **Backend** | Python 3.8+ | Core application logic |
| **Data Models** | Pydantic | Type-safe data structures |
| **Storage** | JSON/JSONL | Local data persistence |
| **Configuration** | Python-dotenv | Environment management |

### Design Decisions

- **Agent Pattern**: Enables easy swapping between AI providers (Gemini, OpenAI, Claude)
- **Protocol-Based Architecture**: Ensures interface consistency across implementations
- **Local-First Storage**: Simplifies deployment and enables offline operation
- **Streaming Transcripts**: JSONL format for efficient append operations

## Prerequisites

- Python 3.8 or higher
- Google Gemini API key
- Virtual environment (recommended)

## Quick Start

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

## Usage

### Question Categories

The system covers core Excel competencies:

- **Formulas & Functions**: Cell references, array formulas, advanced functions
- **Data Analysis**: Pivot tables, data cleaning, analysis tools
- **Visualization**: Charts, conditional formatting, dashboards
- **Automation**: Macros, Power Query, data connections
- **Advanced Features**: Power Pivot, VBA concepts, external integrations

## Evaluation Framework

### Evaluation Approach

The AI agent evaluates responses conversationally throughout the interview, adapting questions based on demonstrated proficiency. The final performance summary provides comprehensive feedback on technical accuracy, problem-solving approach, and Excel competency level.

### Performance Report

Generated reports include:
- **Overall Proficiency Level**: Beginner → Expert classification based on demonstrated skills
- **Strength Analysis**: Areas of demonstrated competence
- **Improvement Areas**: Specific skills needing development
- **Technical Accuracy**: Detailed evaluation of responses
- **Communication Assessment**: Clarity and problem-solving approach

## Configuration

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

## Project Structure

```
ExcelInterviewerAI/
├── main.py                 # Streamlit application entry point
├── config.py              # Configuration and path management
├── core/                  # Core business logic
│   ├── bridge.py         # AI agent protocol and loading
│   ├── models.py         # Pydantic data models
│   └── utils.py          # Utility functions
├── ai/                    # AI-specific components
│   ├── agent.py          # Gemini AI agent implementation
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

## Key Design Patterns

### Agent Protocol
```python
class AIAgent(Protocol):
    @property
    def name(self) -> str: ...
    def generate_reply(self, messages: List[Message], state: Optional[Dict]) -> AIResponseWrapped: ...
    def generate_performance_summary(self, messages: List[Message]) -> str: ...
```

### Performance Summary Generation
The agent generates a comprehensive performance summary at the end of the interview, analyzing all responses to provide detailed feedback on the candidate's Excel proficiency.
