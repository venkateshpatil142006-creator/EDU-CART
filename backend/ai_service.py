import os
import json
from functools import lru_cache
import threading
from collections import Counter
from typing import List, Dict, Any, Optional
from backend.models import Card, Deck, DeckOverview, ExplainResponse
from backend.rag import retrieve_relevant_context
from pydantic import ValidationError


GEMINI_MODEL = "gemini-3.5-flash-lite"
AI_REQUEST_TIMEOUT_MS = 10_000
_explanation_cache: Dict[tuple[str, str, int], tuple[tuple, Dict[str, Any]]] = {}
_explanation_cache_lock = threading.Lock()


def _cache_explanation(key: tuple[str, str, int], context: tuple, result: Dict[str, Any]) -> None:
    with _explanation_cache_lock:
        _explanation_cache.pop(key, None)
        _explanation_cache[key] = (context, dict(result))
        while len(_explanation_cache) > 256:
            _explanation_cache.pop(next(iter(_explanation_cache)))


@lru_cache(maxsize=4)
def _gemini_client_for_key(api_key: str):
    from google import genai
    from google.genai import types

    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=AI_REQUEST_TIMEOUT_MS),
    )


@lru_cache(maxsize=4)
def _groq_client_for_key(api_key: str):
    from groq import Groq

    return Groq(api_key=api_key, timeout=AI_REQUEST_TIMEOUT_MS / 1000)


def _is_specific_question(question: str, topic: str) -> bool:
    normalized = " ".join(question.lower().split()).rstrip(" ?.")
    normalized_topic = " ".join(topic.lower().split())
    vague_prefixes = (
        "what is the central purpose of ",
        "what is the purpose of ",
        "what is the main purpose of ",
        "which statement best describes ",
    )
    if normalized.startswith(vague_prefixes):
        return False
    return normalized not in {
        f"what is {normalized_topic}",
        f"define {normalized_topic}",
        f"what does {normalized_topic} mean",
    }


