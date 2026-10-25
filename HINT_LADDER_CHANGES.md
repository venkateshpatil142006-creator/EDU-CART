# Hint Ladder Feature Changes (#5)

This feature implements GitHub issue #5 by adding a staged 4-level hint ladder to `POST /api/ai/explain`. Previously, any wrong answer immediately generated the complete explanation including the final answer. With the hint ladder, learners can progressively reveal assistance—starting with a guiding question (level 1), followed by a conceptual hint (level 2), a partial step (level 3), and finally the full explanation (level 4)—allowing self-correction before revealing the answer.

---

## Per-File Changes

### `backend/models.py`
- Added `hint_level: int = Field(default=4, ge=1, le=4)` to `ExplainRequest`: Specifies which stage of hint assistance to return (1 to 4), defaulting to 4 to preserve backwards compatibility. Values outside 1-4 are rejected with validation error 422.
- Added `learner_attempt: Optional[str] = None` to `ExplainRequest`: An optional field accepting the learner's incorrect answer or typed attempt to tailor hint responses.

### `backend/main.py`
- Updated the `explain_answer` route handler (`POST /api/ai/explain`) to forward `hint_level=req.hint_level` and `learner_attempt=req.learner_attempt` into `generate_ai_explanation`.

### `backend/ai_service.py`
- Added `HINT_INSTRUCTIONS`: A dictionary mapping hint levels 1 through 4 to specific prompt guidance:
  - Level 1: Ask ONE guiding question pointing toward the idea; give no answer or explanation.
  - Level 2: Give a short conceptual hint naming the underlying rule or concept, without stating the answer.
  - Level 3: Show only the first partial step of working or reasoning, stopping before the conclusion.
  - Level 4: Provide the full explanation addressing why the attempt is wrong and why the correct answer is right.
- Updated `generate_ai_explanation`:
  - Accepts `hint_level: int = 4` and `learner_attempt: Optional[str] = None`.
  - Prompts for levels 1-3 explicitly instruct the model: "Never reveal, state, or paraphrase the correct answer."
  - When `learner_attempt` is supplied, it is included in the prompt; omitted when empty.
  - Level 4 retains the original prompt structure and behavior.
  - Added leak guard (defense-in-depth): If the model's output at levels 1-3 contains the correct answer text (case-insensitive), it falls back to the canned hint for that level.
- Added `_get_canned_explanation`: Provides deterministic fallback text for all 4 hint levels when `GEMINI_API_KEY` is not configured or if an error occurs. Canned text for levels 1-3 never contains the correct answer text. Level 4 returns the exact existing fallback explanation.

### Frontend Files (`frontend/index.html`, `frontend/style.css`, `frontend/app.js`)
- `frontend/index.html`:
  - Added `#hint-btn` ("Give me a hint" button) above the explanation panel in the explainer modal.
  - Updated `#explainer-text` container to host staged hints.
- `frontend/style.css`:
  - Added `.hint-item` CSS class defining clean border separation and margins between consecutive hints using existing CSS variables (`--border`, `--accent`).
- `frontend/app.js`:
  - Added `hintLevel` (starts at 0) and `displayedHints` state variables.
  - Added `resetHintState()`: Resets `hintLevel` to 0, clears displayed hints, and updates the hint button.
  - Added `updateHintButton()`: Controls button text and visibility. Labeled "Give me a hint" for levels 0-2 (fetching levels 1-3), "Show full explanation" for level 3 (fetching level 4), and hidden/disabled once level 4 is shown.
  - Added `renderHints()`: Displays each fetched hint sequentially inside the explainer panel.
  - Added `requestNextHint()`: Increments `hintLevel`, issues a POST request to `/api/ai/explain` with the new level and `learner_attempt`, appends the returned hint, and updates the button.
  - Updated `fetchAiExplanation()`: Refetches the active hint level when the understanding level dropdown changes.
  - Updated `startPractice()`, `nextCard()`, `prevCard()`, and `openExplainerModal()` to reset the hint ladder state and displayed hints whenever a question or session changes.

