

let sessionId = null;
let uploadedDocText = "";
let quizStarted = false;

const $ = (id) => document.getElementById(id);

const startScreen    = $("start-screen");
const sessionScreen  = $("session-screen");
const conversation   = $("conversation");
const loaderOverlay  = $("loader-overlay");
const loaderText     = $("loader-text");
const answerInput    = $("answer-input");
const submitBtn      = $("submit-btn");
const inputBar       = $("input-bar");
const topicDisplay   = $("session-topic");
const levelDisplay   = $("session-level");
const statQuestions  = $("stat-questions");

const doubtMessages  = $("doubt-messages");
const doubtInput     = $("doubt-input");
const doubtSubmitBtn = $("doubt-submit-btn");

const uploadArea  = $("upload-area");
const fileInput   = $("file-upload");
const uploadLabel = $("upload-label");
const uploadStatus = $("upload-status");

uploadArea.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", async () => {
    const file = fileInput.files[0];
    if (!file) return;

    uploadLabel.textContent = `📎 ${file.name}`;
    uploadArea.classList.add("has-file");

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/api/upload", { method: "POST", body: formData });
        const data = await res.json();
        uploadedDocText = data.text || "";
        uploadStatus.textContent = `✅ Extracted ${data.chars.toLocaleString()} characters from ${data.filename}`;
        uploadStatus.classList.remove("hidden");
    } catch (err) {
        uploadStatus.textContent = `❌ Upload failed: ${err.message}`;
        uploadStatus.classList.remove("hidden");
        uploadedDocText = "";
    }
});

answerInput.addEventListener("input", () => {
    answerInput.style.height = "auto";
    answerInput.style.height = Math.min(answerInput.scrollHeight, 140) + "px";
});

doubtInput.addEventListener("input", () => {
    doubtInput.style.height = "auto";
    doubtInput.style.height = Math.min(doubtInput.scrollHeight, 110) + "px";
});

answerInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        submitAnswer();
    }
});

doubtInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        submitDoubt();
    }
});