def generate_ai_deck(topic: str, card_type: str, count: int, materials: List[str]) -> Dict[str, Any]:
    api_key = os.environ.get("GEMINI_API_KEY")
    context = retrieve_relevant_context(topic, materials)
    
    # Try using Google GenAI SDK if key exists
    if api_key:
        try:
            client = _gemini_client_for_key(api_key)
            prompt = f"""
            Create exactly {count} challenging, precise, non-repetitive multiple-choice questions
            about the specific subject "{topic}". Avoid generic questions such as asking for the
            subject's central purpose or broad definition. Every question must test a distinct,
            concrete fact, procedure, relationship, or application and include enough detail to
            have one unambiguous answer. Use plausible distractors and do not use trick wording.

            Use the following retrieved coursework excerpts as the primary source. When excerpts
            are present, ground each question in a specific detail from them; do not make a
            question answerable from only the topic name. Never invent syllabus facts. If the
            excerpts do not contain enough relevant detail, use established subject knowledge,
            but keep each question specific to "{topic}".
            Retrieved reference excerpts:
            {context}
            
            Return ONLY a valid JSON object with this exact structure:
            {{
              "title": "Study Deck Title",
              "description": "Short description",
              "category": "General",
              "cards": [
                {{
                  "question": "Question text",
                  "answer": "Exact copy of one of the four options",
                  "options": ["Option A", "Option B", "Option C", "Option D"],
                  "explanation": "Short explanation of the correct answer",
                  "difficulty": "easy, medium, or hard"
                }}
              ]
            }}
            Every card must have exactly four distinct, non-empty options. The answer must exactly
            match one option, including capitalization and punctuation. Do not generate flashcards.
            """
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            text = (response.text or "").strip()
            # Gemini may wrap JSON in markdown fences or include surrounding prose.
            if text.startswith("```"):
                text = text.split("\n", 1)[-1]
                if text.rstrip().endswith("```"):
                    text = text.rstrip()[:-3]
            start, end = text.find("{"), text.rfind("}")
            if start < 0 or end <= start:
                raise ValueError("Gemini returned no JSON object")
            data = json.loads(text[start:end + 1].strip())
            raw_cards = data.get("cards") if isinstance(data, dict) else None
            valid_cards = []
            for item in raw_cards or []:
                if not isinstance(item, dict):
                    continue
                try:
                    card = Card(
                        deck_id="",
                        type="mcq",
                        question=item.get("question", ""),
                        answer=item.get("answer", ""),
                        options=item.get("options"),
                        explanation=item.get("explanation"),
                        difficulty=item.get("difficulty", "medium"),
                    )
                except (ValidationError, TypeError):
                    continue
                if not _is_specific_question(card.question, topic):
                    continue
                valid_cards.append(card.model_dump())
            if not valid_cards:
                raise ValueError("Gemini response did not contain any valid question cards")
            data["cards"] = valid_cards[:max(1, min(count, 50))]
            return data
        except Exception as e:
            print(f"Gemini API generation failed: {e}")
            raise RuntimeError(
                "Gemini could not produce a valid, topic-specific MCQ deck. Try a more specific topic or review the API key."
            ) from e

    # Offline question bank: useful, deterministic questions when no AI key is configured.
    # These are deliberately labelled as offline practice content, not live AI output.
    topic_key = topic.lower().strip()
    banks = {
        "python": [
            ("What is the difference between a list and a tuple in Python?", "A list is mutable; a tuple is immutable.", "Lists can be changed after creation, while tuples cannot have their elements reassigned.", ["A list is mutable; a tuple is immutable.", "A tuple is always larger.", "Lists only store numbers.", "There is no difference."]),
            ("What does a Python dictionary store?", "Key-value pairs.", "A dictionary maps unique keys to values and is useful for looking up data by key.", ["Only ordered numbers", "Key-value pairs.", "Only strings", "Compiled machine code"]),
            ("What is the purpose of a function?", "To package reusable logic under a name.", "Functions reduce duplication and make programs easier to test and maintain.", ["To package reusable logic under a name.", "To permanently stop a program", "To create a database automatically", "To install packages"]),
            ("What does a Python virtual environment help isolate?", "Project-specific Python packages.", "A virtual environment keeps dependencies for one project separate from other projects.", ["Project-specific Python packages.", "The computer's hardware", "The internet connection", "Only image files"]),
            ("What is the purpose of a try/except block?", "To handle exceptions.", "It lets a program respond to expected runtime errors instead of crashing without a controlled response.", ["To handle exceptions.", "To repeat code forever", "To declare a class only", "To speed up every loop"]),
            ("What does list.append(x) do?", "Adds x to the end of a list.", "append modifies the existing list by adding one item at its end.", ["Adds x to the end of a list.", "Sorts the list", "Removes the first item", "Converts it to a tuple"]),
            ("What is a class in object-oriented Python?", "A blueprint for creating objects.", "A class defines attributes and methods that its instances can use.", ["A blueprint for creating objects.", "A loop condition", "A package manager", "A type of comment"]),
            ("What does `if __name__ == '__main__':` commonly indicate?", "Code intended to run when the file is executed directly.", "The condition is true when the module is run as the main program, not merely imported.", ["Code intended to run when the file is executed directly.", "The file is encrypted", "The code is always skipped", "The Python version is 2"]),
            ("Which data type represents True or False?", "bool", "The bool type has the two values True and False.", ["bool", "str", "float", "dict"]),
            ("What is a Python module?", "A Python file that can be imported.", "Modules help organize code and allow functions, classes, and variables to be reused.", ["A Python file that can be imported.", "A CPU core", "A database row", "A browser tab"]),
        ],
        "photosynthesis": [
            ("Which molecule supplies carbon atoms for sugar synthesis during photosynthesis?", "Carbon dioxide.", "The Calvin cycle fixes carbon from CO2 into organic molecules.", ["Carbon dioxide.", "Oxygen gas.", "Nitrogen gas.", "Water vapor."]),
            ("Which photosynthetic complex splits water and releases oxygen?", "Photosystem II.", "The oxygen-evolving complex associated with Photosystem II oxidizes water.", ["Photosystem II.", "Photosystem I.", "ATP synthase.", "RuBisCO."]),
            ("What is the main role of chlorophyll in a leaf?", "Absorb light energy for photosynthesis.", "Chlorophyll pigments absorb photons that drive photosynthetic electron transfer.", ["Absorb light energy for photosynthesis.", "Store genetic information.", "Convert glucose into amino acids.", "Transport water through xylem."]),
            ("Where does the Calvin cycle take place in a chloroplast?", "The stroma.", "The Calvin cycle enzymes are located in the chloroplast stroma.", ["The stroma.", "The thylakoid lumen.", "The outer membrane.", "The cytosol of a red blood cell."]),
            ("What directly powers carbon fixation reactions in the Calvin cycle?", "ATP and NADPH from the light reactions.", "Light reactions provide ATP energy and NADPH reducing power for carbon fixation.", ["ATP and NADPH from the light reactions.", "Oxygen and starch.", "DNA and RNA.", "Sucrose and carbon monoxide."]),
            ("What is the primary function of the electron transport chain in the light reactions?", "Build a proton gradient used to make ATP.", "Electron transfer contributes to proton movement into the thylakoid lumen.", ["Build a proton gradient used to make ATP.", "Directly assemble glucose in the thylakoid lumen.", "Break down RuBisCO into amino acids.", "Move carbon dioxide into the nucleus."]),
            ("Which enzyme fixes carbon dioxide to RuBP in the Calvin cycle?", "RuBisCO.", "RuBisCO catalyzes the addition of CO2 to ribulose-1,5-bisphosphate.", ["RuBisCO.", "ATP synthase.", "DNA polymerase.", "Catalase."]),
            ("What is the immediate three-carbon product formed after carbon fixation and reduction?", "G3P.", "The Calvin cycle produces glyceraldehyde-3-phosphate, which can be used to build sugars.", ["G3P.", "Oxygen.", "Acetyl-CoA.", "Lactic acid."]),
        ],
        "linux": [
            ("Which command prints the current working directory?", "pwd", "pwd displays the absolute path of the current directory.", ["pwd", "cd", "mkdir", "touch"]),
            ("What does `ls -la` show?", "Directory entries including hidden files and detailed metadata.", "-a includes hidden entries and -l uses a long listing format.", ["Only running processes", "Hidden files and detailed listing", "Disk partitions only", "Network routes"]),
            ("What does chmod change?", "File or directory permissions.", "chmod adjusts read, write, and execute permissions.", ["File permissions", "File contents", "The hostname", "The kernel version"]),
            ("Which command is commonly used to inspect running processes?", "ps", "ps reports process information; top/htop provide an updating view.", ["ps", "mkdir", "grep", "cat"]),
            ("What is the role of systemd on many Linux distributions?", "System and service manager.", "systemd starts and manages services and other system units.", ["System and service manager", "A text editor", "A programming language", "A package format"]),
            ("What does `grep` do?", "Searches text for matching patterns.", "grep filters input or files for lines matching a pattern.", ["Searches text patterns", "Changes file permissions", "Creates users", "Mounts disks"]),
            ("What does sudo commonly allow?", "Running a command with another user's privileges, often root.", "sudo delegates privileged commands according to system policy.", ["Privileged command execution", "Compressing files only", "Changing screen resolution", "Starting a browser"]),
            ("Where are many system-wide configuration files stored?", "/etc", "/etc contains configuration files for the system and many installed services.", ["/etc", "/proc", "/dev/null", "/tmp/only"]),
        ],
        "network": [
            ("What is the main purpose of DNS?", "Translate domain names into IP addresses and related records.", "DNS lets clients locate services using human-readable domain names.", ["Translate domain names to IP records", "Encrypt every file", "Assign CPU time", "Store web page styles"]),
            ("What does HTTP status code 404 mean?", "The requested resource was not found.", "A server returns 404 when it cannot find the requested resource.", ["Resource not found", "Request succeeded", "Server permanently moved", "Authentication succeeded"]),
            ("What is the role of TCP?", "Reliable, ordered byte-stream delivery between endpoints.", "TCP uses acknowledgements and retransmissions to provide reliable ordered delivery.", ["Reliable ordered delivery", "Domain name lookup", "Image compression", "Disk scheduling"]),
            ("What is an IP address used for?", "Identifying an interface on an IP network.", "IP addressing allows packets to be routed toward network interfaces.", ["Identifying a network interface", "Naming Python variables", "Encrypting passwords by itself", "Formatting disks"]),
            ("What does HTTPS add to HTTP?", "TLS-protected communication and server authentication.", "HTTPS uses TLS to protect data in transit and authenticate the server certificate.", ["TLS protection", "Guaranteed zero latency", "Automatic backups", "Unlimited bandwidth"]),
            ("What does a router do?", "Forwards packets between networks.", "Routers use routing information to choose where to forward IP packets.", ["Forwards packets between networks", "Compiles source code", "Stores passwords", "Renders HTML"]),
        ],
        "dbms": [
            ("What is a primary key?", "A column or set of columns that uniquely identifies each row.", "Primary-key values must be unique and cannot be NULL.", ["A unique row identifier", "A duplicate row marker", "A type of index that permits duplicates only", "A database backup"]),
            ("What does SQL SELECT do?", "Retrieves rows and columns from a database.", "SELECT queries data from one or more tables or other queryable sources.", ["Retrieves data", "Deletes a database", "Creates a user account only", "Encrypts the server"]),
            ("What is a foreign key?", "A constraint linking values to a key in another or the same table.", "Foreign keys help enforce referential integrity between related records.", ["A referential integrity constraint", "A password", "A backup file", "A duplicate primary key"]),
            ("Why normalize a relational database?", "To reduce unnecessary duplication and update anomalies.", "Normalization organizes data into related tables with dependencies represented appropriately.", ["Reduce redundancy and anomalies", "Make every query slower", "Remove all relationships", "Store only images"]),
            ("What does an INNER JOIN return?", "Rows with matching join values in both inputs.", "An inner join keeps records for which the join condition matches on both sides.", ["Matching rows from both inputs", "Every row from the left regardless of match", "Only NULL values", "Only table definitions"]),
        ],
        "operating system": [
            ("What is a process?", "A program in execution with its own process state and resources.", "An operating system manages processes and their execution resources.", ["A program in execution", "A file extension", "A network cable", "A database table"]),
            ("What is virtual memory used for?", "Giving processes a virtual address space mapped to physical memory and storage as needed.", "Virtual memory provides isolation and flexible memory management; it does not make storage as fast as RAM.", ["Virtual address spaces and memory management", "Replacing the CPU", "Encrypting all files", "DNS caching"]),
            ("What is a context switch?", "The OS switches the CPU from one thread or process to another.", "The system saves and restores execution state when changing the running task.", ["Switching the running task", "Formatting RAM", "Changing a file name", "Resolving a domain"]),
            ("What is deadlock?", "A set of tasks are stuck waiting for resources held by one another.", "Deadlock can occur when conditions such as circular wait and hold-and-wait are present.", ["Tasks stuck waiting on each other", "A successful program exit", "A faster scheduling algorithm", "A file permission"]),
        ],
    }
    selected = next((items for key, items in banks.items() if key in topic_key or (key == "network" and "tcp/ip" in topic_key)), None)
    if not selected:
        raise RuntimeError(
            f"No curated offline questions are available for {topic!r}. Configure GEMINI_API_KEY or choose a seeded subject deck."
        )

    cards = []
    for i in range(max(1, min(count, 50))):
        question, answer, explanation, options = selected[i % len(selected)]
        if i >= len(selected):
            question = f"Review: {question}"
        choices = list(dict.fromkeys(options))
        if answer not in choices:
            choices = [answer, *choices[:3]]
        if len(choices) != 4:
            choices = [answer, *[f"Incorrect alternative {n}" for n in range(1, 4)]]
        cards.append({
            "type": "mcq",
            "question": question,
            "answer": answer,
            "options": choices,
            "explanation": explanation,
            "difficulty": ("easy", "medium", "hard")[i % 3],
        })

    return {
        "title": f"{topic.strip().title()} — Practice Deck",
        "description": f"Offline practice deck for {topic}. Add a Gemini API key for live AI-generated content.",
        "category": "Offline Practice",
        "cards": cards
    }

