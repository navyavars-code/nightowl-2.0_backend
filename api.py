"""
NightOwl 2.0 — Python Flask API
Drop-in replacement for server.ts
Matches ALL endpoints and response formats exactly so React frontend works unchanged.

Run: python api.py
Runs on: http://localhost:5000
"""
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os, base64, tempfile, json, sys,threading

load_dotenv()
sys.path.append(os.path.dirname(__file__))

from backend.core import (
    build_knowledge_base,
    ask_question,
    generate_flashcards as gen_flashcards_core,
    generate_quiz     as gen_quiz_core,
    generate_notes    as gen_notes_core,
)
from groq import Groq

app   = Flask(__name__)
CORS(app)  # Allow React (port 3000) to call this API (port 5000)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB limit
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# In-memory store: session_id → ChromaDB collection
knowledge_bases: dict = {}
# Track processing status per session
processing_status: dict = {}


# ── Helper: call Groq and parse JSON safely ─────────────────
def groq_json(system: str, user: str, fallback) -> any:
    resp = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system",  "content": system},
            {"role": "user",    "content": user},
        ]
    )
    raw = resp.choices[0].message.content.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        raw = raw.rsplit("```", 1)[0].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


# ══════════════════════════════════════════════════════════════
# 1. HEALTH CHECK
# ══════════════════════════════════════════════════════════════
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "geminiConfigured": False,
        "groqConfigured": bool(os.getenv("GROQ_API_KEY")),
        "timestamp": __import__("datetime").datetime.utcnow().isoformat()
    })
def process_pdf_background(tmp_path, session_id):
    try:
        processing_status[session_id] = "processing"
        collection = build_knowledge_base(tmp_path)
        knowledge_bases[session_id] = collection
        processing_status[session_id] = "done"
    except Exception as e:
        processing_status[session_id] = f"error: {str(e)}"
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

