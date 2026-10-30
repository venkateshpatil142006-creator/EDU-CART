# EduCards 🎓

EduCards is a collaborative, AI-powered study assistant designed to help students and educators practice multiple-choice questions (MCQs), ingest syllabus materials for Retrieval-Augmented Generation (RAG), and receive adaptive AI explanations for incorrect answers.

---

## 🌟 Key Features

1. **MCQ Study Deck Generator:** Generate four-option questions on any topic using Google Gemini or choose from seeded subject decks.
2. **Syllabus RAG Ingestion:** Upload lecture notes, syllabi, or textbooks (PDF or TXT) to ground AI deck generation directly in your coursework.
3. **Interactive Practice Mode:** Practice MCQs with randomized options, server-recorded attempts, points, and streaks.
4. **Adaptive AI Explainer:** When you answer a question incorrectly, trigger the AI tutor to explain the concept tailored to your exact understanding level (ELI5, Beginner, Intermediate, or Advanced Expert).
5. **Learner Profiles and Leaderboard:** Track accuracy, points, streaks, completed decks, and topics to review.
6. **Learning Analytics:** Explore personal and aggregate trends, response times, activity, and question difficulty with generated charts.
7. **Session Overview:** Review strengths, weak areas, missed answers, hints used, and next steps after finishing a deck.
8. **Developer-style UI:** A dark, monospace practice experience with a persistent light-theme option, keyboard shortcuts, and a circular progress indicator.

---

## 🛠️ Tech Stack

- **Backend:** Python 3.10+, FastAPI, Pydantic v2, Uvicorn, Google GenAI SDK (`google-genai`), PyPDF
- **Frontend:** HTML5, CSS3, Vanilla JavaScript (ES6+)
- **Analytics:** pandas, NumPy, Matplotlib (Agg/non-interactive rendering)
- **Storage:** PostgreSQL when `DATABASE_URL` is configured; otherwise SQLite (`data/educards.sqlite3` by default), with imports from legacy JSON and optional one-time SQLite-to-PostgreSQL migration
- **Testing:** Pytest, HTTPX

---

## 📁 Project Structure

