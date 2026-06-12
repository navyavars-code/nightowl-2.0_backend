import streamlit as st

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="NightOwl 2.0",
    page_icon="🦉",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================================
# CUSTOM CSS
# =========================================================

css = """
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {

    --bg-primary: #0B1020;
    --bg-secondary: #111827;
    --bg-tertiary: #151A2E;

    --card-bg: rgba(255,255,255,0.04);
    --card-border: rgba(255,255,255,0.08);

    --text-primary: #F8FAFC;
    --text-secondary: #CBD5E1;
    --text-muted: #94A3B8;

    --accent-purple: #8B5CF6;
    --accent-indigo: #6366F1;
    --accent-amber: #F59E0B;

}

/* =========================================================
GLOBAL
========================================================= */

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {

    background:
        radial-gradient(circle at top left,
        rgba(99,102,241,0.18),
        transparent 30%),

        radial-gradient(circle at bottom right,
        rgba(139,92,246,0.12),
        transparent 30%),

        linear-gradient(
            135deg,
            #0B1020 0%,
            #111827 50%,
            #151A2E 100%
        );

    color: white;
}

[data-testid="stAppViewContainer"] {
    background: transparent;
}

.main .block-container {
    max-width: 1280px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}

/* REMOVE STREAMLIT DEFAULTS */

#MainMenu,
header,
footer {
    visibility: hidden;
}

/* =========================================================
NAVBAR
========================================================= */

.navbar {

    display: flex;
    justify-content: space-between;
    align-items: center;

    padding: 1rem 1.5rem;

    margin-bottom: 3rem;

    border-radius: 24px;

    background: rgba(255,255,255,0.04);

    backdrop-filter: blur(16px);

    border: 1px solid rgba(255,255,255,0.06);
}

.logo-wrap {
    display: flex;
    align-items: center;
    gap: 14px;
}

.logo-icon {
    font-size: 2.2rem;
}

.logo-text {
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: -1px;
}

.nav-right {
    display: flex;
    align-items: center;
    gap: 12px;
}

.nav-pill {

    padding: 10px 18px;

    border-radius: 999px;

    background: rgba(255,255,255,0.05);

    border: 1px solid rgba(255,255,255,0.06);

    color: var(--text-secondary);

    font-size: 0.9rem;
}

/* =========================================================
HERO
========================================================= */

.hero {

    text-align: center;

    padding-top: 2rem;
    padding-bottom: 3rem;
}

.hero-title {

    font-size: 4.5rem;
    font-weight: 800;

    line-height: 1.05;

    letter-spacing: -2px;

    margin-bottom: 1rem;

    background: linear-gradient(
        to right,
        #ffffff,
        #CBD5E1
    );

    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.hero-sub {

    color: var(--text-muted);

    font-size: 1.15rem;

    max-width: 700px;

    margin: auto;

    line-height: 1.8;
}

/* =========================================================
GLASS CARD
========================================================= */

.glass-card {

    background: rgba(255,255,255,0.04);

    border: 1px solid rgba(255,255,255,0.07);

    border-radius: 30px;

    backdrop-filter: blur(16px);

    transition: 0.3s ease;

    overflow: hidden;
}

.glass-card:hover {
    transform: translateY(-2px);
}

/* =========================================================
UPLOAD
========================================================= */

.upload-wrapper {

    padding: 3rem;

    text-align: center;

    margin-bottom: 3rem;
}

.upload-icon {

    font-size: 4rem;

    margin-bottom: 1rem;

    animation: float 4s ease-in-out infinite;
}

.upload-title {

    font-size: 1.7rem;

    font-weight: 700;

    margin-bottom: 0.6rem;
}

.upload-sub {

    color: var(--text-muted);

    margin-bottom: 2rem;
}

/* FILE UPLOADER */

[data-testid="stFileUploader"] {

    border: 1px dashed rgba(255,255,255,0.10);

    border-radius: 20px;

    padding: 1rem;

    background: rgba(255,255,255,0.03);
}

/* =========================================================
BUTTONS
========================================================= */

.stButton > button {

    width: 100%;

    border: none;

    border-radius: 999px;

    padding: 0.85rem 1.5rem;

    font-size: 1rem;

    font-weight: 600;

    color: white;

    background:
        linear-gradient(
            135deg,
            #8B5CF6,
            #6366F1
        );

    transition: all 0.3s ease;

    box-shadow:
        0 10px 35px rgba(99,102,241,0.35);
}

.stButton > button:hover {

    transform: translateY(-2px);

    box-shadow:
        0 15px 40px rgba(99,102,241,0.45);
}

/* =========================================================
TABS
========================================================= */

.stTabs [data-baseweb="tab-list"] {

    gap: 12px;

    background: rgba(255,255,255,0.03);

    padding: 0.7rem;

    border-radius: 20px;

    border: 1px solid rgba(255,255,255,0.06);
}

.stTabs [data-baseweb="tab"] {

    height: 52px;

    border-radius: 14px;

    padding-left: 24px;
    padding-right: 24px;

    color: var(--text-secondary);

    transition: 0.25s ease;
}

.stTabs [aria-selected="true"] {

    background:
        linear-gradient(
            135deg,
            rgba(139,92,246,0.18),
            rgba(99,102,241,0.18)
        ) !important;

    color: white !important;

    border: 1px solid rgba(255,255,255,0.08);
}

/* =========================================================
FLASHCARD
========================================================= */

.flashcard {

    position: relative;

    padding: 4rem 3rem;

    border-radius: 32px;

    overflow: hidden;

    background:
        linear-gradient(
            145deg,
            rgba(17,24,39,0.95),
            rgba(15,23,42,0.95)
        );

    border: 1px solid rgba(255,255,255,0.07);

    min-height: 430px;

    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}

.flashcard::before {

    content: "";

    position: absolute;

    width: 400px;
    height: 400px;

    background:
        radial-gradient(
            rgba(99,102,241,0.20),
            transparent 70%
        );

    top: -100px;
    right: -100px;
}

.flash-title {

    color: #F59E0B;

    font-size: 1.2rem;

    font-weight: 600;

    margin-bottom: 2rem;
}

.flash-content {

    font-size: 2.2rem;

    line-height: 1.5;

    text-align: center;

    max-width: 850px;

    font-weight: 600;
}

/* =========================================================
PROGRESS
========================================================= */

.progress-wrap {
    margin-top: 2rem;
}

.progress-top {

    display: flex;
    justify-content: space-between;

    margin-bottom: 0.8rem;

    color: var(--text-secondary);
}

.progress-bar {

    height: 10px;

    background: rgba(255,255,255,0.06);

    border-radius: 999px;

    overflow: hidden;
}

.progress-fill {

    width: 35%;
    height: 100%;

    border-radius: 999px;

    background:
        linear-gradient(
            90deg,
            #8B5CF6,
            #6366F1
        );
}

/* =========================================================
CHAT
========================================================= */

.chat-card {

    padding: 1.4rem;

    border-radius: 22px;

    background: rgba(255,255,255,0.04);

    border: 1px solid rgba(255,255,255,0.06);

    margin-bottom: 1rem;
}

.chat-user {

    font-weight: 700;

    margin-bottom: 0.5rem;
}

.chat-msg {

    color: var(--text-secondary);

    line-height: 1.7;
}

/* =========================================================
QUIZ
========================================================= */

.quiz-option {

    padding: 1rem 1.2rem;

    border-radius: 16px;

    margin-bottom: 1rem;

    background: rgba(255,255,255,0.03);

    border: 1px solid rgba(255,255,255,0.05);

    transition: 0.25s ease;
}

.quiz-option:hover {

    background: rgba(99,102,241,0.12);

    transform: translateX(4px);
}

/* =========================================================
NOTES
========================================================= */

.notes-card {

    padding: 2rem;

    border-radius: 24px;

    background: rgba(255,255,255,0.04);

    border: 1px solid rgba(255,255,255,0.06);

    line-height: 1.9;
}

/* =========================================================
ANIMATIONS
========================================================= */

@keyframes float {

    0% {
        transform: translateY(0px);
    }

    50% {
        transform: translateY(-10px);
    }

    100% {
        transform: translateY(0px);
    }
}

</style>
"""

