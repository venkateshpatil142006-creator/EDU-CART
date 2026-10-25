# Contributing to EduCards 🎓

Thank you for your interest in contributing to EduCards! We welcome contributions from the community, whether it's bug fixes, new features, documentation improvements, or feedback.

Please follow these guidelines to make your contribution experience smooth and effective.

---

## 🚀 Getting Started

1. **Fork the Repository** and clone your fork locally:
   ```bash
   git clone https://github.com/your-username/educards.git
   cd educards
   ```

2. **Create a Feature Branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Set Up the Development Environment**:
   - Install Python 3.10+
   - Install backend dependencies:
     ```bash
     pip install -r backend/requirements.txt
     ```

---

## 🏃 Running the Application & Tests

- **Run the Backend Server**:
  ```bash
  python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
  ```
- **Run the Test Suite**:
  ```bash
  python -m pytest backend/ -v
  ```
  *Ensure all tests pass successfully before submitting your changes.*

---

## 📝 Pull Request Process

1. **Write or Update Tests**: If you are fixing a bug or adding a new feature, include corresponding tests in `backend/test_*.py`.
2. **Commit Changes**: Use clear, descriptive commit messages (e.g., `feat: add flashcard export feature` or `fix: handle empty PDF upload gracefully`).
3. **Push to Your Fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
4. **Open a Pull Request**: Submit your pull request to the main repository with a clear description of the problem solved or feature added.

---

## 🛡️ Code of Conduct

Please be respectful, collaborative, and constructive in all interactions. EduCards is an inclusive space for all learners and developers.