### `backend/test_explain.py`
- Added comprehensive unit and integration tests:
  - `test_ai_explain_default_hint_level`: Validates that omitted `hint_level` defaults to full explanation (level 4).
  - `test_ai_explain_levels_no_correct_answer`: Parametrized test verifying that levels 1, 2, and 3 never leak the correct answer text.
  - `test_ai_explain_level_4_full_explanation`: Verifies that level 4 includes the correct answer and explanation.
  - `test_ai_explain_invalid_hint_level`: Verifies that hint levels 0 and 5 return status 422.
  - `test_ai_explain_with_learner_attempt`: Confirms that `learner_attempt` is accepted and processed successfully.
  - `test_ai_explain_leak_guard`: Verifies that if an AI response leaks the answer text at levels 1-3, the leak guard falls back to the canned hint.

### `README.md`
- Documented `hint_level` and `learner_attempt` parameters, hint level definitions table, and example request body under the `POST /api/ai/explain` entry in the API Endpoints section.

---

## Request & Response Examples

### Level 1: Guiding Question
Request:
```json
{
  "question": "What is the powerhouse of the cell?",
  "user_answer": "Nucleus",
  "correct_answer": "Mitochondria",
  "understanding_level": "Beginner",
  "hint_level": 1
}
```
Response:
```json
{
  "explanation": "At a Beginner level: Consider 'What is the powerhouse of the cell?'. What key concept or mechanism plays the primary role here?"
}
```

### Level 2: Conceptual Hint
Request:
```json
{
  "question": "What is the powerhouse of the cell?",
  "user_answer": "Nucleus",
  "correct_answer": "Mitochondria",
  "understanding_level": "Beginner",
  "hint_level": 2,
  "learner_attempt": "Nucleus"
}
```
Response:
```json
{
  "explanation": "At a Beginner level: Focus on the foundational concepts behind 'What is the powerhouse of the cell?'. Recall the core rule or definition."
}
```

### Level 3: Partial Step
Request:
```json
{
  "question": "What is the powerhouse of the cell?",
  "user_answer": "Nucleus",
  "correct_answer": "Mitochondria",
  "understanding_level": "Beginner",
  "hint_level": 3
}
```
Response:
```json
{
  "explanation": "At a Beginner level: Step 1: Break down 'What is the powerhouse of the cell?' into its components and eliminate what doesn't fit."
}
```

### Level 4: Full Explanation
Request:
```json
{
  "question": "What is the powerhouse of the cell?",
  "user_answer": "Nucleus",
  "correct_answer": "Mitochondria",
  "understanding_level": "Beginner",
  "hint_level": 4
}
```
Response:
```json
{
  "explanation": "At a Beginner level: Your answer 'Nucleus' is not quite right. The correct answer is 'Mitochondria'. Here's why: EduCards AI notes that 'Mitochondria' satisfies all conditions of the question 'What is powerhouse of the cell?'."
}
```

---

## Backward Compatibility

- Existing API clients that do not pass `hint_level` will automatically use default `hint_level = 4`.
- The response format `{"explanation": "..."}` remains unchanged.
- The canned fallback for level 4 produces the exact string generated prior to this change.

---

## Verification

### Running Automated Tests
```bash
python -m pytest backend/ -v
```
All 19 tests pass successfully with no external network or API key required.

### Manual Verification
1. Start the server without `GEMINI_API_KEY`:
   ```bash
   python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```
2. Test via `curl`:
   ```bash
   curl -s -X POST http://127.0.0.1:8000/api/ai/explain \
     -H "Content-Type: application/json" \
     -d '{"question":"What is DNA?","user_answer":"Protein","correct_answer":"Deoxyribonucleic acid","hint_level":1}'
   ```
3. Test in UI:
   - Open `http://127.0.0.1:8000` in the browser.
   - Start practice on a deck and select a wrong option for an MCQ.
   - Click "Give me a hint" through levels 1, 2, and 3. Notice the button label switches to "Show full explanation" at level 3.
   - Click "Show full explanation" to view level 4; the button is hidden once full explanation is rendered.
   - Move to the next card or restart practice and verify hint state is cleanly reset.