# ══════════════════════════════════════════════════════════════
# 2. PARSE DOCUMENT  (replaces Gemini inline PDF parsing)
#    Receives: { fileName, mimeType, fileData (base64), textContent }
#    Returns:  { title, parsedContent, charCount, wordCount }
# ══════════════════════════════════════════════════════════════
@app.route("/parse-document", methods=["POST"])
def parse_document():
    data = request.json or {}
    file_name = data.get("fileName", "Untitled")
    file_data = data.get("fileData")
    text_cont = data.get("textContent")

    if not file_data and not text_cont:
        return jsonify({"error": "Missing document data"}), 400

    session_id = file_name.replace(" ", "_")

    try:
        if file_data:
            raw_bytes = base64.b64decode(file_data)
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(raw_bytes)
                tmp_path = tmp.name

            # Quick preview text using PyPDFLoader (fast, just first few pages)
            from langchain_community.document_loaders import PyPDFLoader
            pages = PyPDFLoader(tmp_path).load()
            preview = "\n\n".join(p.page_content for p in pages[:3])

            # Start heavy processing in background
            thread = threading.Thread(target=process_pdf_background, args=(tmp_path, session_id))
            thread.start()

            return jsonify({
                "title": file_name,
                "parsedContent": preview,
                "charCount": len(preview),
                "wordCount": len(preview.split()),
                "sessionId": session_id,
                "processing": True
            })
        else:
            return jsonify({
                "title": file_name,
                "parsedContent": text_cont,
                "charCount": len(text_cont),
                "wordCount": len(text_cont.split()),
                "sessionId": session_id,
                "processing": False
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/status/<session_id>", methods=["GET"])
def check_status(session_id):
    status = processing_status.get(session_id, "unknown")
    return jsonify({"status": status})


# ══════════════════════════════════════════════════════════════
# 3. CHAT  (replaces Gemini "Professor Hoot" chat)
#    Receives: { messages: [{role, content}], documentContext }
#    Returns:  { role: "assistant", content }
# ══════════════════════════════════════════════════════════════

@app.route("/chat", methods=["POST"])
def chat():
    data     = request.json or {}
    messages = data.get("messages", [])
    context  = data.get("documentContext", "")
    session  = data.get("sessionId", "")
    if session and processing_status.get(session) == "processing":
        return jsonify({"error": "Still processing your document, please wait a moment..."}), 202
    if not messages:
        return jsonify({"error": "Messages array is required"}), 400

    try:
        # If we have a RAG collection, use semantic search for richer context
        if session and session in knowledge_bases:
            last_q  = messages[-1]["content"] if messages else ""
            answer  = ask_question(last_q, knowledge_bases[session])
            return jsonify({"role": "assistant", "content": answer})

        # Fallback: use raw document context + Groq
        system = """You are "Professor Hoot", a brilliant, supportive, and engaging late-night study assistant for NightOwl 2.0.
- Use markdown (bold, bullets, headers) to structure answers beautifully.
- If document context is provided, prioritize it for factual answers.
- If the answer is NOT in the document, answer from general knowledge and note it.
- Be encouraging, clear, and student-friendly."""

        history = []
        if context:
            history.append({
                "role": "user",
                "content": f"Document context:\n{context[:3000]}\n\nUse this as reference for my questions."
            })
            history.append({"role": "assistant", "content": "Got it! I've read your notes. Ask me anything 🦉"})

        for m in messages:
            history.append({"role": m["role"], "content": m["content"]})

        resp = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system}] + history
        )
        return jsonify({
            "role":    "assistant",
            "content": resp.choices[0].message.content
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════
# 4. FLASHCARDS
#    Receives: { contextText, topicDescription, count }
#    Returns:  { flashcards: [{question, answer, category}] }
# ══════════════════════════════════════════════════════════════

@app.route("/generate-flashcards", methods=["POST"])
def generate_flashcards():
    data    = request.json or {}
    context = data.get("contextText", data.get("topicDescription", ""))
    count   = data.get("count", 10)
    session = data.get("sessionId", "")
    if session and processing_status.get(session) == "processing":
        return jsonify({"error": "Still processing your document, please wait a moment..."}), 202
    try:
        # Use RAG collection if available
        if session and session in knowledge_bases:
            cards = gen_flashcards_core(knowledge_bases[session], num_cards=count)
            # Add category field to match expected format
            for c in cards:
                c.setdefault("category", "Active Recall")
            return jsonify({"flashcards": cards})

        # Fallback: use contextText directly
        system = """You are an expert professor creating exam-level flashcards for college students.
        Return ONLY a valid JSON array. Each item: {"question": "...", "answer": "...", "category": "..."}

        Rules:
        - AVOID basic "What is X?" questions unless X is foundational.
        - PREFER questions on comparisons, mechanisms, trade-offs, applications, and reasoning ("why"/"how").
        - Answers must be 2-4 sentences with real explanation, not one-liners.
        - No extra text outside the JSON array."""
        user = f"Generate {count} flashcards from:\n\n{context[:4000]}"
        cards = groq_json(system, user, [])
        if not isinstance(cards, list):
            cards = []
        return jsonify({"flashcards": cards})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════
# 5. QUIZ
#    Receives: { contextText, topicDescription, count }
#    Returns:  { quizzes: [{question, options, correctAnswerIdx, explanation}] }
# ══════════════════════════════════════════════════════════════
@app.route("/generate-quiz", methods=["POST"])
def generate_quiz():
    data    = request.json or {}
    context = data.get("contextText", data.get("topicDescription", ""))
    count   = data.get("count", 5)
    session = data.get("sessionId", "")
    if session and processing_status.get(session) == "processing":
        return jsonify({"error": "Still processing your document, please wait a moment..."}), 202
    try:
        if session and session in knowledge_bases:
            qs = gen_quiz_core(knowledge_bases[session], num_questions=count)
            # Convert our format to React's expected format
            quizzes = []
            for q in qs:
                opts = list(q["options"].values())  # ["opt A text", "opt B text", ...]
                correct_letter = q["answer"]        # "A", "B", "C", or "D"
                correct_idx    = ["A","B","C","D"].index(correct_letter) if correct_letter in "ABCD" else 0
                quizzes.append({
                    "question":        q["question"],
                    "options":         opts,
                    "correctAnswerIdx": correct_idx,
                    "explanation":     q.get("explanation", "")
                })
            return jsonify({"quizzes": quizzes})

        # Fallback: contextText directly
        system = """You are an expert professor creating exam-level MCQs for college engineering students.
        Return ONLY a valid JSON array. Each item must have EXACTLY:
        {
          "question": "...",
          "options": ["option1","option2","option3","option4"],
          "correctAnswerIdx": 0,
          "explanation": "..."
        }

        Rules:
        - AVOID basic "What is X?" questions unless foundational.
        - PREFER application, comparison, mechanism, and trade-off questions.
        - Distractor options must be plausible (common misconceptions), not obviously wrong.
        - explanation: 2-3 sentences covering why the answer is correct and why a distractor is tempting.
        - correctAnswerIdx is 0-3. No extra text, no markdown."""
        user = f"Generate {count} MCQ questions from:\n\n{context[:4000]}"
        quizzes = groq_json(system, user, [])
        if not isinstance(quizzes, list):
            quizzes = []
        return jsonify({"quizzes": quizzes})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════
# 6. NOTES
#    Receives: { contextText, topicDescription }
#    Returns:  { notes: {title, summary, keyTakeaways, content} }
# ══════════════════════════════════════════════════════════════
@app.route("/generate-notes", methods=["POST"])
def generate_notes():
    data    = request.json or {}
    context = data.get("contextText", data.get("topicDescription", ""))
    session = data.get("sessionId", "")
    if session and processing_status.get(session) == "processing":
        return jsonify({"error": "Still processing your document, please wait a moment..."}), 202
    try:
        if session and session in knowledge_bases:
            raw_notes = gen_notes_core(knowledge_bases[session])
            # Wrap in the format React expects
            return jsonify({"notes": {
                "title":        "Smart Study Notes",
                "summary":      raw_notes[:300] + "...",
                "keyTakeaways": [line.strip("- ") for line in raw_notes.split("\n") if line.startswith("- ")][:5],
                "content":      raw_notes
            }})

        # Generate markdown notes directly (more reliable than forcing JSON for long content)
        resp = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system",
                 "content": "You are a study notes generator. Summarize the given content into concise, well-organized markdown notes with headers, bullet points, and key concepts. Do NOT just repeat the original text — actively summarize and explain."},
                {"role": "user", "content": f"Create summarized study notes from this content:\n\n{context[:4000]}"}
            ]
        )
        content_md = resp.choices[0].message.content

        # Generate a short title + summary + takeaways from the same content
        meta_system = """Return ONLY valid JSON: {"title": "...", "summary": "2-3 sentence summary", "keyTakeaways": ["point1","point2","point3","point4","point5"]}"""
        meta = groq_json(meta_system, f"Based on this content, generate title/summary/takeaways:\n\n{context[:2000]}", {
            "title": "Study Notes",
            "summary": "AI-generated summary of your document.",
            "keyTakeaways": []
        })

        return jsonify({"notes": {
            "title": meta.get("title", "Study Notes"),
            "summary": meta.get("summary", ""),
            "keyTakeaways": meta.get("keyTakeaways", []),
            "content": content_md
        }})
    except Exception as e:
        traceback.print_exc()  # prints full error to Render logs
        return jsonify({"error": str(e)}), 500

# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("🦉 NightOwl 2.0 Python API starting...")
    app.run(host="0.0.0.0", port=port, debug=False)