HINT_INSTRUCTIONS = {
    1: "Ask ONE guiding question that points the learner toward the idea; give no answer, no explanation, no definition of the answer.",
    2: "Give a short conceptual hint naming the underlying concept or rule, without stating the answer.",
    3: "Show only the first partial step of the working or reasoning, and stop before the conclusion.",
    4: "Provide a clear, encouraging explanation addressing:\n1. Why the student's answer ({user_answer}) is incorrect.\n2. What the correct answer ({correct_answer}) is and why.\n3. Explained tailored precisely to the '{understanding_level}' level.",
}

def _get_canned_explanation(
    question: str,
    user_answer: Optional[str],
    correct_answer: str,
    understanding_level: str,
    hint_level: int = 4
) -> str:
    if hint_level == 1:
        return f"At a {understanding_level} level: Consider '{question}'. What key concept or mechanism plays the primary role here?"
    elif hint_level == 2:
        return f"At a {understanding_level} level: Focus on the foundational concepts behind '{question}'. Recall the core rule or definition."
    elif hint_level == 3:
        return f"At a {understanding_level} level: Step 1: Break down '{question}' into its components and eliminate what doesn't fit."
    if user_answer:
        return (
            f"At a {understanding_level} level: Your answer '{user_answer}' is not quite right. "
            f"The correct answer is '{correct_answer}'. "
            f"Here's why: '{correct_answer}' satisfies the conditions in '{question}'."
        )
    return (
        f"At a {understanding_level} level: The correct answer is '{correct_answer}'. "
        f"It satisfies the conditions in '{question}'."
    )

