let currentDecks = [];
let currentMaterials = [];
let currentDeck = null;
let currentCardIndex = 0;
let currentWrongContext = null;
let hintLevel = 0;
let displayedHints = [];
let currentUser = null;
let currentSessionId = null;
let currentQuestionStartedAt = 0;
let currentQuestionHintsUsed = 0;
let currentSessionPoints = 0;
let currentStreak = 0;
let completedCardIds = new Set();
let answeredCardIds = new Set();
let wrongCardIds = new Set();
let sessionFinished = false;
let reviewMode = false;
let practiceStartedAt = 0;
let activeAnalyticsView = "me";
let currentAnswerWasWrong = false;
let practiceAdvanceTimer = null;
let activeTheme = "dark";

document.addEventListener("DOMContentLoaded", () => {
  activeTheme = localStorage.getItem("educards_theme") === "light" ? "light" : "dark";
  applyTheme(activeTheme, false);
  document.getElementById("theme-toggle").addEventListener("click", toggleTheme);
  document.addEventListener("keydown", handlePracticeShortcut);
  document.getElementById("learn-more-ai").addEventListener("click", openExplainerModal);
  document.getElementById("review-mistakes").addEventListener("click", reviewMistakes);
  document.getElementById("analytics-tab-me").addEventListener("click", () => showAnalytics("me"));
  document.getElementById("analytics-tab-global").addEventListener("click", () => showAnalytics("global"));
  document.getElementById("decks-grid").addEventListener("click", handleDeckAction);
  document.getElementById("dashboard-decks-grid").addEventListener("click", handleDeckAction);
  initializeUser();
});

function applyTheme(theme, refreshAnalytics = true) {
  activeTheme = theme === "light" ? "light" : "dark";
  document.body.dataset.theme = activeTheme;
  const toggle = document.getElementById("theme-toggle");
  if (toggle) {
    const nextTheme = activeTheme === "dark" ? "light" : "dark";
    toggle.textContent = `${nextTheme === "light" ? "Light" : "Dark"} mode`;
    toggle.setAttribute("aria-label", `Switch to ${nextTheme} theme`);
  }
  if (refreshAnalytics && document.getElementById("view-analytics").classList.contains("active")) {
    loadAnalytics(activeAnalyticsView);
  }
}

function toggleTheme() {
  const nextTheme = activeTheme === "dark" ? "light" : "dark";
  localStorage.setItem("educards_theme", nextTheme);
  applyTheme(nextTheme);
}

function handlePracticeShortcut(event) {
  if (!document.getElementById("view-practice").classList.contains("active") ||
      document.getElementById("practice-results").hidden === false ||
      document.querySelector(".modal.active") ||
      event.target.closest("input, textarea, select, [contenteditable='true']")) return;
  if (/^[1-4]$/.test(event.key)) {
    const option = document.querySelectorAll("#mcq-options .mcq-option")[Number(event.key) - 1];
    if (option && !option.disabled) {
      event.preventDefault();
      option.click();
    }
    return;
  }
  if (event.key === "Enter") {
    const options = [...document.querySelectorAll("#mcq-options .mcq-option")];
    if (options.length && options.every(option => option.disabled)) {
      event.preventDefault();
      nextCard();
    }
  }
}

async function initializeUser() {
  const savedUserId = localStorage.getItem("educard_user_id");
  if (savedUserId) {
    try {
      const response = await fetch(`/api/users/${encodeURIComponent(savedUserId)}`);
      if (response.ok) {
        currentUser = await response.json();
      } else {
        localStorage.removeItem("educard_user_id");
      }
    } catch (error) {
      console.error("Could not restore learner identity", error);
    }
  }
  if (currentUser) {
    updateUserLabel();
  } else {
    document.getElementById("identity-modal").classList.add("active");
  }
  await Promise.all([loadDecks(), loadMaterials()]);
}

function updateProgressRing() {
  const ring = document.getElementById("practice-progress-ring");
  const label = document.getElementById("progress-ring-label");
  if (!ring || !currentDeck) return;
  const total = reviewMode ? getPracticeCards().length : currentDeck.cards.length;
  const completed = reviewMode ? currentCardIndex : answeredCardIds.size;
  const percentage = total ? Math.min(100, Math.round((completed / total) * 100)) : 0;
  const progressCircle = ring.querySelector(".progress-ring-value");
  if (progressCircle) progressCircle.style.strokeDashoffset = String(213.63 * (1 - percentage / 100));
  ring.setAttribute("aria-valuenow", String(percentage));
  if (label) label.textContent = `${percentage}%`;
}

function updateUserLabel() {
  const label = document.getElementById("current-user-label");
  if (label && currentUser) label.textContent = currentUser.username;
}

async function registerUser(event) {
  event.preventDefault();
  const input = document.getElementById("username-input");
  const error = document.getElementById("identity-error");
  const username = input.value.trim();
  error.textContent = "";
  try {
    const response = await fetch("/api/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username })
    });
    const data = await response.json();
    if (!response.ok) {
      error.textContent = data.detail || "Could not create your profile.";
      return;
    }
    currentUser = data;
    localStorage.setItem("educard_user_id", currentUser.id);
    document.getElementById("identity-modal").classList.remove("active");
    updateUserLabel();
  } catch (requestError) {
    console.error("User registration failed", requestError);
    error.textContent = "Could not connect to EduCards. Please try again.";
  }
}

function switchView(viewName) {
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  document.querySelectorAll("nav button").forEach(b => b.classList.remove("active"));
  
  const viewEl = document.getElementById(`view-${viewName}`);
  if (viewEl) viewEl.classList.add("active");
  
  const navEl = document.getElementById(`nav-${viewName}`);
  if (navEl) navEl.classList.add("active");
  
  if (viewName === "dashboard" || viewName === "decks") {
    loadDecks();
  } else if (viewName === "materials") {
    loadMaterials();
  } else if (viewName === "leaderboard") {
    loadLeaderboard();
  } else if (viewName === "profile") {
    loadProfile();
  } else if (viewName === "analytics") {
    loadAnalytics(activeAnalyticsView);
  }
}

async function loadDecks() {
  try {
    const res = await fetch("/api/decks");
    if (!res.ok) throw new Error(`Deck request failed (${res.status})`);
    currentDecks = await res.json();
    renderDecks();
  } catch (err) {
    console.error("Failed to load decks", err);
  }
}

