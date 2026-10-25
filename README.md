# EduCards 🎓

EduCards is a collaborative, AI-powered study assistant designed to help students and educators generate interactive flashcards and multiple-choice questions (MCQs), ingest syllabus materials for Retrieval-Augmented Generation (RAG), practice interactively, and receive adaptive AI explanations for incorrect answers.

---

## 🌟 Key Features

1. **Gen AI Study Deck Generator:** Automatically generate high-quality flashcard and MCQ decks on any topic using Google Gemini.
2. **Syllabus RAG Ingestion:** Upload lecture notes, syllabi, or textbooks (PDF or TXT) to ground AI deck generation directly in your coursework.
3. **Interactive Practice Mode:** Practice decks with interactive flashcard flipping and MCQ quiz mode with instant validation.
4. **Adaptive AI Explainer:** When you answer a question incorrectly, trigger the AI tutor to explain the concept tailored to your exact understanding level (ELI5, Beginner, Intermediate, or Advanced Expert).
5. **Clean, Modern UI:** Built with Vanilla HTML5, CSS3 (solid colors, CSS variables, zero-gradient minimal aesthetic), and Vanilla JavaScript.

---

## 🛠️ Tech Stack

- **Backend:** Python 3.10+, FastAPI, Pydantic v2, Uvicorn, Google GenAI SDK (`google-genai`), PyPDF
- **Frontend:** HTML5, CSS3, Vanilla JavaScript (ES6+)
- **Storage:** Local JSON persistence (`data/decks.json`)
- **Testing:** Pytest, HTTPX

---

## 📁 Project Structure

```text
ps_2_gfg/
├── backend/
│   ├── ai_service.py      # Gemini AI client & prompt engineering
│   ├── main.py            # FastAPI application & API endpoints
│   ├── models.py          # Pydantic data models (Deck, Card, Material)
│   ├── rag.py             # PDF/Text extraction & RAG chunking
│   ├── storage.py         # JSON storage persistence helper
│   ├── requirements.txt   # Backend Python dependencies
│   └── test_*.py          # Unit and integration test suite
├── data/
│   └── decks.json         # Local JSON store for study decks
├── frontend/
│   ├── index.html         # Single-page application shell & modals
│   ├── style.css          # Solid color design system & UI styles
│   └── app.js             # Frontend router, state, and API client
└── README.md
```

---

## 🚀 Getting Started (Local)

### Requirements

- Python 3.10 or newer
- Internet access for the first dependency installation
- API keys are **optional**. Without them, the app uses built-in mock responses so you can demonstrate the project locally.

### Option A — easiest on Linux/macOS

From the project root directory:

```bash
chmod +x run.sh
./run.sh
```

The script creates a `.venv` virtual environment, installs dependencies, and starts the server. The first run may take a few minutes. Keep this terminal open while using the app.

### Option B — Windows

Double-click `run.bat`, or run it from Command Prompt in the project folder:

```bat
run.bat
```

### Option C — manual setup

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Windows Command Prompt:

```bat
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Open **http://127.0.0.1:8000**. API documentation is available at **http://127.0.0.1:8000/docs** and the health check is **http://127.0.0.1:8000/api/health**.

### Environment variables (optional)

| Variable | Required? | Used for |
|---|---|---|
| `GEMINI_API_KEY` | No | Real AI deck generation, explanations, and feedback. Without it, mock/fallback responses are used. |
| `GROQ_API_KEY` | No | Real AI mindmap generation. Without it, a mock mindmap is returned. |

To configure keys, copy `.env.example` to `.env` and fill in your keys. `run.sh` and `run.bat` load `.env` when present. Never commit `.env` or share your API keys. You can run and present the project without either key.

### Data storage

Decks are stored in `data/decks.json`; uploaded study materials are stored in `data/materials.json`. These files are created automatically when needed. Keep a backup if you create data you want to preserve.

### Running tests

Activate the virtual environment, then run:

```bash
python -m pytest backend/ -v
```

Tests that mock the Gemini or Groq SDK require the dependencies from `backend/requirements.txt` to be installed first.

---

## 🔌 API Endpoints

- `GET /api/health` — Health check
- `GET /api/decks` — List all study decks
- `POST /api/decks` — Create a new study deck
- `GET /api/decks/{id}` — Get deck details
- `POST /api/decks/generate` — Generate study deck using Gen AI & RAG
- `GET /api/materials` — List uploaded RAG materials
- `POST /api/materials/upload` — Upload and index a PDF/TXT syllabus
- `POST /api/ai/explain` — Get adaptive AI explanation, conversational tutor turn, or staged hint ladder for incorrect answers.
  - Parameters: `question` (str), `user_answer` (str), `correct_answer` (str), `understanding_level` (str, default `"Beginner"`), `hint_level` (int 1-4, default `4`), `learner_attempt` (str, optional), `history` (list of `{"role": "user"|"assistant", "content": "..."}` turns, optional).

  | hint_level | Content |
  |---|---|
  | 1 | A guiding question, no answer |
  | 2 | A conceptual hint |
  | 3 | A partial worked step |
  | 4 | The full explanation (default) |

  Example request:
  ```json
  {
    "question": "What is the powerhouse of the cell?",
    "user_answer": "Nucleus",
    "correct_answer": "Mitochondria",
    "understanding_level": "Beginner",
    "hint_level": 1,
    "learner_attempt": "Nucleus"
  }
  ```
- `POST /api/decks/{id}/mindmap` — Generate mindmap for study deck using Gen AI
- `POST /api/ai/feedback` — Submit a learner's conceptual restatement and receive targeted AI critique (3 sentences or fewer) detailing what was accurate and what to refine.
  - Parameters: `concept` (str), `correct_answer` (str), `learner_restatement` (str).


---

## 📄 License

MIT License

## Presentation demo (offline mode)

The repository includes three sample decks (Python, Linux, and Networking) so the interface is populated on first launch. The generator also has an offline question bank for Python, Linux, networking, DBMS, and operating-system topics. If no `GEMINI_API_KEY` is configured, generation uses this offline content; live AI responses require a valid API key. Mindmaps have an offline fallback and do not require a Groq key.

For a smooth demo: (1) start with `./run.sh`, (2) open `http://127.0.0.1:8000`, (3) open a sample deck and practice cards, (4) generate a 10-card Python/Linux/DBMS deck, (5) upload a `.txt` or PDF study file and generate another deck, and (6) open a deck mindmap. Use `/docs` to demonstrate the API.

The generator now waits for the saved deck list to refresh before entering practice mode, preventing the new-deck practice race condition.


## Troubleshooting AI generation and empty decks

- Start the app with `./run.sh`; this script loads `GEMINI_API_KEY` from the project `.env` file.
- After changing frontend code, hard-refresh the browser with `Ctrl+Shift+R`. Static assets use a versioned URL to avoid stale JavaScript.
- If Gemini returns invalid/empty JSON or the API key is unavailable, deck generation falls back to built-in offline question banks for Python, Linux, networking, DBMS, and operating systems. This fallback is labelled as offline practice content; it is not live AI output.
- Empty legacy decks are automatically repaired with built-in practice cards when `/api/decks` is loaded.
- Keep `.env` private and never paste your API key into screenshots or chat.