def generate_ai_explanation(
    question: str,
    user_answer: Optional[str],
    correct_answer: str,
    understanding_level: str,
    hint_level: int = 4,
    learner_attempt: Optional[str] = None,
    history: Optional[List[Any]] = None
) -> Dict[str, Any]:
    is_conversational = (history is not None)
    user_turns = []
    if is_conversational:
        for turn in history:
            role = turn.role if hasattr(turn, 'role') else (turn.get('role') if isinstance(turn, dict) else None)
            content = turn.content if hasattr(turn, 'content') else (turn.get('content') if isinstance(turn, dict) else None)
            if role == "user":
                user_turns.append(content)
        round_count = len(user_turns)
        is_full = (round_count >= 3)
    else:
        round_count = 0
        is_full = (hint_level == 4)

    cache_key = (question, understanding_level, hint_level)
    cache_context = (
        user_answer or "",
        correct_answer,
        learner_attempt or "",
        json.dumps(
            [
                (
                    turn.role if hasattr(turn, "role") else turn.get("role"),
                    turn.content if hasattr(turn, "content") else turn.get("content"),
                )
                for turn in (history or [])
            ],
            ensure_ascii=False,
        ),
    )
    with _explanation_cache_lock:
        cached = _explanation_cache.get(cache_key)
        if cached and cached[0] == cache_context:
            return dict(cached[1])

    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            client = _gemini_client_for_key(api_key)
            if is_conversational:
                formatted_history = "\n".join([
                    f"{t.role if hasattr(t, 'role') else t.get('role')}: {t.content if hasattr(t, 'content') else t.get('content')}"
                    for t in history[-4:]
                ])
                if is_full:
                    prompt_instruction = f"""
                    Round limit reached ({round_count} rounds completed).
                    Do NOT ask any further questions.
                    Provide the full, complete explanation of why '{user_answer}' is incorrect and why '{correct_answer}' is the correct answer.
                    """
                else:
                    prompt_instruction = f"""
                    Current round: {round_count + 1} of 3.
                    Ask AT MOST ONE short question back to the learner checking their understanding before giving the final answer.
                    Do not give away the final correct answer yet.
                    """
                prompt = f"""
                The student is working on a study question with an interactive tutor.
                Question: {question}
                Student Initial Answer: {user_answer}
                Correct Answer: {correct_answer}
                Target Level: {understanding_level}
                
                Conversation History:
                {formatted_history}
                
                Instruction:
                {prompt_instruction}
                """
            else:
                user_answer = user_answer or ""
                attempt_line = f"\nLearner's Attempt: {learner_attempt.strip()}" if (learner_attempt and learner_attempt.strip()) else ""
                if hint_level == 4:
                    prompt = f"""
                Explain the following study question at the requested level.
                Question: {question}
                Student's Answer (if any): {user_answer or "Not provided"}{attempt_line}
                Correct Answer: {correct_answer}
                Target Understanding Level: {understanding_level} (e.g. ELI5 = Explain like I am 5, Beginner, Intermediate, Advanced)
                
                Provide a clear, encouraging explanation addressing:
                1. If a student's answer is provided, why it is incorrect.
                2. What the correct answer ({correct_answer}) is and why.
                3. Explained tailored precisely to the '{understanding_level}' level.
                """
                else:
                    instruction = HINT_INSTRUCTIONS.get(hint_level, "")
                    prompt = f"""
                The student answered a study question incorrectly.
                Question: {question}
                Student's Answer: {user_answer}{attempt_line}
                Correct Answer: {correct_answer}
                Target Understanding Level: {understanding_level} (e.g. ELI5 = Explain like I am 5, Beginner, Intermediate, Advanced)
                
                Instruction: {instruction}
                Never reveal, state, or paraphrase the correct answer.
                Explain tailored precisely to the '{understanding_level}' level.
                """
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            text = response.text.strip()
            if not is_conversational and 1 <= hint_level <= 3 and correct_answer and correct_answer.strip():
                if correct_answer.strip().lower() in text.lower():
                    text = _get_canned_explanation(question, user_answer, correct_answer, understanding_level, hint_level)
            result = {
                "explanation": text,
                "is_full_explanation": is_full,
                "turn_count": round_count
            }
            result = ExplainResponse.model_validate(result).model_dump()
            _cache_explanation(cache_key, cache_context, result)
            return dict(result)
        except Exception as e:
            print(f"Gemini explain API failed, using fallback: {e}")

    # Fallback explanation
    if is_conversational:
        if is_full:
            explanation = (
                f"At a {understanding_level} level: After 3 guided rounds, here is the full explanation: "
                f"Your initial answer '{user_answer}' was incorrect. The correct answer is '{correct_answer}'. "
                f"EduCards AI notes that '{correct_answer}' satisfies all conditions of '{question}'."
            )
        elif round_count == 0:
            explanation = (
                f"Hint & Question 1 of 3: Consider the core mechanism of '{question}'. "
                f"What do you think is the initial factor that takes place?"
            )
        elif round_count == 1:
            last_reply = user_turns[-1] if user_turns else ""
            explanation = (
                f"Hint & Question 2 of 3: Regarding your thought '{last_reply}', "
                f"which specific principle distinguishes that from other possibilities?"
            )
        else: # round_count == 2
            last_reply = user_turns[-1] if user_turns else ""
            explanation = (
                f"Hint & Question 3 of 3: Good progress on '{last_reply}'. "
                f"How does that connect directly to the final result?"
            )
    else:
        explanation = _get_canned_explanation(question, user_answer, correct_answer, understanding_level, hint_level)

    result = {
        "explanation": explanation,
        "is_full_explanation": is_full,
        "turn_count": round_count
    }
    return ExplainResponse.model_validate(result).model_dump()


