import os
import json
from typing import List, Dict, Any, Optional
from backend.models import Card, Deck
from backend.rag import retrieve_relevant_context

def generate_ai_deck(topic: str, card_type: str, count: int, materials: List[str]) -> Dict[str, Any]:
    api_key = os.environ.get("GEMINI_API_KEY")
    context = retrieve_relevant_context(topic, materials)
    
    # Try using Google GenAI SDK if key exists
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            prompt = f"""
            Generate a study deck about '{topic}' with {count} cards of type '{card_type}'.
            Here is reference study material/syllabus context:
            {context}
            
            Return ONLY a valid JSON object with this exact structure:
            {{
              "title": "Study Deck Title",
              "description": "Short description",
              "category": "General",
              "cards": [
                {{
                  "type": "flashcard" or "mcq",
                  "question": "Question text",
                  "answer": "Correct answer",
                  "options": ["Option A", "Option B", "Option C", "Option D"] (required only for mcq, else omit or null),
                  "explanation": "Detailed explanation of the correct answer"
                }}
              ]
            }}
            """
            response = client.models.generate_content(
                model="gemini-3.8-flash",
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
            valid_cards = [c for c in (raw_cards or []) if isinstance(c, dict) and str(c.get("question", "")).strip() and str(c.get("answer", "")).strip()]
            if not valid_cards:
                raise ValueError("Gemini response did not contain any valid question cards")
            data["cards"] = valid_cards[:max(1, min(count, 50))]
            return data
        except Exception as e:
            print(f"Gemini API generation failed, falling back to mock: {e}")

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
        selected = [
            (f"What is the central purpose of {topic}?", f"{topic} is studied to understand its core concepts, practical use, and limitations.", f"A good explanation of {topic} connects its definition to when and why it is used.", [f"Understand the core concepts of {topic}", "Ignore the problem being solved", "Avoid testing assumptions", "Use it without understanding it"]),
            (f"How would you explain {topic} to a beginner?", f"Start with its definition, explain the main components, then give a practical example of {topic}.", "A clear explanation moves from the basic idea to components and then a concrete example.", ["Definition, components, and practical example", "Only advanced jargon", "A list of unrelated facts", "No examples or context"]),
            (f"Why is it useful to learn {topic}?", f"It helps you reason about real problems where {topic} is applied.", "Understanding use cases and trade-offs makes it easier to apply a concept appropriately.", ["It helps solve relevant problems", "It removes the need to think", "It guarantees every solution is correct", "It makes testing unnecessary"]),
            (f"What is a good way to revise {topic}?", "Use active recall, practice questions, and spaced repetition.", "Retrieving information from memory and revisiting it over time improves retention.", ["Active recall and spaced repetition", "Read once and never revisit", "Memorize headings only", "Skip practice"]),
        ]

    cards = []
    for i in range(max(1, min(count, 50))):
        question, answer, explanation, options = selected[i % len(selected)]
        # For longer decks, vary the prompt while keeping the underlying answer accurate.
        if i >= len(selected):
            question = f"Review: {question}"
        kind = "mcq" if card_type == "mcq" or (card_type == "mixed" and i % 2 == 1) else "flashcard"
        cards.append({"type": kind, "question": question, "answer": answer,
                      "options": options if kind == "mcq" else None, "explanation": explanation})

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
    user_answer: str,
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
    return (
        f"At a {understanding_level} level: Your answer '{user_answer}' is not quite right. "
        f"The correct answer is '{correct_answer}'. "
        f"Here's why: EduCards AI notes that '{correct_answer}' satisfies all conditions of the question '{question}'."
    )

def generate_ai_explanation(
    question: str,
    user_answer: str,
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

    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
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
                attempt_line = f"\nLearner's Attempt: {learner_attempt.strip()}" if (learner_attempt and learner_attempt.strip()) else ""
                if hint_level == 4:
                    prompt = f"""
                The student answered a study question incorrectly.
                Question: {question}
                Student's Answer: {user_answer}{attempt_line}
                Correct Answer: {correct_answer}
                Target Understanding Level: {understanding_level} (e.g. ELI5 = Explain like I am 5, Beginner, Intermediate, Advanced)
                
                Provide a clear, encouraging explanation addressing:
                1. Why the student's answer ({user_answer}) is incorrect.
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
                model="gemini-3.8-flash",
                contents=prompt,
            )
            text = response.text.strip()
            if not is_conversational and 1 <= hint_level <= 3 and correct_answer and correct_answer.strip():
                if correct_answer.strip().lower() in text.lower():
                    text = _get_canned_explanation(question, user_answer, correct_answer, understanding_level, hint_level)
            return {
                "explanation": text,
                "is_full_explanation": is_full,
                "turn_count": round_count
            }
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

    return {
        "explanation": explanation,
        "is_full_explanation": is_full,
        "turn_count": round_count
    }

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
            from groq import Groq
            client = Groq(api_key=api_key)
            card_list_text = "\n".join(f"- {front}" for front in card_fronts) if card_fronts else "No specific cards provided."
            prompt = f"""
Generate a structured mindmap for the study deck '{deck_title}'.
Here are the key flashcard questions/concepts from the deck:
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
                and "nodes" in data
                and isinstance(data["nodes"], list)
                and "edges" in data
                and isinstance(data["edges"], list)
            ):
                valid_nodes = all(
                    isinstance(n, dict) and "id" in n and "label" in n for n in data["nodes"]
                )
                valid_edges = all(
                    isinstance(e, dict) and "from" in e and "to" in e for e in data["edges"]
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
            from google import genai
            client = genai.Client(api_key=api_key)
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
                model="gemini-3.8-flash",
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