async function apiPost(endpoint, body) {
    const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

async function startSession() {
    const topic = $("topic-input").value.trim();
    const difficulty = $("difficulty-select").value;

    if (!topic && !uploadedDocText) {
        alert("Please enter a topic or upload study notes.");
        return;
    }

    showLoader("AI Tutor is preparing your revision notes…");

    try {
        const data = await apiPost("/api/session/start", {
            topic: topic || "Uploaded Document Study Notes",
            difficulty,
            doc_text: uploadedDocText || null,
        });

        sessionId = data.session_id;
        quizStarted = false;

        topicDisplay.textContent = data.topic || topic;
        levelDisplay.textContent = data.difficulty;
        startScreen.classList.remove("active");
        sessionScreen.classList.add("active");

        inputBar.classList.add("hidden");

        renderAgentTurn(data, true);
        updateStats(data);
        hideLoader();
        scrollToBottom();
    } catch (err) {
        hideLoader();
        alert("Failed to start session: " + err.message);
    }
}

async function startQuiz() {
    const btn = $("start-quiz-btn");
    if (btn) btn.remove();

    inputBar.classList.remove("hidden");
    quizStarted = true;
    answerInput.placeholder = "Type your answer here…";

    showTypingIndicator();
    scrollToBottom();

    try {
        const data = await apiPost("/api/session/respond", {
            session_id: sessionId,
            answer: "I've read the revision notes. I'm ready — start asking me questions!",
        });

        removeTypingIndicator();
        renderAgentTurn(data, false);
        updateStats(data);
        answerInput.focus();
    } catch (err) {
        removeTypingIndicator();
        renderErrorBubble("Something went wrong: " + err.message);
    }
    scrollToBottom();
}

async function submitAnswer() {
    const answer = answerInput.value.trim();
    if (!answer || !sessionId) return;

    answerInput.disabled = true;
    submitBtn.disabled = true;

    renderStudentAnswer(answer);
    answerInput.value = "";
    answerInput.style.height = "auto";
    scrollToBottom();

    showTypingIndicator();

    try {
        const data = await apiPost("/api/session/respond", {
            session_id: sessionId,
            answer,
        });

        removeTypingIndicator();
        renderAgentTurn(data, false);
        updateStats(data);

        if (data.is_concluded) {
            inputBar.classList.add("hidden");
            launchConfetti();
        }
    } catch (err) {
        removeTypingIndicator();
        renderErrorBubble("Something went wrong: " + err.message);
    } finally {
        answerInput.disabled = false;
        submitBtn.disabled = false;
        answerInput.focus();
        scrollToBottom();
    }
}

async function endQuiz() {
    if (!sessionId) return;

    const confirmEnd = confirm("Are you sure you want to finish the Q&A session and get your final score?");
    if (!confirmEnd) return;

    answerInput.disabled = true;
    submitBtn.disabled = true;
    const endBtn = $("end-quiz-btn");
    if (endBtn) endBtn.disabled = true;

    showTypingIndicator();
    scrollToBottom();

    try {
        const data = await apiPost("/api/session/conclude", {
            session_id: sessionId,
        });

        removeTypingIndicator();
        renderAgentTurn(data, false);
        updateStats(data);

        inputBar.classList.add("hidden");
        launchConfetti();
    } catch (err) {
        removeTypingIndicator();
        renderErrorBubble("Failed to conclude session: " + err.message);
        answerInput.disabled = false;
        submitBtn.disabled = false;
        if (endBtn) endBtn.disabled = false;
    }
    scrollToBottom();
}

async function submitDoubt() {
    const question = doubtInput.value.trim();
    if (!question || !sessionId) return;

    doubtInput.value = "";
    doubtInput.style.height = "auto";
    doubtInput.disabled = true;
    doubtSubmitBtn.disabled = true;

    const userBubble = createElement("div", "doubt-bubble-user");
    userBubble.textContent = question;
    doubtMessages.appendChild(userBubble);
    scrollDoubtToBottom();

    const typingEl = createElement("div", "doubt-typing");
    typingEl.id = "doubt-typing";
    typingEl.innerHTML = `<div class="dot"></div><div class="dot"></div><div class="dot"></div>`;
    doubtMessages.appendChild(typingEl);
    scrollDoubtToBottom();

    try {
        const res = await apiPost("/api/chat/doubt", {
            session_id: sessionId,
            question: question
        });

        const typing = $("doubt-typing");
        if (typing) typing.remove();

        const botBubble = createElement("div", "doubt-bubble-bot");
        botBubble.innerHTML = `
            <div class="doubt-bubble-bot-label">🤖 AI Tutor</div>
            <div>${escapeAndFormat(res.answer || "")}</div>
        `;
        doubtMessages.appendChild(botBubble);
    } catch (err) {
        const typing = $("doubt-typing");
        if (typing) typing.remove();

        const errBubble = createElement("div", "doubt-bubble-bot");
        errBubble.style.borderColor = "#FCA5A5";
        errBubble.style.background = "#FEF2F2";
        errBubble.innerHTML = `<div class="doubt-bubble-bot-label" style="color:#DC2626;">⚠️ Error</div><div>${esc(err.message)}</div>`;
        doubtMessages.appendChild(errBubble);
    } finally {
        doubtInput.disabled = false;
        doubtSubmitBtn.disabled = false;
        doubtInput.focus();
        scrollDoubtToBottom();
    }
}

function scrollDoubtToBottom() {
    requestAnimationFrame(() => {
        doubtMessages.scrollTop = doubtMessages.scrollHeight;
    });
}

async function resetSession() {
    if (sessionId) {
        try {
            await apiPost("/api/session/reset", { session_id: sessionId });
        } catch (_) {  }
    }

    sessionId = null;
    quizStarted = false;
    conversation.innerHTML = "";
    inputBar.classList.remove("hidden");
    sessionScreen.classList.remove("active");
    startScreen.classList.add("active");
    statQuestions.textContent = "0";
    const endBtn = $("end-quiz-btn");
    if (endBtn) endBtn.disabled = false;

    doubtMessages.innerHTML = `
        <div class="doubt-welcome">
            <div class="doubt-welcome-icon">💡</div>
            <div class="doubt-welcome-title">Got any doubts?</div>
            <div class="doubt-welcome-text">
                Ask any questions about the notes or concepts here anytime while revising.
            </div>
        </div>
    `;
    doubtInput.value = "";

    $("topic-input").value = "";
    uploadedDocText = "";
    uploadLabel.textContent = "📄 Choose PDF / TXT";
    uploadArea.classList.remove("has-file");
    uploadStatus.classList.add("hidden");
    fileInput.value = "";
}

function renderAgentTurn(data, isInitialNotes) {
    if (data.agent_text && data.agent_text.trim()) {
        const bubble = createElement("div", "agent-text-bubble");
        bubble.innerHTML = `🤖 ${escapeAndFormat(data.agent_text)}`;
        conversation.appendChild(bubble);
    }

    for (const action of (data.actions || [])) {
        const card = renderActionCard(action);
        if (card) conversation.appendChild(card);
    }

    if (isInitialNotes) {
        renderStartQuizButton();
    }

    if (quizStarted) {
        const hasQuestion = (data.actions || []).some(a => a.type === "ask_question");
        answerInput.placeholder = hasQuestion
            ? "Type your answer here…"
            : "Ask a question, or say anything…";
    }
}

function renderStartQuizButton() {
    const wrapper = createElement("div", "start-quiz-wrapper");
    wrapper.id = "start-quiz-btn";
    wrapper.innerHTML = `
        <button class="btn-start-quiz" onclick="startQuiz()">
            🚀 I'm Ready — Start Questions!
        </button>
        <p class="start-quiz-hint">Take your time reading the notes above. When you're ready, click the button to begin the Q&A session.</p>
    `;
    conversation.appendChild(wrapper);
}

function renderActionCard(action) {
    const { type, args } = action;

    switch (type) {
        case "give_revision_notes": return renderNotesCard(args);
        case "ask_question":       return renderQuestionCard(args);
        case "explain_concept":    return renderExplanationCard(args);
        case "test_code_execution":return renderCodeCard(args);
        case "conclude_session":   return renderConcludeCard(args);
        default: return null;
    }
}

function renderNotesCard(args) {
    const card = createElement("div", "action-card card-notes");
    let html = `
        <span class="action-badge">📝 Revision Notes</span>
        <div class="card-title">📖 ${esc(args.topic_title || "Revision Notes")}</div>
        <div class="notes-content">${escapeAndFormat(args.notes || "")}</div>
    `;
    if (args.key_points) {
        html += `
            <div class="key-points-box">
                <strong>🔑 Key Points</strong>
                ${escapeAndFormat(args.key_points)}
            </div>
        `;
    }
    card.innerHTML = html;
    return card;
}

function renderQuestionCard(args) {
    const card = createElement("div", "action-card card-question");
    let html = `
        <span class="action-badge">❓ Question (${esc(args.difficulty || "Medium")})</span>
        <div class="card-title">${esc(args.question || "")}</div>
    `;
    if (args.hint) {
        html += `<div class="question-hint">💡 Hint: ${esc(args.hint)}</div>`;
    }
    card.innerHTML = html;
    return card;
}

function renderExplanationCard(args) {
    const card = createElement("div", "action-card card-explanation");
    let html = `
        <span class="action-badge">💡 Concept Explanation</span>
        <div class="card-title">${esc(args.concept_title || "Explanation")}</div>
        <div class="explanation-text">${escapeAndFormat(args.explanation || "")}</div>
    `;
    if (args.code_example) {
        html += `<div class="code-block">${esc(args.code_example)}</div>`;
    }
    card.innerHTML = html;
    return card;
}

function renderCodeCard(args) {
    const card = createElement("div", "action-card card-code");
    card.innerHTML = `
        <span class="action-badge">💻 Code Verification</span>
        <div class="code-block">${esc(args.code || "")}</div>
    `;
    return card;
}

function renderConcludeCard(args) {
    const card = createElement("div", "action-card card-conclude");
    let html = `
        <span class="action-badge">🏆 Session Complete</span>
        <div class="mastery-score">🎉 ${args.mastery_percentage || 0}%</div>
        <div class="conclude-summary">${escapeAndFormat(args.summary || "Great job!")}</div>
    `;
    if (args.weak_topics && args.weak_topics.length) {
        html += `
            <div class="weak-topics">
                📌 <strong>Review next time:</strong> ${args.weak_topics.map(esc).join(", ")}
            </div>
        `;
    }
    card.innerHTML = html;
    return card;
}

function renderStudentAnswer(text) {
    const bubble = createElement("div", "student-bubble");
    bubble.innerHTML = `
        <div class="student-label">🙋 Your Answer</div>
        <div class="student-answer-text">${esc(text)}</div>
    `;
    conversation.appendChild(bubble);
}

function renderErrorBubble(message) {
    const bubble = createElement("div", "agent-text-bubble");
    bubble.style.borderColor = "#FCA5A5";
    bubble.style.background = "#FEF2F2";
    bubble.innerHTML = `⚠️ ${esc(message)}`;
    conversation.appendChild(bubble);
}

function showTypingIndicator() {
    const el = createElement("div", "typing-indicator");
    el.id = "typing-dots";
    el.innerHTML = `<div class="dot"></div><div class="dot"></div><div class="dot"></div>`;
    conversation.appendChild(el);
    scrollToBottom();
}

function removeTypingIndicator() {
    const el = $("typing-dots");
    if (el) el.remove();
}

function updateStats(data) {
    statQuestions.textContent = data.questions_answered ?? 0;
}

function showLoader(text) {
    loaderText.textContent = text;
    loaderOverlay.classList.remove("hidden");
}
function hideLoader() {
    loaderOverlay.classList.add("hidden");
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        conversation.scrollTop = conversation.scrollHeight;
    });
}