st.markdown(css, unsafe_allow_html=True)

# =========================================================
# NAVBAR
# =========================================================

navbar = """
<div class="navbar">

    <div class="logo-wrap">
        <div class="logo-icon">🦉</div>
        <div class="logo-text">NightOwl 2.0</div>
    </div>

    <div class="nav-right">
        <div class="nav-pill">🔥 14 Day Streak</div>
        <div class="nav-pill">✨ AI Study Mode</div>
    </div>

</div>
"""

st.markdown(navbar, unsafe_allow_html=True)

# =========================================================
# HERO
# =========================================================

hero = """
<div class="hero">

    <div class="hero-title">
        Study Smarter.<br>
        Not Harder.
    </div>

    <div class="hero-sub">
        Upload your notes and instantly generate flashcards,
        quizzes, notes & AI-powered explanations.
    </div>

</div>
"""

st.markdown(hero, unsafe_allow_html=True)

# =========================================================
# UPLOAD SECTION
# =========================================================

upload_ui = """
<div class="glass-card upload-wrapper">

    <div class="upload-icon">📚</div>

    <div class="upload-title">
        Upload Your Study Material
    </div>

    <div class="upload-sub">
        Drag & drop PDFs to generate AI-powered study content
    </div>

</div>
"""

st.markdown(upload_ui, unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Upload PDF",
    type=["pdf"],
    label_visibility="collapsed"
)