function renderDecks() {
  const grid = document.getElementById("decks-grid");
  const dashGrid = document.getElementById("dashboard-decks-grid");
  
  if (!currentDecks.length) {
    const emptyHtml = `<p style="color: var(--text-secondary);">No study decks yet. Click "+ Gen AI Deck" to create one!</p>`;
    if (grid) grid.innerHTML = emptyHtml;
    if (dashGrid) dashGrid.innerHTML = emptyHtml;
    return;
  }

  const html = currentDecks.map(deck => `
    <div class="card">
      <div>
        <span class="badge">${escapeHtml(deck.category)}</span>
        <h3>${escapeHtml(deck.title)}</h3>
        <p>${escapeHtml(deck.description)}</p>
        <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1rem;">${deck.cards.length} MCQs &bull; By ${escapeHtml(deck.creator)}</p>
      </div>


            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
        <button class="btn" data-action="practice" data-deck-id="${escapeHtml(deck.id)}" style="flex: 1;">Practice</button>
        <button class="btn btn-secondary" data-action="mindmap" data-deck-id="${escapeHtml(deck.id)}">Mindmap</button>
      </div>

      <div style="display: flex; justify-content: flex-end; margin-top: 0.65rem;">
        <button
          class="btn btn-danger"
          data-action="delete" data-deck-id="${escapeHtml(deck.id)}"
          style="padding: 0.45rem 0.8rem;"
        >Delete deck</button>
      </div>
    </div>
  `).join("");

  if (grid) grid.innerHTML = html;
  if (dashGrid) dashGrid.innerHTML = html;
}

function handleDeckAction(event) {
  const button = event.target.closest("button[data-action][data-deck-id]");
  if (!button) return;
  const { action, deckId } = button.dataset;
  if (action === "practice") startPractice(deckId);
  else if (action === "mindmap") openMindmapForDeck(deckId);
  else if (action === "delete") deleteDeck(deckId);
}

async function deleteDeck(deckId) {
  const deck = currentDecks.find(item => item.id === deckId);
  const deckTitle = deck ? deck.title : "this deck";

  const confirmed = window.confirm(
    `Are you sure you want to delete "${deckTitle}"?\n\nThis action cannot be undone.`
  );

  if (!confirmed) {
    return;
  }

  try {
    const response = await fetch(
      `/api/decks/${encodeURIComponent(deckId)}`,
      { method: "DELETE" }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || `Delete failed (${response.status})`
      );
    }

    currentDecks = currentDecks.filter(
      item => item.id !== deckId
    );

    renderDecks();

    window.alert(`"${deckTitle}" has been deleted successfully.`);
  } catch (error) {
    console.error("Failed to delete deck:", error);
    window.alert(`Could not delete deck: ${error.message}`);
  }
}
async function loadMaterials() {
  try {
    const res = await fetch("/api/materials");
    currentMaterials = await res.json();
    renderMaterials();
    updateMaterialDropdown();
  } catch (err) {
    console.error("Failed to load materials", err);
  }
}

function renderMaterials() {
  const listEl = document.getElementById("materials-list");
  if (!currentMaterials.length) {
    listEl.innerHTML = `<p style="color: var(--text-secondary);">No study materials uploaded yet.</p>`;
    return;
  }

  listEl.innerHTML = currentMaterials.map(m => `
    <div style="padding: 1rem; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
      <div>
        <strong>📄 ${escapeHtml(m.filename)}</strong>
        <p style="font-size: 0.85rem; color: var(--text-secondary); margin: 0;">Chunks: ${m.chunk_count} &bull; Uploaded: ${new Date(m.uploaded_at).toLocaleDateString()}</p>
      </div>
      <span class="badge status-positive">Indexed for RAG</span>
    </div>
  `).join("");
}

function updateMaterialDropdown() {
  const select = document.getElementById("gen-material");
  if (!select) return;
  
  let html = `<option value="">-- Use General Knowledge / All Materials --</option>`;
  currentMaterials.forEach(m => {
    html += `<option value="${escapeHtml(m.id)}">${escapeHtml(m.filename)} (${m.chunk_count} chunks)</option>`;
  });
  select.innerHTML = html;
}

async function uploadMaterial(event) {
  event.preventDefault();
  const fileInput = document.getElementById("material-file");
  const file = fileInput.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/materials/upload", {
      method: "POST",
      body: formData
    });
    if (res.ok) {
      fileInput.value = "";
      loadMaterials();
      alert("Material successfully uploaded and indexed for RAG!");
    } else {
      alert("Failed to upload material.");
    }
  } catch (err) {
    console.error("Upload error", err);
    alert("Error uploading material.");
  }
}

function openGenModal() {
  document.getElementById("gen-modal").classList.add("active");
}

function closeGenModal() {
  document.getElementById("gen-modal").classList.remove("active");
}

async function generateDeck(event) {
  event.preventDefault();
  const topic = document.getElementById("gen-topic").value;
  const count = parseInt(document.getElementById("gen-count").value);
  const materialId = document.getElementById("gen-material").value;

  closeGenModal();
  
  // Show loading indicator
  const grid = document.getElementById("decks-grid");
  if (grid) grid.innerHTML = `<p style="color: var(--accent); font-weight: 600;">Building your study deck...</p>`;

  try {
    const res = await fetch("/api/decks/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic, count, material_id: materialId || null })
    });

    if (res.ok) {
      const deck = await res.json();
      await loadDecks();
      startPractice(deck.id);
    } else {
      let detail = "Unknown server error";
      try { const body = await res.json(); detail = body.detail || JSON.stringify(body); } catch (_) {}
      alert(`Could not generate deck: ${detail}`);
      await loadDecks();
    }
  } catch (err) {
    console.error("Generation error", err);
    alert("Error generating deck.");
    loadDecks();
  }
}