def build_deck_overview(data: Dict[str, Any]) -> Dict[str, Any]:
    attempts = data["attempts"]
    total = len(attempts)
    correct = sum(bool(attempt["is_correct"]) for attempt in attempts)
    wrong_attempts = [attempt for attempt in attempts if not attempt["is_correct"]]
    mistake_counts: Dict[str, int] = {}
    subject_counts: Dict[str, Dict[str, int]] = {}
    for attempt in attempts:
        subject = attempt["subject"]
        stats = subject_counts.setdefault(subject, {"attempts": 0, "correct": 0})
        stats["attempts"] += 1
        stats["correct"] += int(bool(attempt["is_correct"]))
        if not attempt["is_correct"]:
            mistake_counts[subject] = mistake_counts.get(subject, 0) + 1

    strengths = [
        f"{subject}: {stats['correct']}/{stats['attempts']} correct"
        for subject, stats in sorted(
            subject_counts.items(),
            key=lambda item: (
                -(item[1]["correct"] / item[1]["attempts"]),
                -item[1]["attempts"],
                item[0],
            ),
        )[:3]
        if stats["correct"]
    ]
    weak_areas = [
        f"{subject}: {mistakes} missed answer{'s' if mistakes != 1 else ''}"
        for subject, mistakes in sorted(
            mistake_counts.items(), key=lambda item: (-item[1], item[0])
        )[:5]
    ]
    mistake_review = [
        {
            "question": attempt["question"],
            "your_answer": attempt["selected"],
            "correct_answer": attempt["correct_answer"],
            "why_you_may_have_erred": (
                "Your selected option may have seemed plausible, but it did not match the concept tested."
            ),
            "tip": attempt.get("explanation") or "Review the key concept and compare it with each option.",
        }
        for attempt in wrong_attempts[:100]
    ]
    slowest = sorted(attempts, key=lambda attempt: attempt["time_taken_ms"], reverse=True)[:3]
    hints_used = sum(attempt["hints_used"] for attempt in attempts)
    summary = (
        f"You answered {correct} of {total} recorded answers correctly "
        f"({round(correct / total * 100, 1) if total else 0}% accuracy) and earned "
        f"{data['session']['total_points']} points. You used {hints_used} hints. "
        f"{len(wrong_attempts)} answers need review. The slowest question was "
        f"'{slowest[0]['question']}' at {(slowest[0]['time_taken_ms'] / 1000):.1f} seconds."
        if slowest else
        f"You completed {total} recorded answers with {correct} correct and earned "
        f"{data['session']['total_points']} points. You used {hints_used} hints."
    )
    overview = {
        "summary": summary,
        "strengths": strengths or ["Keep practicing to build a clear strength area."],
        "weak_areas": weak_areas or ["No repeated weak topic was identified."],
        "mistake_review": mistake_review,
        "next_steps": [
            "Review the explanation for each missed question.",
            "Revisit the topic with the most missed answers before your next practice session.",
        ] if wrong_attempts else [
            "Try a harder deck to keep strengthening your understanding.",
            "Return later and review these concepts to reinforce retention.",
        ],
    }
    return DeckOverview.model_validate(overview).model_dump()