```text
ps_2_gfg/
├── backend/
│   ├── analytics.py      # Aggregated analytics and chart generation
│   ├── ai_service.py      # Gemini AI client & prompt engineering
│   ├── main.py            # FastAPI application & API endpoints
│   ├── models.py          # Pydantic data models (Deck, Card, Material)
│   ├── rag.py             # PDF/Text extraction & RAG chunking
│   ├── seed.py            # Idempotent subject deck seeding
│   ├── storage.py         # SQLite storage, legacy import, scoring
│   ├── requirements.txt   # Backend Python dependencies
│   └── test_*.py          # Unit and integration test suite
├── data/
│   └── decks.json         # Legacy deck import source
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
| `DATABASE_URL` | No | PostgreSQL connection URL. When set, PostgreSQL is used instead of SQLite. |
| `POSTGRES_URL` | No | Alias used when `DATABASE_URL` is not set. |
| `EDUCART_DB_PATH` | No | SQLite file path; defaults to `data/educards.sqlite3` locally and `/tmp/educards.sqlite3` on Vercel/Lambda. Also used as the default SQLite source for PostgreSQL migration. |
| `EDUCART_SQLITE_MIGRATION_PATH` | No | Explicit SQLite database file to copy into PostgreSQL once. |

To configure keys, copy `.env.example` to `.env` and fill in your keys. `run.sh` and `run.bat` load `.env` when present. Never commit `.env` or share your API keys. You can run and present the project without either key.

### Data storage

Application data uses PostgreSQL when `DATABASE_URL` (or `POSTGRES_URL`) is set; otherwise it is stored in SQLite. Set `EDUCART_DB_PATH` to choose another SQLite file. When PostgreSQL is selected, startup copies any existing SQLite database at `EDUCART_SQLITE_MIGRATION_PATH` (or `EDUCART_DB_PATH`, or the default local database path) once; existing PostgreSQL rows are preserved on conflicts. Set a PostgreSQL connection URL before launching the app to use the hosted database.

On first startup, EduCards imports valid MCQs from the legacy `data/decks.json` file and materials from `data/materials.json`; legacy flashcards and invalid MCQs are discarded. The JSON files remain as import sources and are not used for ongoing writes. Run `python -m backend.seed` to safely seed the ten built-in subject decks.

Vercel's `/tmp` directory is ephemeral and is wiped on cold starts. SQLite data stored at `/tmp/educards.sqlite3` will not persist across cold starts; configure a hosted PostgreSQL database for persistent users, scores, decks, or materials.

During practice, press **1–4** to select an option and **Enter** to move on after answering. Use the header control to switch between dark and light themes; the preference is saved in localStorage. The dark theme is the default.

Learners choose a username on first visit. The browser stores only the generated user ID in localStorage; there are no passwords. Usernames are unique without regard to capitalization.

The analytics module uses pandas for accuracy, hint-use, activity, and ranking aggregations; NumPy for response-time percentiles, weak-card flags, and learning-trend fitting; and Matplotlib's Agg backend for PNG chart rendering. Personal and global analytics responses are cached in memory for approximately 60 seconds. Global analytics exposes grouped metrics only, not learner answers or attempt records.

Correct answers earn 10 points plus a speed bonus of up to 5 points (full at 5 seconds or faster, declining linearly to 0 at 20 seconds), less 2 points per hint used. Five consecutive correct answers in one session activate a 1.5× multiplier. A repeat correct answer for the same card on the same UTC day is capped at 1 point; wrong answers earn 0.

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
- `POST /api/decks/generate` — Generate an MCQ-only deck using Gen AI & RAG
- `POST /api/decks/{id}/cards` — Add a validated four-option MCQ
- `GET /api/materials` — List uploaded RAG materials
- `POST /api/materials/upload` — Upload and index a PDF/TXT syllabus
- `GET /api/users` and `POST /api/users` — List or create username-only learner identities
- `POST /api/deck-sessions` — Start a practice session
- `POST /api/deck-sessions/{id}/finish` — Finish a session
- `POST /api/attempts` — Record an answer and calculate points server-side
- `GET /api/leaderboard?period=all|week&limit=10` — View ranked scores
- `GET /api/users/{id}/profile` — View learner statistics and recent sessions
- `GET /api/analytics/me/{user_id}` — Personal practice metrics and charts
- `GET /api/analytics/global` — Aggregate class-wide metrics and charts
- `POST /api/decks/{id}/overview` — Build and cache a validated end-of-session overview; request body: `{"session_id": "..."}`
- `POST /api/ai/explain` — Get adaptive AI explanation, conversational tutor turn, or staged hint ladder for incorrect answers.
  - Parameters: `question` (str), `user_answer` (str, optional), `correct_answer` (str), `understanding_level` (str, default `"Beginner"`), `hint_level` (int 1-4, default `4`), `learner_attempt` (str, optional), `history` (list of `{"role": "user"|"assistant", "content": "..."}` turns, optional).

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

The repository seeds ten subject decks (Python, pandas/NumPy, Linux, DBMS/SQL, Operating Systems, Networking, Data Structures and Algorithms, Git, Web/HTTP/REST, and Cybersecurity basics) with 15 validated MCQs each. If no `GEMINI_API_KEY` is configured, generation uses offline practice content; live AI responses require a valid API key. Mindmaps have an offline fallback and do not require a Groq key.

For a smooth demo: (1) start with `./run.sh`, (2) choose a username, (3) practice a seeded deck, (4) view the leaderboard and profile, (5) generate a deck grounded in an uploaded `.txt` or PDF study file, and (6) open a deck mindmap. Use `/docs` to demonstrate the API.

The generator now waits for the saved deck list to refresh before entering practice mode, preventing the new-deck practice race condition.


## Troubleshooting AI generation

- Start the app with `./run.sh`; this script loads `GEMINI_API_KEY` from the project `.env` file.
- After changing frontend code, hard-refresh the browser with `Ctrl+Shift+R`. Static assets use a versioned URL to avoid stale JavaScript.
- If Gemini returns invalid/empty MCQs or the API key is unavailable, deck generation falls back to built-in offline practice questions. This fallback is labelled as offline practice content; it is not live AI output.
- Keep `.env` private and never paste your API key into screenshots or chat.