function launchConfetti() {
    const wrapper = createElement("div", "confetti-wrapper");
    document.body.appendChild(wrapper);
    const colors = ["#4F46E5", "#F59E0B", "#10B981", "#EF4444", "#8B5CF6", "#EC4899"];
    for (let i = 0; i < 80; i++) {
        const piece = document.createElement("div");
        piece.className = "confetti-piece";
        piece.style.left = Math.random() * 100 + "%";
        piece.style.background = colors[Math.floor(Math.random() * colors.length)];
        piece.style.animationDelay = Math.random() * 1.5 + "s";
        piece.style.animationDuration = 2 + Math.random() * 2 + "s";
        piece.style.width = 6 + Math.random() * 8 + "px";
        piece.style.height = 6 + Math.random() * 8 + "px";
        piece.style.borderRadius = Math.random() > 0.5 ? "50%" : "2px";
        wrapper.appendChild(piece);
    }
    setTimeout(() => wrapper.remove(), 5000);
}

function createElement(tag, className) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    return el;
}

function esc(str) {
    const div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
}


function escapeAndFormat(text) {
    if (!text) return "";

    let escaped = esc(text);

    escaped = escaped.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

    escaped = escaped.replace(/`([^`]+)`/g, '<code style="background:#F3F4F6;padding:2px 6px;border-radius:4px;font-size:0.88em;">$1</code>');

    const lines = escaped.split("\n");
    let html = "";
    let inUl = false;
    let inOl = false;

    for (let line of lines) {
        const trimmed = line.trim();

        const ulMatch = trimmed.match(/^[-*]\s+(.+)/);
        if (ulMatch) {
            if (!inUl) { html += "<ul>"; inUl = true; }
            if (inOl) { html += "</ol>"; inOl = false; }
            html += `<li>${ulMatch[1]}</li>`;
            continue;
        }

        const olMatch = trimmed.match(/^\d+[\.)\]]\s+(.+)/);
        if (olMatch) {
            if (!inOl) { html += "<ol>"; inOl = true; }
            if (inUl) { html += "</ul>"; inUl = false; }
            html += `<li>${olMatch[1]}</li>`;
            continue;
        }

        if (inUl) { html += "</ul>"; inUl = false; }
        if (inOl) { html += "</ol>"; inOl = false; }

        html += trimmed ? trimmed + "<br>" : "<br>";
    }

    if (inUl) html += "</ul>";
    if (inOl) html += "</ol>";

    return html;
}