def _validate_overview_mistakes(overview: DeckOverview, attempts: List[Dict[str, Any]]) -> bool:
    wrong_attempts = [item for item in attempts if not item["is_correct"]][:100]
    wrong_keys = Counter(
        (item["question"], item["selected"], item["correct_answer"])
        for item in wrong_attempts
    )
    review_keys = Counter(
        (item["question"], item["your_answer"], item["correct_answer"])
        for item in overview.mistake_review
    )
    return review_keys == wrong_keys


def generate_deck_overview(data: Dict[str, Any]) -> Dict[str, Any]:
    fallback = build_deck_overview(data)
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return fallback
    try:
        client = _gemini_client_for_key(api_key)
        wrong_attempts = [
            {
                "question": item["question"],
                "your_answer": item["selected"],
                "correct_answer": item["correct_answer"],
                "topic": item["subject"],
                "explanation": item.get("explanation"),
            }
            for item in data["attempts"]
            if not item["is_correct"]
        ]
        topics_with_mistakes = sorted(
            {
                topic: sum(1 for item in data["attempts"] if not item["is_correct"] and item["subject"] == topic)
                for topic in {item["subject"] for item in data["attempts"]}
            }.items(),
            key=lambda item: (-item[1], item[0]),
        )
        slowest = sorted(
            data["attempts"], key=lambda item: item["time_taken_ms"], reverse=True
        )[:3]
        context = {
            "wrong_answers": wrong_attempts[:100],
            "topics_with_most_mistakes": topics_with_mistakes,
            "hints_used": sum(item["hints_used"] for item in data["attempts"]),
            "slowest_questions": [
                {
                    "question": item["question"],
                    "seconds": round(item["time_taken_ms"] / 1000, 1),
                    "correct": bool(item["is_correct"]),
                }
                for item in slowest
            ],
            "deterministic_summary": fallback["summary"],
        }
        prompt = f"""
Write a concise, supportive study-session overview based only on this JSON data:
{json.dumps(context, ensure_ascii=False)}

Return ONLY a JSON object with exactly these fields and types:
{{
  "summary": "string",
  "strengths": ["string"],
  "weak_areas": ["string"],
  "mistake_review": [
    {{
      "question": "exact question from wrong_answers",
      "your_answer": "exact your_answer from wrong_answers",
      "correct_answer": "exact correct_answer from wrong_answers",
      "why_you_may_have_erred": "short, nonjudgmental explanation",
      "tip": "actionable study tip grounded in the supplied explanation"
    }}
  ],
  "next_steps": ["string"]
}}
Every mistake_review entry must correspond exactly to a supplied wrong answer. Do not invent
questions, answers, topics, scores, or learner behavior. Keep the output practical and concise.
"""
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        text = (response.text or "").strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.rstrip().endswith("```"):
                text = text.rstrip()[:-3]
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Gemini returned no overview JSON object")
        overview = DeckOverview.model_validate_json(text[start:end + 1])
        if not _validate_overview_mistakes(overview, data["attempts"]):
            raise ValueError("Gemini overview included an answer not present in the session")
        return overview.model_dump()
    except Exception as error:
        print(f"Gemini overview failed validation or generation; using deterministic overview: {error}")
        return fallback

