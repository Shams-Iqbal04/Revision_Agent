import streamlit as st
import html
import json
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from agent.tutor_agent import step_tutor
from database.db import get_analytics
from utils.ingestion import extract_text_from_file

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="AI Revision Agent - 1-on-1 Interactive AI Tutor",
    page_icon="🎓",
    layout="wide"
)

# ============================================================
# CSS STYLING
# ============================================================
st.markdown("""
<style>
.main-header {
    font-size: 2.2rem;
    font-weight: 800;
    color: #4F46E5;
    margin-bottom: 0.1rem;
}
.sub-header {
    font-size: 1rem;
    color: #6B7280;
    margin-bottom: 1.5rem;
}
.agent-action-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 9999px;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
}
.badge-question {
    background-color: #EEF2FF;
    color: #4F46E5;
    border: 1px solid #C7D2FE;
}
.badge-notes {
    background-color: #FEF3C7;
    color: #D97706;
    border: 1px solid #FDE68A;
}
.badge-explanation {
    background-color: #ECFDF5;
    color: #059669;
    border: 1px solid #A7F3D0;
}
.badge-code {
    background-color: #F3F4F6;
    color: #374151;
    border: 1px solid #E5E7EB;
}
.badge-conclude {
    background-color: #EDE9FE;
    color: #7C3AED;
    border: 1px solid #DDD6FE;
}
.turn-card {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.04);
}
.student-answer-card {
    background-color: #F0F9FF;
    border: 1px solid #BAE6FD;
    border-radius: 14px;
    padding: 16px 20px;
    margin-bottom: 16px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.04);
}
.student-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 9999px;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
    background-color: #DBEAFE;
    color: #1D4ED8;
    border: 1px solid #93C5FD;
}
.notes-box {
    background-color: #FFFBEB;
    border: 1px solid #FDE68A;
    border-radius: 12px;
    padding: 20px;
    margin: 10px 0;
}
.key-points-box {
    background-color: #FEF3C7;
    border-radius: 8px;
    padding: 12px 16px;
    margin-top: 12px;
    font-size: 14px;
}
.metric-box {
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 12px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_active" not in st.session_state:
    st.session_state.session_active = False

if "topic" not in st.session_state:
    st.session_state.topic = ""

if "difficulty" not in st.session_state:
    st.session_state.difficulty = "Beginner"

if "action_history" not in st.session_state:
    st.session_state.action_history = []

# List of dicts: {"answer": str, "after_action_idx": int}
# Tracks what the student typed after each agent turn
if "student_answers" not in st.session_state:
    st.session_state.student_answers = []

if "questions_answered" not in st.session_state:
    st.session_state.questions_answered = 0

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.title("🎓 AI Tutor Control")
    analytics = get_analytics()
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="metric-box"><div style="font-size:11px;color:#64748B;">Questions</div><div style="font-size:20px;font-weight:700;color:#4F46E5;">{st.session_state.questions_answered}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-box"><div style="font-size:11px;color:#64748B;">Turns Taken</div><div style="font-size:20px;font-weight:700;color:#059669;">{len(st.session_state.action_history)}</div></div>', unsafe_allow_html=True)

    st.divider()
    st.subheader("📁 Upload Study Notes (Optional)")
    uploaded_file = st.file_uploader("Upload PDF or TXT", type=["pdf", "txt", "md"])
    doc_text = ""
    if uploaded_file:
        doc_text = extract_text_from_file(uploaded_file)
        if doc_text:
            st.success(f"Loaded {len(doc_text)} chars from {uploaded_file.name}")

    st.divider()
    if st.session_state.session_active:
        if st.button("🔄 Reset / Start New Topic", use_container_width=True):
            st.session_state.messages = []
            st.session_state.action_history = []
            st.session_state.student_answers = []
            st.session_state.session_active = False
            st.session_state.questions_answered = 0
            st.rerun()

    st.caption("🤖 Powered by Tool-Calling ReAct AI Agent with Groq")

# ============================================================
# HEADER
# ============================================================
st.markdown('<div class="main-header">🎓 Autonomous AI Revision Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Your 1-on-1 adaptive AI Tutor: get revision notes, answer questions, and learn from your mistakes.</div>', unsafe_allow_html=True)

# ============================================================
# SESSION CONFIG & START
# ============================================================
if not st.session_state.session_active:
    st.markdown("### 1️⃣ Start Your Revision Session")
    col_t, col_d = st.columns([3, 1])
    with col_t:
        topic_input = st.text_input(
            "What topic do you want to revise?",
            placeholder="e.g. Python Generators, Garbage Collection, SQL Joins, System Design"
        )
    with col_d:
        diff_input = st.selectbox("Your Level", ["Beginner", "Intermediate", "Advanced"])

    if st.button("🚀 Begin Tutoring Session", type="primary", use_container_width=True):
        if not topic_input and not doc_text:
            st.warning("Please enter a topic or upload notes.")
        else:
            final_topic = topic_input if topic_input else "Uploaded Document Study Notes"
            if doc_text:
                final_topic += f"\n\nContext Notes:\n{doc_text[:1500]}"
            st.session_state.topic = final_topic
            st.session_state.difficulty = diff_input
            st.session_state.session_active = True
            
            # Initial trigger message to the agent
            start_msg = HumanMessage(content=f"Hi, I want to revise {final_topic} at {diff_input} level. Please start by giving me revision notes on this topic, and then ask me a question.")
            st.session_state.messages.append(start_msg)

            with st.spinner("🤖 AI Tutor is preparing your revision notes and first question..."):
                res = step_tutor(st.session_state.messages, topic=final_topic, difficulty=diff_input)
                st.session_state.messages.append(res["response"])
                st.session_state.action_history.append(res)

            st.rerun()
    st.stop()

# ============================================================
# ACTIVE SESSION UI
# ============================================================
st.info(f"📚 **Currently Revising:** {st.session_state.topic.splitlines()[0]} | **Level:** {st.session_state.difficulty}")

# ---- Render History of Agent Actions and Student Answers ----
for idx, act in enumerate(st.session_state.action_history):
    tool_calls = act.get("tool_calls", [])
    agent_text = act.get("content", "")
    
    # Show agent's text response (correct/wrong feedback) if present
    if agent_text and agent_text.strip():
        with st.container():
            st.markdown('<div class="turn-card">', unsafe_allow_html=True)
            st.markdown(f"🤖 **AI Tutor:** {agent_text}")
            st.markdown('</div>', unsafe_allow_html=True)

    # Show each tool action
    for tc in tool_calls:
        t_name = tc.get("name")
        t_args = tc.get("args", {})

        with st.container():
            st.markdown('<div class="turn-card">', unsafe_allow_html=True)

            if t_name == "ask_question":
                q = t_args.get("question", "")
                diff = t_args.get("difficulty", "Medium")
                st.markdown(f'<span class="agent-action-badge badge-question">❓ Question ({diff})</span>', unsafe_allow_html=True)
                st.markdown(f"### {q}")
                hint = t_args.get("hint", "")
                if hint:
                    st.caption(f"💡 Hint: {hint}")

            elif t_name == "give_revision_notes":
                title = t_args.get("topic_title", "Revision Notes")
                notes = t_args.get("notes", "")
                key_points = t_args.get("key_points", "")
                st.markdown(f'<span class="agent-action-badge badge-notes">📝 Revision Notes</span>', unsafe_allow_html=True)
                st.markdown(f"### 📖 {title}")
                st.markdown(f'<div class="notes-box">', unsafe_allow_html=True)
                st.markdown(notes)
                if key_points:
                    st.markdown(f'<div class="key-points-box"><strong>🔑 Key Points:</strong><br>{key_points}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            elif t_name == "explain_concept":
                title = t_args.get("concept_title", "Concept Breakdown")
                exp = t_args.get("explanation", "")
                code = t_args.get("code_example", "")
                st.markdown('<span class="agent-action-badge badge-explanation">📖 Concept Explanation</span>', unsafe_allow_html=True)
                st.markdown(f"### 💡 {title}")
                st.markdown(exp)
                if code:
                    st.code(code, language="python")

            elif t_name == "test_code_execution":
                code = t_args.get("code", "")
                st.markdown('<span class="agent-action-badge badge-code">💻 Code Verification</span>', unsafe_allow_html=True)
                st.code(code, language="python")

            elif t_name == "conclude_session":
                score = t_args.get("mastery_percentage", 100)
                summary = t_args.get("summary", "Great job!")
                weak = t_args.get("weak_topics", [])
                st.markdown('<span class="agent-action-badge badge-conclude">🏆 Revision Completed!</span>', unsafe_allow_html=True)
                st.balloons()
                st.markdown(f"## 🎉 Mastery Score: {score}%")
                st.markdown(summary)
                if weak:
                    st.warning(f"Topics to review next time: {', '.join(weak)}")

            st.markdown('</div>', unsafe_allow_html=True)

    # Show the student's answer that came AFTER this agent turn (if any)
    for sa in st.session_state.student_answers:
        if sa["after_action_idx"] == idx:
            with st.container():
                st.markdown('<div class="student-answer-card">', unsafe_allow_html=True)
                st.markdown(f'<span class="student-badge">🙋 Your Answer</span>', unsafe_allow_html=True)
                st.markdown(f"**{sa['answer']}**")
                st.markdown('</div>', unsafe_allow_html=True)

# ---- User Response Input ----
latest_action = st.session_state.action_history[-1] if st.session_state.action_history else None
latest_tools = latest_action["tool_calls"] if latest_action and latest_action.get("tool_calls") else []
latest_tool_names = [tc["name"] for tc in latest_tools]

# Only show input if session isn't concluded
if "conclude_session" not in latest_tool_names:
    st.markdown("---")
    with st.form("tutor_response_form", clear_on_submit=True):
        placeholder_text = "Type your answer here..." if "ask_question" in latest_tool_names else "Ask a question, say 'next question', or type anything..."
        user_response = st.text_area("Your Response:", placeholder=placeholder_text, height=90)
        submitted = st.form_submit_button("🚀 Submit Answer", type="primary", use_container_width=True)

        if submitted and user_response.strip():
            current_action_idx = len(st.session_state.action_history) - 1
            
            # Save the student's answer for display
            st.session_state.student_answers.append({
                "answer": user_response.strip(),
                "after_action_idx": current_action_idx
            })

            if "ask_question" in latest_tool_names:
                st.session_state.questions_answered += 1

            # Build tool acknowledgment messages for ALL tool calls in the last response
            for tc in latest_tools:
                t_ack = ToolMessage(content="Action presented to student.", tool_call_id=tc["id"])
                st.session_state.messages.append(t_ack)

            # Append student response
            u_msg = HumanMessage(content=user_response.strip())
            st.session_state.messages.append(u_msg)

            with st.spinner("🤖 AI Tutor is evaluating your answer..."):
                next_res = step_tutor(
                    st.session_state.messages,
                    topic=st.session_state.topic,
                    difficulty=st.session_state.difficulty
                )
                st.session_state.messages.append(next_res["response"])
                st.session_state.action_history.append(next_res)

            st.rerun()