async function startPractice(deckId) {
  if (!currentUser) {
    document.getElementById("identity-modal").classList.add("active");
    return;
  }
  currentDeck = currentDecks.find(d => d.id === deckId);
  // Fetch the canonical deck from the API if the dashboard's cached copy is stale.
  if (!currentDeck || !Array.isArray(currentDeck.cards) || currentDeck.cards.length === 0) {
    try {
      const response = await fetch(`/api/decks/${encodeURIComponent(deckId)}`);
      if (response.ok) {
        currentDeck = await response.json();
        const index = currentDecks.findIndex(d => d.id === deckId);
        if (index >= 0) currentDecks[index] = currentDeck;
        else currentDecks.push(currentDeck);
        renderDecks();
      }
    } catch (error) {
      console.error("Could not refresh deck before practice", error);
    }
  }
  if (!currentDeck || !Array.isArray(currentDeck.cards) || currentDeck.cards.length === 0) {
    alert("This deck has no valid MCQs. Choose another deck or generate new questions.");
    return;
  }
  try {
    const response = await fetch("/api/deck-sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: currentUser.id, deck_id: deckId })
    });
    const session = await response.json();
    if (!response.ok) throw new Error(session.detail || "Could not start practice session.");
    currentSessionId = session.id;
  } catch (error) {
    console.error("Could not start practice session", error);
    alert(error.message || "Could not start practice session.");
    return;
  }
  currentCardIndex = 0;
  currentSessionPoints = 0;
  currentStreak = 0;
  clearTimeout(practiceAdvanceTimer);
  practiceAdvanceTimer = null;
  completedCardIds = new Set();
  answeredCardIds = new Set();
  wrongCardIds = new Set();
  reviewMode = false;
  practiceStartedAt = performance.now();
  sessionFinished = false;
  document.getElementById("practice-active-content").hidden = false;
  document.getElementById("practice-results").hidden = true;
  resetHintState();
  document.getElementById("practice-deck-title").innerText = currentDeck.title;
  switchView("practice");
  renderCard();
}

function renderCard() {
  if (!currentDeck || !currentDeck.cards.length) return;
  const cards = getPracticeCards();
  if (currentCardIndex < 0 || currentCardIndex >= cards.length) return;
  const card = cards[currentCardIndex];
  document.getElementById("practice-progress").innerText =
    `${reviewMode ? "Mistake" : "Card"} ${currentCardIndex + 1} of ${cards.length}`;
  updateProgressRing();
  document.getElementById("mcq-question").textContent = card.question;
  const optionsEl = document.getElementById("mcq-options");
  optionsEl.replaceChildren();
  card.options.forEach(option => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "mcq-option";
    button.textContent = option;
    button.disabled = sessionFinished && !reviewMode;
    button.addEventListener("click", () => checkMcqAnswer(option));
    optionsEl.appendChild(button);
  });
  currentQuestionStartedAt = performance.now();
  currentQuestionHintsUsed = 0;
  document.getElementById("practice-status").textContent = "";
  const explanation = document.getElementById("card-explanation");
  explanation.hidden = true;
  explanation.textContent = "";
  const nextButton = document.querySelector("#practice-active-content > div:last-child button:last-child");
  if (nextButton) nextButton.textContent = reviewMode ? "Next Mistake →" : "Next Card →";
  currentWrongContext = {
    question: card.question,
    user_answer: null,
    correct_answer: card.answer,
  };
  currentAnswerWasWrong = false;
  updatePracticeStats();
}

function getPracticeCards() {
  if (!currentDeck) return [];
  return reviewMode
    ? currentDeck.cards.filter(card => wrongCardIds.has(card.id))
    : currentDeck.cards;
}

function updatePracticeStats() {
  document.getElementById("practice-score").textContent = currentSessionPoints;
  document.getElementById("practice-streak").textContent = currentStreak;
}

async function checkMcqAnswer(selected) {
  if (!currentDeck || !currentSessionId || (sessionFinished && !reviewMode)) return;
  const card = getPracticeCards()[currentCardIndex];
  const optionsEl = document.getElementById("mcq-options");
  const buttons = optionsEl.querySelectorAll(".mcq-option");
  buttons.forEach(button => {
    button.disabled = true;
    if (button.textContent === card.answer) button.classList.add("correct");
    else if (button.textContent === selected) button.classList.add("incorrect");
  });

  if (reviewMode) {
    document.getElementById("practice-status").textContent =
      selected === card.answer ? "Correct." : `Review answer: ${card.answer}`;
    const explanation = document.getElementById("card-explanation");
    explanation.textContent = card.explanation || "Review the key concept behind the correct answer.";
    explanation.hidden = false;
    return;
  }

  try {
    const response = await fetch("/api/attempts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: currentUser.id,
        session_id: currentSessionId,
        deck_id: currentDeck.id,
        card_id: card.id,
        selected,
        time_taken_ms: Math.max(0, Math.round(performance.now() - currentQuestionStartedAt)),
        hints_used: currentQuestionHintsUsed
      })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Could not save your answer.");
    currentSessionPoints = result.session_points;
    currentStreak = result.current_streak;
    updatePracticeStats();
    currentWrongContext = {
      question: card.question,
      user_answer: result.is_correct ? null : selected,
      correct_answer: card.answer
    };

    if (result.is_correct) {
      currentAnswerWasWrong = false;
      completedCardIds.add(card.id);
      answeredCardIds.add(card.id);
      updateProgressRing();
      document.getElementById("practice-status").textContent =
        `Correct! +${result.points_awarded} points${currentStreak >= 5 ? " · 1.5× streak bonus" : ""}`;
      const explanation = document.getElementById("card-explanation");
      explanation.hidden = true;
      explanation.textContent = "";
      if (completedCardIds.size === currentDeck.cards.length) {
        await finishPracticeSession();
      } else {
        practiceAdvanceTimer = setTimeout(nextCard, 1000);
      }
    } else {
      answeredCardIds.add(card.id);
      updateProgressRing();
      wrongCardIds.add(card.id);
      document.getElementById("practice-status").textContent = "Not quite. Review the explanation, then try another option.";
      const explanation = document.getElementById("card-explanation");
      explanation.textContent = card.explanation || "Compare the selected option with the concept tested by this question.";
      explanation.hidden = false;
    }
  } catch (error) {
    console.error("Could not record MCQ attempt", error);
    document.getElementById("practice-status").textContent = error.message || "Could not save your answer.";
    buttons.forEach(button => {
      button.disabled = false;
      button.classList.remove("correct", "incorrect");
    });
  }
}