def generate_mindmap(deck: Any) -> Dict[str, Any]:
    deck_title = getattr(deck, "title", None) or (deck.get("title") if isinstance(deck, dict) else "Study Deck")
    cards = getattr(deck, "cards", None) or (deck.get("cards") if isinstance(deck, dict) else [])

    card_fronts = []
    for c in cards:
        if hasattr(c, "question") and c.question:
            card_fronts.append(c.question)
        elif isinstance(c, dict) and c.get("question"):
            card_fronts.append(c["question"])

    def _fallback_mindmap() -> Dict[str, Any]:
        root = deck_title or "Study Deck"
        nodes = []
        edges = []
        if card_fronts:
            for i, front in enumerate(card_fronts, 1):
                nid = f"n{i}"
                nodes.append({"id": nid, "label": front})
                edges.append({"from": "root", "to": nid})
        else:
            nodes.append({"id": "n1", "label": "Key Concepts"})
            edges.append({"from": "root", "to": "n1"})
        return {
            "root": root,
            "nodes": nodes,
            "edges": edges
        }

    api_key = os.environ.get("GROQ_API_KEY")
    if api_key:
        try:
            client = _groq_client_for_key(api_key)
            card_list_text = "\n".join(f"- {front}" for front in card_fronts) if card_fronts else "No specific cards provided."
            prompt = f"""
Generate a structured mindmap for the study deck '{deck_title}'.
Here are the key MCQ questions/concepts from the deck:
{card_list_text}

Return ONLY a valid JSON object with this exact schema:
{{
  "root": "<topic>",
  "nodes": [
    {{"id": "n1", "label": "..."}}
  ],
  "edges": [
    {{"from": "n1", "to": "n2"}}
  ]
}}
"""
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"},
            )
            raw_text = chat_completion.choices[0].message.content or ""
            text = raw_text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            data = json.loads(text.strip())

            if (
                isinstance(data, dict)
                and "root" in data
                and isinstance(data["root"], str)
                and data["root"].strip()
                and "nodes" in data
                and isinstance(data["nodes"], list)
                and len(data["nodes"]) <= 100
                and "edges" in data
                and isinstance(data["edges"], list)
                and len(data["edges"]) <= 200
            ):
                valid_nodes = all(
                    isinstance(n, dict)
                    and isinstance(n.get("id"), str)
                    and n["id"].strip()
                    and isinstance(n.get("label"), str)
                    and n["label"].strip()
                    and len(n["label"]) <= 500
                    for n in data["nodes"]
                )
                node_ids = {node["id"] for node in data["nodes"] if isinstance(node, dict) and isinstance(node.get("id"), str)}
                valid_nodes = valid_nodes and len(node_ids) == len(data["nodes"])
                valid_edges = all(
                    isinstance(e, dict)
                    and isinstance(e.get("from"), str)
                    and isinstance(e.get("to"), str)
                    and e["from"] in node_ids | {"root"}
                    and e["to"] in node_ids | {"root"}
                    for e in data["edges"]
                )
                if valid_nodes and valid_edges:
                    return data
            print("Groq mindmap output failed validation, falling back to mock")
        except Exception as e:
            print(f"Groq API mindmap generation failed, falling back to mock: {e}")

    return _fallback_mindmap()