st.markdown("<br>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1,1,1])

with col2:
    st.button("✨ Generate Study Material")

st.markdown("<br><br>", unsafe_allow_html=True)

# =========================================================
# TABS
# =========================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "💬 Chat",
    "🧠 Flashcards",
    "❓ Quiz",
    "📝 Notes"
])

# =========================================================
# CHAT TAB
# =========================================================

with tab1:

    st.markdown("<br>", unsafe_allow_html=True)

    user_chat = """
    <div class="chat-card">

        <div class="chat-user">
            You
        </div>

        <div class="chat-msg">
            Explain race conditions in Java.
        </div>

    </div>
    """

    ai_chat = """
    <div class="chat-card">

        <div class="chat-user">
            NightOwl AI
        </div>

        <div class="chat-msg">
            A race condition occurs when multiple threads
            access shared data simultaneously and the final
            result depends on execution timing.
        </div>

    </div>
    """

    st.markdown(user_chat, unsafe_allow_html=True)
    st.markdown(ai_chat, unsafe_allow_html=True)

    st.text_input(
        "",
        placeholder="Ask doubts or explain concepts..."
    )

# =========================================================
# FLASHCARD TAB
# =========================================================

with tab2:

    st.markdown("<br>", unsafe_allow_html=True)

    flashcard = """
    <div class="flashcard">

        <div class="flash-title">
            ✨ Flashcard Answer
        </div>

        <div class="flash-content">
            When two threads access shared data and the
            final outcome depends on timing.
        </div>

    </div>
    """

    st.markdown(flashcard, unsafe_allow_html=True)

    progress = """
    <div class="progress-wrap">

        <div class="progress-top">
            <span>Card 3 of 10</span>
            <span>Shuffle</span>
        </div>

        <div class="progress-bar">
            <div class="progress-fill"></div>
        </div>

    </div>
    """

    st.markdown(progress, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1,1,1])

    with c1:
        st.button("⬅ Previous")

    with c2:
        st.button("🔓 Reveal Answer")

    with c3:
        st.button("Next ➜")

# =========================================================
# QUIZ TAB
# =========================================================

with tab3:

    st.markdown("<br>", unsafe_allow_html=True)

    quiz = """
    <div class="glass-card" style="padding:2rem;">

        <h2>What is a race condition?</h2>

        <br>

        <div class="quiz-option">
            A condition where threads execute sequentially
        </div>

        <div class="quiz-option">
            A timing-dependent issue in multithreading
        </div>

        <div class="quiz-option">
            A Java compiler error
        </div>

        <div class="quiz-option">
            A database deadlock
        </div>

    </div>
    """

    st.markdown(quiz, unsafe_allow_html=True)

# =========================================================
# NOTES TAB
# =========================================================

with tab4:

    st.markdown("<br>", unsafe_allow_html=True)

    notes = """
    <div class="notes-card">

        <h2>Race Conditions</h2>

        <p>
        A race condition occurs when multiple threads
        access shared resources simultaneously and the
        final outcome depends on execution order.
        </p>

        <p>
        Race conditions can lead to inconsistent data,
        unexpected behavior, and synchronization issues.
        </p>

        <ul>
            <li>Synchronization</li>
            <li>Locks & Mutexes</li>
            <li>Atomic variables</li>
            <li>Thread-safe collections</li>
        </ul>

    </div>
    """

    st.markdown(notes, unsafe_allow_html=True)