"""
NightOwl 2.0 — Python Flask API
Drop-in replacement for server.ts
Matches ALL endpoints and response formats exactly so React frontend works unchanged.

Run: python api.py
Runs on: http://localhost:5000
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os, base64, tempfile, json, sys

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


# ══════════════════════════════════════════════════════════════
# 2. PARSE DOCUMENT  (replaces Gemini inline PDF parsing)
#    Receives: { fileName, mimeType, fileData (base64), textContent }
#    Returns:  { title, parsedContent, charCount, wordCount }
# ══════════════════════════════════════════════════════════════
@app.route("/parse-document", methods=["POST"])
def parse_document():
    data      = request.json or {}
    file_name = data.get("fileName", "Untitled")
    file_data = data.get("fileData")       # base64 string
    text_cont = data.get("textContent")

    if not file_data and not text_cont:
        return jsonify({"error": "Missing document data"}), 400

    try:
        if file_data:
            # Decode base64 PDF → temp file → PyPDFLoader
            raw_bytes = base64.b64decode(file_data)
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(raw_bytes)
                tmp_path = tmp.name

            from langchain_community.document_loaders import PyPDFLoader
            pages   = PyPDFLoader(tmp_path).load()
            parsed  = "\n\n".join(p.page_content for p in pages)
            os.unlink(tmp_path)

            # Also build knowledge base for RAG (stored by filename key)
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp2:
                tmp2.write(raw_bytes)
                tmp2_path = tmp2.name
            session_id = file_name.replace(" ", "_")
            knowledge_bases[session_id] = build_knowledge_base(tmp2_path)
            os.unlink(tmp2_path)
        else:
            parsed = text_cont

        return jsonify({
            "title":         file_name,
            "parsedContent": parsed,
            "charCount":     len(parsed),
            "wordCount":     len(parsed.split()),
            "sessionId":     file_name.replace(" ", "_")   # bonus: send back for RAG
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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

    try:
        # Use RAG collection if available
        if session and session in knowledge_bases:
            cards = gen_flashcards_core(knowledge_bases[session], num_cards=count)
            # Add category field to match expected format
            for c in cards:
                c.setdefault("category", "Active Recall")
            return jsonify({"flashcards": cards})

        # Fallback: use contextText directly
        system = """You are a flashcard generator. Return ONLY a valid JSON array.
Each item: {"question": "...", "answer": "...", "category": "..."}
Make questions test understanding. Keep answers concise. No extra text."""
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
        system = """You are a quiz generator. Return ONLY a valid JSON array.
Each item must have EXACTLY:
{
  "question": "...",
  "options": ["option1","option2","option3","option4"],
  "correctAnswerIdx": 0,
  "explanation": "..."
}
correctAnswerIdx is 0-3. No extra text, no markdown."""
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

        system = """You are a note generator. Return ONLY a valid JSON object:
{
  "title": "...",
  "summary": "2-3 sentence executive summary",
  "keyTakeaways": ["point1", "point2", "point3", "point4", "point5"],
  "content": "full markdown notes here"
}
No extra text outside JSON."""
        user = f"Create study notes from:\n\n{context[:4000]}"
        notes = groq_json(system, user, {
            "title": "Study Notes",
            "summary": "Notes generated from your document.",
            "keyTakeaways": [],
            "content": context[:1000]
        })
        return jsonify({"notes": notes})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("🦉 NightOwl 2.0 Python API starting...")
    app.run(host="0.0.0.0", port=port, debug=False)