def generate_ai_feedback(concept: str, correct_answer: str, learner_restatement: str) -> Dict[str, Any]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            client = _gemini_client_for_key(api_key)
            prompt = f"""
            The student was taught the following concept and attempted to explain it back in their own words.
            Concept: {concept}
            Correct Answer / Core Principle: {correct_answer}
            Student's Restatement: {learner_restatement}
            
            Provide constructive feedback in 3 sentences or fewer:
            1. Clearly state what part of the concept the student accurately understood.
            2. State one specific detail or misconception they should refine.
            IMPORTANT: Do not provide a model answer first. Directly address the student's restatement.
            """
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            text = response.text.strip()
            return {
                "feedback": text,
                "what_was_right": "Your restatement shows understanding of the core concept.",
                "thing_to_refine": "Review how this principle connects to the final outcome."
            }
        except Exception as e:
            print(f"Gemini feedback API failed, using fallback: {e}")

    # Fallback critique
    return {
        "feedback": (
            f"You correctly grasped the foundational principle of {concept}. "
            f"To refine your understanding further, make sure to consider how '{correct_answer}' fully answers all conditions. "
            f"Great job putting this into your own words!"
        ),
        "what_was_right": f"You accurately described the core premise of {concept}.",
        "thing_to_refine": f"Double check the connection between your explanation and '{correct_answer}'."
    }