async function finishPracticeSession() {
  if (!currentSessionId || sessionFinished) return;
  try {
    const response = await fetch(
      `/api/deck-sessions/${encodeURIComponent(currentSessionId)}/finish?user_id=${encodeURIComponent(currentUser.id)}`,
      { method: "POST" }
    );
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Could not finish practice session.");
    sessionFinished = true;
    document.getElementById("practice-active-content").hidden = true;
    document.getElementById("practice-results").hidden = false;
    document.getElementById("result-accuracy").textContent = `${result.score}%`;
    document.getElementById("result-points").textContent = result.total_points;
    document.getElementById("result-time").textContent =
      `${Math.max(0, Math.round((performance.now() - practiceStartedAt) / 1000))} seconds`;
    const reviewButton = document.getElementById("review-mistakes");
    reviewButton.hidden = wrongCardIds.size === 0;
    await loadDeckOverview();
    document.querySelectorAll("#mcq-options .mcq-option").forEach(button => {
      button.disabled = true;
    });
  } catch (error) {
    console.error("Could not finish practice session", error);
    document.getElementById("practice-status").textContent = error.message;
  }
}

async function loadDeckOverview() {
  const loading = document.getElementById("overview-loading");
  const container = document.getElementById("overview-content");
  loading.hidden = false;
  loading.textContent = "Preparing your AI overview...";
  container.replaceChildren();
  try {
    const response = await fetch(`/api/decks/${encodeURIComponent(currentDeck.id)}/overview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: currentSessionId })
    });
    const overview = await response.json();
    if (!response.ok) throw new Error(overview.detail || "Could not load the session overview.");
    if (!isValidOverview(overview)) throw new Error("The session overview had an invalid format.");
    loading.hidden = true;
    renderDeckOverview(overview, container);
  } catch (error) {
    console.error("Could not load deck overview", error);
    loading.textContent = error.message || "Could not load the session overview.";
  }
}

function isValidOverview(overview) {
  const requiredMistakeKeys = [
    "question", "your_answer", "correct_answer", "why_you_may_have_erred", "tip"
  ];
  return overview && typeof overview.summary === "string" &&
    ["strengths", "weak_areas", "next_steps", "mistake_review"].every(key => Array.isArray(overview[key])) &&
    overview.strengths.every(value => typeof value === "string") &&
    overview.weak_areas.every(value => typeof value === "string") &&
    overview.next_steps.every(value => typeof value === "string") &&
    overview.mistake_review.every(item =>
      item && requiredMistakeKeys.every(key => typeof item[key] === "string"));
}

function renderDeckOverview(overview, container) {
  const summary = document.createElement("p");
  summary.className = "overview-summary";
  summary.textContent = overview.summary;
  container.appendChild(summary);
  appendOverviewList(container, "Strengths", overview.strengths);
  appendOverviewList(container, "Areas to strengthen", overview.weak_areas);
  appendOverviewList(container, "Next steps", overview.next_steps);
  if (overview.mistake_review.length) {
    const section = document.createElement("section");
    const heading = document.createElement("h4");
    heading.textContent = "Mistake review";
    section.appendChild(heading);
    for (const mistake of overview.mistake_review) {
      const item = document.createElement("article");
      item.className = "mistake-review-item";
      const question = document.createElement("h5");
      question.textContent = mistake.question;
      item.appendChild(question);
      for (const [label, value] of [
        ["Your answer", mistake.your_answer],
        ["Correct answer", mistake.correct_answer],
        ["Why it may have happened", mistake.why_you_may_have_erred],
        ["Tip", mistake.tip],
      ]) {
        const paragraph = document.createElement("p");
        paragraph.textContent = `${label}: ${value}`;
        item.appendChild(paragraph);
      }
      section.appendChild(item);
    }
    container.appendChild(section);
  }
}

function appendOverviewList(container, title, values) {
  const section = document.createElement("section");
  const heading = document.createElement("h4");
  heading.textContent = title;
  section.appendChild(heading);
  const list = document.createElement("ul");
  for (const value of values) {
    const item = document.createElement("li");
    item.textContent = value;
    list.appendChild(item);
  }
  section.appendChild(list);
  container.appendChild(section);
}

function nextCard() {
  if (!currentDeck) return;
  clearTimeout(practiceAdvanceTimer);
  practiceAdvanceTimer = null;
  resetHintState();
  const cards = getPracticeCards();
  if (reviewMode && currentCardIndex + 1 >= cards.length) {
    reviewMode = false;
    currentCardIndex = 0;
    document.getElementById("practice-active-content").hidden = true;
    document.getElementById("practice-results").hidden = false;
    return;
  }
  currentCardIndex = (currentCardIndex + 1) % cards.length;
  renderCard();
}

function prevCard() {
  if (!currentDeck) return;
  resetHintState();
  const cards = getPracticeCards();
  currentCardIndex = (currentCardIndex - 1 + cards.length) % cards.length;
  renderCard();
}

function reviewMistakes() {
  if (!wrongCardIds.size) return;
  reviewMode = true;
  currentCardIndex = 0;
  document.getElementById("practice-results").hidden = true;
  document.getElementById("practice-active-content").hidden = false;
  renderCard();
}

function showAnalytics(view) {
  activeAnalyticsView = view;
  document.getElementById("analytics-tab-me").setAttribute("aria-selected", String(view === "me"));
  document.getElementById("analytics-tab-global").setAttribute("aria-selected", String(view === "global"));
  document.getElementById("analytics-tab-me").classList.toggle("btn-secondary", view !== "me");
  document.getElementById("analytics-tab-global").classList.toggle("btn-secondary", view !== "global");
  loadAnalytics(view);
}

async function loadAnalytics(view) {
  const summary = document.getElementById("analytics-summary");
  const charts = document.getElementById("analytics-charts");
  const details = document.getElementById("analytics-details");
  summary.textContent = "Loading analytics...";
  charts.replaceChildren();
  details.replaceChildren();
  if (view === "me" && !currentUser) {
    summary.textContent = "Choose a username to view your analytics.";
    return;
  }
  try {
    const url = view === "me"
      ? `/api/analytics/me/${encodeURIComponent(currentUser.id)}?theme=${activeTheme}`
      : `/api/analytics/global?theme=${activeTheme}`;
    const response = await fetch(url);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Could not load analytics.");
    if (view === "me") renderPersonalAnalytics(data, summary, charts, details);
    else renderGlobalAnalytics(data, summary, charts, details);
  } catch (error) {
    console.error("Could not load analytics", error);
    summary.textContent = error.message || "Could not load analytics.";
  }
}

function renderAnalyticsCharts(chartData, chartNames, container) {
  const labels = {
    accuracy_by_subject: "Accuracy by subject",
    learning_curve: "Learning curve",
    daily_activity: "Activity by day",
    response_time_distribution: "Response time distribution",
    points_distribution: "Points distribution"
  };
  for (const name of chartNames) {
    const source = chartData[name];
    if (typeof source !== "string" ||
        !/^data:image\/png;base64,[A-Za-z0-9+/=]+$/.test(source)) continue;
    const figure = document.createElement("figure");
    figure.className = "analytics-chart";
    const caption = document.createElement("figcaption");
    caption.textContent = labels[name];
    const image = document.createElement("img");
    image.alt = labels[name];
    image.src = source;
    figure.append(caption, image);
    container.appendChild(figure);
  }
}

function renderPersonalAnalytics(data, summary, charts, details) {
  if (data.total_attempts === 0) {
    summary.textContent = "No practice data yet. Complete a deck to see your learning trends.";
    return;
  }
  summary.textContent = `${data.total_attempts} answers · ${data.accuracy}% accuracy · ` +
      `Rank ${data.rank ? `#${data.rank}` : "not ranked"} · ` +
      `${data.hint_usage_rate}% of answers used a hint · ` +
      `Learning trend ${data.learning_curve_trend_slope >= 0 ? "+" : ""}${data.learning_curve_trend_slope} points per attempt.`;
  renderAnalyticsCharts(
    data.charts,
    ["accuracy_by_subject", "learning_curve", "daily_activity", "response_time_distribution"],
    charts
  );
  const times = data.response_time_ms_percentiles;
  const timeParagraph = document.createElement("p");
  timeParagraph.textContent = times.p50 === null
    ? "Response time percentiles are unavailable."
    : `Response times: median ${(times.p50 / 1000).toFixed(1)}s · ` +
      `90th percentile ${(times.p90 / 1000).toFixed(1)}s · ` +
      `95th percentile ${(times.p95 / 1000).toFixed(1)}s.`;
  details.appendChild(timeParagraph);
  appendAnalyticsList(details, "Accuracy by deck", data.accuracy_by_deck, item =>
    `${item.deck_title || item.deck_id}: ${item.accuracy}% (${item.correct}/${item.attempts})`);
  appendAnalyticsList(details, "Accuracy by difficulty", data.accuracy_by_difficulty, item =>
    `${item.difficulty}: ${item.accuracy}% (${item.correct}/${item.attempts})`);
  appendAnalyticsList(details, "Cards to review", data.weak_cards, item =>
    `${item.question}: ${item.accuracy}% accuracy across ${item.attempts} attempts`);
}

function renderGlobalAnalytics(data, summary, charts, details) {
  if (data.total_attempts === 0) {
    summary.textContent = "No practice data is available yet.";
    return;
  }
  summary.textContent = `${data.total_attempts} aggregate answers across learners. This view does not expose individual answers or attempts.`;
  renderAnalyticsCharts(
    data.charts,
    ["accuracy_by_subject", "daily_activity", "points_distribution"],
    charts
  );
  appendAnalyticsList(details, "Hardest questions", data.hardest_questions, item =>
    `${item.question}: ${item.accuracy}% accuracy across ${item.attempts} answers`);
  appendAnalyticsList(details, "Most active days", data.most_active_days, item =>
    `${item.day}: ${item.attempts} answers`);
}

function appendAnalyticsList(container, title, values, formatValue) {
  const section = document.createElement("section");
  const heading = document.createElement("h3");
  heading.textContent = title;
  section.appendChild(heading);
  if (!values.length) {
    const empty = document.createElement("p");
    empty.textContent = "No data available yet.";
    section.appendChild(empty);
  } else {
    const list = document.createElement("ul");
    for (const value of values) {
      const item = document.createElement("li");
      item.textContent = formatValue(value);
      list.appendChild(item);
    }
    section.appendChild(list);
  }
  container.appendChild(section);
}

async function loadLeaderboard() {
  const container = document.getElementById("leaderboard-content");
  if (!container) return;
  const period = document.getElementById("leaderboard-period").value;
  container.textContent = "Loading leaderboard...";
  try {
    const response = await fetch(`/api/leaderboard?period=${encodeURIComponent(period)}&limit=100`);
    const entries = await response.json();
    if (!response.ok) throw new Error(entries.detail || "Could not load leaderboard.");
    if (!entries.length) {
      container.textContent = "No scores yet. Complete a practice deck to get on the board.";
      return;
    }
    container.innerHTML = `
      <div class="table-scroll">
        <table class="data-table">
          <thead><tr><th>Rank</th><th>Learner</th><th>Points</th><th>Accuracy</th><th>Decks</th></tr></thead>
          <tbody>${entries.map(entry => `
            <tr class="${currentUser && entry.user_id === currentUser.id ? "current-user-row" : ""}">
              <td>${entry.rank}</td>
              <td>${escapeHtml(entry.username)}${currentUser && entry.user_id === currentUser.id ? " (you)" : ""}</td>
              <td>${entry.total_points}</td><td>${entry.accuracy}%</td><td>${entry.decks_completed}</td>
            </tr>`).join("")}</tbody>
        </table>
      </div>`;
  } catch (error) {
    console.error("Could not load leaderboard", error);
    container.textContent = error.message || "Could not load leaderboard.";
  }
}

async function loadProfile() {
  const container = document.getElementById("profile-content");
  const subtitle = document.getElementById("profile-subtitle");
  if (!currentUser) {
    container.textContent = "Choose a username to view your learner profile.";
    return;
  }
  subtitle.textContent = `Learner: ${currentUser.username}`;
  container.textContent = "Loading profile...";
  try {
    const response = await fetch(`/api/users/${encodeURIComponent(currentUser.id)}/profile`);
    const profile = await response.json();
    if (!response.ok) throw new Error(profile.detail || "Could not load profile.");
    const deckRows = profile.accuracy_per_deck.length
      ? profile.accuracy_per_deck.map(deck => `
          <tr><td>${escapeHtml(deck.deck_title)}</td><td>${deck.attempts}</td><td>${deck.accuracy}%</td></tr>`).join("")
      : `<tr><td colspan="3">No attempts yet.</td></tr>`;
    const weakTopics = profile.weakest_topics.length
      ? profile.weakest_topics.map(topic => `<li>${escapeHtml(topic.topic)} — ${topic.accuracy}% (${topic.attempts} attempts)</li>`).join("")
      : "<li>Complete some questions to see topics to review.</li>";
    const recentSessions = profile.recent_sessions.length
      ? profile.recent_sessions.map(session => `
          <tr><td>${escapeHtml(session.deck_title)}</td>
          <td>${session.finished_at ? `${session.score}%` : "In progress"}</td>
          <td>${session.total_points}</td>
          <td>${new Date(session.started_at).toLocaleDateString()}</td></tr>`).join("")
      : `<tr><td colspan="4">No sessions yet.</td></tr>`;
    container.innerHTML = `
      <div class="profile-summary">
        <div class="profile-stat">Total points<strong>${profile.total_points}</strong></div>
        <div class="profile-stat">Leaderboard rank<strong>${profile.rank ? `#${profile.rank}` : "—"}</strong></div>
        <div class="profile-stat">Accuracy<strong>${profile.accuracy}%</strong></div>
        <div class="profile-stat">Current streak<strong>${profile.current_streak}</strong></div>
        <div class="profile-stat">Best streak<strong>${profile.best_streak}</strong></div>
      </div>
      <section class="panel"><h3>Accuracy by deck</h3>
        <div class="table-scroll"><table class="data-table"><thead><tr><th>Deck</th><th>Attempts</th><th>Accuracy</th></tr></thead><tbody>${deckRows}</tbody></table></div>
      </section>
      <section class="panel"><h3>Topics to review</h3><ul>${weakTopics}</ul></section>
      <section class="panel"><h3>Recent sessions</h3>
        <div class="table-scroll"><table class="data-table"><thead><tr><th>Deck</th><th>Accuracy</th><th>Points</th><th>Date</th></tr></thead><tbody>${recentSessions}</tbody></table></div>
      </section>`;
  } catch (error) {
    console.error("Could not load profile", error);
    container.textContent = error.message || "Could not load profile.";
  }
}

let conversationHistory = [];

function openExplainerModal() {
  if (!currentWrongContext) return;
  resetHintState();
  const hasWrongAnswer = Boolean(currentWrongContext.user_answer);
  document.getElementById("explainer-question-title").textContent = currentWrongContext.question;
  document.getElementById("explainer-summary").textContent = hasWrongAnswer
    ? `You answered "${currentWrongContext.user_answer}". The correct answer is "${currentWrongContext.correct_answer}".`
    : `Correct answer: "${currentWrongContext.correct_answer}". Ask the AI tutor for a deeper explanation.`;
  document.getElementById("tutor-context-badge").textContent =
    hasWrongAnswer ? "Incorrect Answer Analysis" : "Question Explanation";

  conversationHistory = [];
  const badgeEl = document.getElementById("tutor-round-badge");
  if (badgeEl) {
    badgeEl.innerText = "Discussion Round 1 of 3";
    badgeEl.className = "badge status-positive";
  }
  const replySection = document.getElementById("tutor-reply-section");
  if (replySection) replySection.style.display = hasWrongAnswer ? "block" : "none";
  document.getElementById("hint-btn").hidden = !hasWrongAnswer;
  document.getElementById("explain-it-back-container").style.display =
    hasWrongAnswer ? "block" : "none";
  const replyInput = document.getElementById("learner-reply-input");
  if (replyInput) replyInput.value = "";

  document.getElementById("explainer-modal").classList.add("active");
  if (hasWrongAnswer) fetchAiConversationalTurn();
  else fetchSingleAiExplanation();
}

function closeExplainerModal() {
  document.getElementById("explainer-modal").classList.remove("active");
  document.querySelectorAll("#mcq-options .mcq-option").forEach(button => {
    if (currentAnswerWasWrong && !sessionFinished) button.disabled = false;
    button.classList.remove("correct", "incorrect");
  });
}

async function fetchSingleAiExplanation() {
  const container = document.getElementById("tutor-dialogue-container");
  container.textContent = "Consulting tutor...";
  try {
    const response = await fetch("/api/ai/explain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: currentWrongContext.question,
        correct_answer: currentWrongContext.correct_answer,
        understanding_level: document.getElementById("understanding-level").value,
        hint_level: 4
      })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Could not load the AI explanation.");
    if (typeof data.explanation !== "string") throw new Error("The AI explanation was invalid.");
    container.textContent = data.explanation;
  } catch (error) {
    console.error("Could not load AI explanation", error);
    container.textContent = error.message || "Could not load the AI explanation.";
  }
}

function restartConversation() {
  conversationHistory = [];
  fetchAiConversationalTurn();
}

function renderDialogue() {
  const container = document.getElementById("tutor-dialogue-container");
  if (!container) return;

  if (!conversationHistory.length) {
    container.innerHTML = `<div id="explainer-text" style="color: var(--text-primary); margin: 0; white-space: pre-wrap;">Consulting tutor...</div>`;
    return;
  }

  container.innerHTML = conversationHistory.map(msg => {
    if (msg.role === "user") {
      return `
        <div class="dialogue-message dialogue-user">
          <strong>You:</strong>
          <span>${escapeHtml(msg.content)}</span>
        </div>
      `;
    } else {
      return `
        <div class="dialogue-message dialogue-assistant">
          <strong>AI Tutor:</strong>
          <span>${escapeHtml(msg.content)}</span>
        </div>
      `;
    }
  }).join("");

  container.scrollTop = container.scrollHeight;
}

async function sendLearnerReply() {
  const inputEl = document.getElementById("learner-reply-input");
  const text = inputEl ? inputEl.value.trim() : "";
  if (!text) return;

  conversationHistory.push({ role: "user", content: text });
  if (inputEl) inputEl.value = "";
  renderDialogue();

  await fetchAiConversationalTurn();
}

async function fetchAiConversationalTurn() {
  if (!currentWrongContext) return;
  const level = document.getElementById("understanding-level").value;
  const replySection = document.getElementById("tutor-reply-section");
  const badgeEl = document.getElementById("tutor-round-badge");
  const sendBtn = document.getElementById("btn-send-reply");
  if (sendBtn) sendBtn.disabled = true;

  try {
    const res = await fetch("/api/ai/explain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: currentWrongContext.question,
        user_answer: currentWrongContext.user_answer,
        correct_answer: currentWrongContext.correct_answer,
        understanding_level: level,
        history: conversationHistory
      })
    });

    if (res.ok) {
      const data = await res.json();
      if (typeof data.explanation !== "string" || !data.explanation.trim() ||
          typeof data.is_full_explanation !== "boolean" ||
          !Number.isInteger(data.turn_count)) {
        throw new Error("The AI tutor returned an invalid response.");
      }
      conversationHistory.push({ role: "assistant", content: data.explanation });
      renderDialogue();

      if (badgeEl) {
        if (data.is_full_explanation) {
          badgeEl.innerText = "Full Explanation Reached";
          badgeEl.className = "badge status-positive";
        } else {
          badgeEl.innerText = `Discussion Round ${(data.turn_count || 0) + 1} of 3`;
          badgeEl.className = "badge status-positive";
        }
      }

      if (replySection) {
        replySection.style.display = data.is_full_explanation ? "none" : "block";
      }
    } else {
      conversationHistory.push({ role: "assistant", content: "Unable to connect with AI tutor right now." });
      renderDialogue();
    }
  } catch (err) {
    console.error("Conversational tutor error", err);
    conversationHistory.push({ role: "assistant", content: "Error connecting to tutor service." });
    renderDialogue();
  } finally {
    if (sendBtn) sendBtn.disabled = false;
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function resetHintState() {
  hintLevel = 0;
  displayedHints = [];
  renderHints();
  updateHintButton();
}

function updateHintButton() {
  const btn = document.getElementById("hint-btn");
  if (!btn) return;
  if (hintLevel >= 4) {
    btn.style.display = "none";
    btn.disabled = true;
  } else {
    btn.style.display = "inline-flex";
    btn.disabled = false;
    if (hintLevel === 3) {
      btn.innerText = "Show full explanation";
    } else {
      btn.innerText = "Give me a hint";
    }
  }
}

function renderHints() {
  const container = document.getElementById("hint-output");
  if (!container) return;
  if (!displayedHints.length) {
    container.innerText = "Click 'Give me a hint' to get started.";
    return;
  }
  container.innerHTML = displayedHints.map(h => `
    <div class="hint-item">
      <strong style="color: var(--accent);">${h.level === 4 ? "Full Explanation" : `Hint ${h.level}`}:</strong>
      <div style="margin-top: 0.25rem; color: var(--text-primary);">${escapeXml(h.text)}</div>
    </div>
  `).join("");
}

async function requestNextHint() {
  if (hintLevel >= 4 || !currentWrongContext) return;
  const targetLevel = hintLevel + 1;
  const btn = document.getElementById("hint-btn");
  if (btn) {
    btn.disabled = true;
    btn.innerText = "Loading...";
  }

  const level = document.getElementById("understanding-level").value;
  try {
    const res = await fetch("/api/ai/explain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: currentWrongContext.question,
        user_answer: currentWrongContext.user_answer,
        correct_answer: currentWrongContext.correct_answer,
        understanding_level: level,
        hint_level: targetLevel,
        learner_attempt: currentWrongContext.user_answer || null
      })
    });

    if (res.ok) {
      const data = await res.json();
      if (typeof data.explanation !== "string" || !data.explanation.trim()) {
        throw new Error("The AI tutor returned an invalid hint.");
      }
      hintLevel = targetLevel;
      currentQuestionHintsUsed = Math.min(4, currentQuestionHintsUsed + 1);
      displayedHints.push({ level: hintLevel, text: data.explanation });
      renderHints();
    } else {
      alert("Failed to fetch hint.");
    }
  } catch (err) {
    console.error("Hint error", err);
    alert("Error fetching hint.");
  } finally {
    updateHintButton();
  }
}

async function fetchAiExplanation() {
  if (!currentWrongContext || hintLevel === 0) return;
  const level = document.getElementById("understanding-level").value;
  try {
    const res = await fetch("/api/ai/explain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: currentWrongContext.question,
        user_answer: currentWrongContext.user_answer,
        correct_answer: currentWrongContext.correct_answer,
        understanding_level: level,
        hint_level: hintLevel,
        learner_attempt: currentWrongContext.user_answer || null
      })
    });

    if (res.ok) {
      const data = await res.json();
      if (typeof data.explanation !== "string" || !data.explanation.trim()) {
        throw new Error("The AI tutor returned an invalid explanation.");
      }
      if (displayedHints.length > 0) {
        displayedHints[displayedHints.length - 1].text = data.explanation;
        renderHints();
      }
    }
  } catch (err) {
    console.error("Explainer error", err);
  }
}

function escapeHtmlFeedback(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function resetRestatementUI() {
  const container = document.getElementById("explain-it-back-container");
  if (container) container.style.display = "none";
  const inputSection = document.getElementById("restatement-input-section");
  if (inputSection) inputSection.style.display = "block";
  const skippedMsg = document.getElementById("restatement-skipped-msg");
  if (skippedMsg) skippedMsg.style.display = "none";
  const input = document.getElementById("learner-restatement");
  if (input) input.value = "";
  const feedbackBox = document.getElementById("restatement-feedback-box");
  if (feedbackBox) {
    feedbackBox.style.display = "none";
    feedbackBox.innerHTML = "";
  }
}

function showExplainItBackSection() {
  const container = document.getElementById("explain-it-back-container");
  if (container) container.style.display = "block";
}

function skipRestatement() {
  const inputSection = document.getElementById("restatement-input-section");
  const skippedMsg = document.getElementById("restatement-skipped-msg");
  const feedbackBox = document.getElementById("restatement-feedback-box");
  if (inputSection) inputSection.style.display = "none";
  if (feedbackBox) feedbackBox.style.display = "none";
  if (skippedMsg) skippedMsg.style.display = "block";
}

async function submitRestatement() {
  if (!currentWrongContext) return;
  const input = document.getElementById("learner-restatement");
  const restatement = input ? input.value.trim() : "";
  if (!restatement) {
    alert("Please write your restatement before submitting, or tap 'Skip this step'.");
    return;
  }

  const submitBtn = document.getElementById("btn-submit-restatement");
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerText = "Analyzing...";
  }

  try {
    const res = await fetch("/api/ai/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        concept: currentWrongContext.question,
        correct_answer: currentWrongContext.correct_answer,
        learner_restatement: restatement
      })
    });

    if (res.ok) {
      const data = await res.json();
      if (["feedback", "what_was_right", "thing_to_refine"].some(
        key => typeof data[key] !== "string" || !data[key].trim()
      )) {
        throw new Error("The AI tutor returned invalid feedback.");
      }
      const feedbackBox = document.getElementById("restatement-feedback-box");
      if (feedbackBox) {
        feedbackBox.style.display = "block";
        feedbackBox.innerHTML = `
          <strong style="display: block; color: #4338CA; margin-bottom: 0.5rem;">AI Tutor Critique:</strong>
          <p style="margin-bottom: 0.5rem; color: #1E1B4B; white-space: pre-wrap;">${escapeHtmlFeedback(data.feedback)}</p>
          <div style="font-size: 0.85rem; color: #15803D; margin-bottom: 0.25rem;">&bull; <strong>What you got right:</strong> ${escapeHtmlFeedback(data.what_was_right)}</div>
          <div style="font-size: 0.85rem; color: #B45309;">&bull; <strong>To refine:</strong> ${escapeHtmlFeedback(data.thing_to_refine)}</div>
        `;
      }
    } else {
      alert("Unable to fetch feedback at this time.");
    }
  } catch (err) {
    console.error("Feedback error", err);
    alert("Error submitting restatement.");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerText = "Submit for Feedback";
    }
  }
}

// Observe explainer modal opening to activate Explain-it-back section
(function setupExplainItBackObserver() {
  function attach() {
    const modal = document.getElementById("explainer-modal");
    if (!modal) return;
    const observer = new MutationObserver((mutations) => {
      for (const m of mutations) {
        if (m.attributeName === "class" && modal.classList.contains("active")) {
          resetRestatementUI();
          showExplainItBackSection();
        }
      }
    });
    observer.observe(modal, { attributes: true, attributeFilter: ["class"] });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", attach);
  } else {
    attach();
  }
})();

function openMindmapForDeck(deckId) {
  currentDeck = currentDecks.find(d => d.id === deckId);
  if (!currentDeck) return;
  openMindmap();
}

function closeMindmapModal() {
  const modal = document.getElementById("mindmap-modal");
  if (modal) modal.classList.remove("active");
}

async function openMindmap() {
  if (!currentDeck) return;
  const modal = document.getElementById("mindmap-modal");
  const titleEl = document.getElementById("mindmap-title");
  const container = document.getElementById("mindmap-container");

  titleEl.innerText = `${currentDeck.title} - Mindmap`;
  container.innerHTML = `<p style="color: var(--accent); font-weight: 600;">Generating mindmap...</p>`;
  modal.classList.add("active");

  try {
    const res = await fetch(`/api/decks/${encodeURIComponent(currentDeck.id)}/mindmap`, {
      method: "POST"
    });
    if (res.ok) {
      const data = await res.json();
      renderMindmapSvg(data);
    } else {
      container.innerHTML = `<p style="color: var(--danger);">Failed to load mindmap.</p>`;
    }
  } catch (err) {
    console.error("Mindmap error", err);
    container.innerHTML = `<p style="color: var(--danger);">Error loading mindmap.</p>`;
  }
}

function renderMindmapSvg(data) {
  const container = document.getElementById("mindmap-container");
  if (!container) return;
  const colors = getComputedStyle(document.body);
  const surface = colors.getPropertyValue("--card-bg").trim();
  const text = colors.getPropertyValue("--text-primary").trim();
  const accent = colors.getPropertyValue("--accent").trim();
  const border = colors.getPropertyValue("--border").trim();

  const width = 740;
  const height = 460;
  const cx = width / 2;
  const cy = height / 2;
  const nodes = Array.isArray(data.nodes) ? data.nodes : [];
  const edges = Array.isArray(data.edges) ? data.edges : [];

  const positions = {};
  positions["root"] = { x: cx, y: cy };
  if (data.root) {
    positions[data.root] = { x: cx, y: cy };
  }

  const rx = 240;
  const ry = 150;
  nodes.forEach((node, idx) => {
    const angle = (2 * Math.PI * idx) / nodes.length - Math.PI / 2;
    const nx = Math.round(cx + rx * Math.cos(angle));
    const ny = Math.round(cy + ry * Math.sin(angle));
    positions[node.id] = { x: nx, y: ny };
  });

  let linesHtml = "";
  const connectedNodes = new Set();
  edges.forEach(edge => {
    const p1 = positions[edge.from];
    const p2 = positions[edge.to];
    if (p1 && p2) {
      linesHtml += `<line x1="${p1.x}" y1="${p1.y}" x2="${p2.x}" y2="${p2.y}" stroke="${border}" stroke-width="2" />`;
      connectedNodes.add(edge.to);
      connectedNodes.add(edge.from);
    }
  });

  nodes.forEach(node => {
    if (!connectedNodes.has(node.id)) {
      const p = positions[node.id];
      if (p) {
        linesHtml += `<line x1="${cx}" y1="${cy}" x2="${p.x}" y2="${p.y}" stroke="${border}" stroke-width="2" />`;
      }
    }
  });

  const rootFull = data.root || "Topic";
  const rootLabel = truncate(rootFull, 22);
  let nodesHtml = `
    <g class="mindmap-root-node">
      <rect x="${cx - 95}" y="${cy - 24}" width="190" height="48" rx="8" fill="${surface}" stroke="${accent}" stroke-width="2" />
      <text x="${cx}" y="${cy}" fill="${text}" font-size="13" font-weight="bold" text-anchor="middle" dominant-baseline="central">${escapeXml(rootLabel)}</text>
      <title>${escapeXml(rootFull)}</title>
    </g>
  `;

  nodes.forEach(node => {
    const p = positions[node.id];
    const full = node.label || node.id;
    const label = truncate(full, 20);
    nodesHtml += `
      <g class="mindmap-child-node">
        <rect x="${p.x - 70}" y="${p.y - 20}" width="140" height="40" rx="6" fill="${surface}" stroke="${accent}" stroke-width="2" />
        <text x="${p.x}" y="${p.y}" fill="${text}" font-size="11" font-weight="600" text-anchor="middle" dominant-baseline="central">${escapeXml(label)}</text>
        <title>${escapeXml(full)}</title>
      </g>
    `;
  });

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" xmlns="http://www.w3.org/2000/svg" style="background: ${surface}; border-radius: 8px; border: 1px solid ${border};">
      <g class="edges">${linesHtml}</g>
      <g class="nodes">${nodesHtml}</g>
    </svg>
  `;
}

function truncate(str, maxLen) {
  if (!str) return "";
  return str.length > maxLen ? str.slice(0, maxLen - 1) + "…" : str;
}

function escapeXml(unsafe) {
  if (!unsafe) return "";
  return String(unsafe).replace(/[<>&'"]/g, c => {
    switch (c) {
      case '<': return '&lt;';
      case '>': return '&gt;';
      case '&': return '&amp;';
      case '\'': return '&apos;';
      case '"': return '&quot;';
    }
  });
}
