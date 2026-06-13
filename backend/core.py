from dotenv import load_dotenv
import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb
from groq import Groq

load_dotenv()
from fastembed import TextEmbedding

_fastembed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

class FastEmbedWrapper:
    def embed_query(self, text):
        return list(_fastembed_model.embed([text]))[0].tolist()
    def embed_documents(self, texts):
        return [e.tolist() for e in _fastembed_model.embed(texts)]

embeddings = FastEmbedWrapper()
# Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def build_knowledge_base(file_path):
    print("📄 Loading PDF...")
    loader = PyPDFLoader(file_path)
    pages = loader.load()

    print("✂️ Splitting into chunks...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(pages)
    print(f"✅ {len(chunks)} chunks created")

    print("💾 Storing in ChromaDB...")
    chroma_client = chromadb.Client()
    collection = chroma_client.create_collection("study_buddy")

    for i, chunk in enumerate(chunks):
        embedding = embeddings.embed_query(chunk.page_content)
        collection.add(
            documents=[chunk.page_content],
            embeddings=[embedding],
            ids=[f"chunk_{i}"]
        )

    print("✅ Knowledge base ready!")
    return collection

def ask_question(question, collection):
    # Search relevant chunks locally
    question_embedding = embeddings.embed_query(question)
    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=2
    )
    context = "\n\n".join(results["documents"][0])

    # Groq answers the question
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": """You are a smart and friendly study assistant helping a student understand their subject.

You have access to the student's notes (provided as context). Follow these rules:
1. If the answer is clearly in the context → answer from it and add: "📄 Source: Your Notes"
2. If the answer is NOT in the context → answer from your general knowledge and add: "🌐 Source: General Knowledge (not in your notes)"
3. If it's partially in the notes → answer fully and mention both sources
4. Always explain in simple, student-friendly language"""},
            {"role": "user", "content": f"My Notes Context:\n{context}\n\nMy Question: {question}"}
        ]
    )
    return response.choices[0].message.content


def generate_flashcards(collection, num_cards=10):
    print("\n⚡ Generating flashcards from your notes...")

    # Get all stored chunks from ChromaDB
    all_data = collection.get()
    all_chunks = all_data["documents"]

    # Pick evenly spaced chunks to cover whole document
    step = max(1, len(all_chunks) // num_cards)
    selected_chunks = all_chunks[::step][:num_cards]
    combined_text = "\n\n".join(selected_chunks)

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": """You are a study assistant that creates flashcards.
Generate exactly 10 flashcards from the provided text.
Format each flashcard EXACTLY like this:
Q: [question]
A: [answer]
---
Make questions test understanding, not just memory.
Keep answers concise and clear."""},
            {"role": "user", "content": f"Create 10 flashcards from this text:\n\n{combined_text}"}
        ]
    )

    # Parse the response into a list of flashcards
    raw = response.choices[0].message.content
    cards = []
    for block in raw.split("---"):
        block = block.strip()
        if "Q:" in block and "A:" in block:
            lines = block.split("\n")
            question = ""
            answer = ""
            for line in lines:
                if line.startswith("Q:"):
                    question = line[2:].strip()
                elif line.startswith("A:"):
                    answer = line[2:].strip()
            if question and answer:
                cards.append({"question": question, "answer": answer})

    return cards

def generate_quiz(collection, num_questions=10):
    print("\n📝 Generating full topic quiz...")

    all_data = collection.get()
    all_chunks = all_data["documents"]

    if len(all_chunks) <= num_questions:
        selected_chunks = all_chunks
    else:
        group_size = max(1, len(all_chunks) // num_questions)
        selected_chunks = []
        for i in range(0, len(all_chunks), group_size):
            group = all_chunks[i:i + group_size]
            selected_chunks.append(group[len(group) // 2])
            if len(selected_chunks) == num_questions:
                break

    combined_text = "\n\n".join(selected_chunks)

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": """You are a quiz generator. Return ONLY a valid JSON array. No extra text, no markdown, no explanation.
Format:
[
  {
    "question": "question text",
    "options": {"A": "option1", "B": "option2", "C": "option3", "D": "option4"},
    "answer": "A",
    "explanation": "one line explanation"
  }
]"""},
            {"role": "user", "content": f"Generate 10 unique MCQ questions covering different concepts from this text. Return ONLY JSON:\n\n{combined_text}"}
        ]
    )

    import json
    import re
    raw = response.choices[0].message.content.strip()

    # Clean markdown code blocks if present
    raw = re.sub(r'^```(?:json)?', '', raw).strip()
    raw = re.sub(r'```$', '', raw).strip()

    try:
        questions = json.loads(raw)
        # Validate each question has required fields
        valid = []
        seen_questions = set()  # prevent duplicate questions
        for q in questions:
            if all(k in q for k in ["question", "options", "answer"]):
                if q["question"] not in seen_questions:
                    seen_questions.add(q["question"])
                    valid.append(q)
        print(f"✅ Parsed {len(valid)} questions!")
        return valid
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse error: {e}")
        print("Raw output was:", raw[:500])
        return []

def generate_notes(collection):
    print("\n📋 Generating short notes from your PDF...")

    all_data = collection.get()
    all_chunks = all_data["documents"]

    # Pick evenly spread chunks to cover whole document
    step = max(1, len(all_chunks) // 10)
    selected_chunks = all_chunks[::step][:10]
    combined_text = "\n\n".join(selected_chunks)

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": """You are a smart note-maker for students.
Create concise, well-structured short notes from the provided text.
Format your response EXACTLY like this:

## 📌 Topic: [main topic name]

### 🔑 Key Concepts:
- [concept 1]: [one line explanation]
- [concept 2]: [one line explanation]
- [concept 3]: [one line explanation]

### 📖 Important Points:
- [point 1]
- [point 2]
- [point 3]

### ⚡ Quick Facts:
- [fact 1]
- [fact 2]
- [fact 3]

### 🧠 Remember:
[2-3 line summary of the most important thing to remember]

Keep everything concise — a student should be able to read this in 2 minutes."""},
            {"role": "user", "content": f"Create short notes from this text:\n\n{combined_text}"}
        ]
    )

    return response.choices[0].message.content

if __name__ == "__main__":
    collection = build_knowledge_base("test.pdf")

    while True:
        print("\n" + "="*50)
        print("📚 NightOwl 2.0 — What would you like to do?")
        print("="*50)
        print("1. 💬 Chat with your notes")
        print("2. 🃏 Generate flashcards")
        print("3. 📝 Take full topic quiz")
        print("4. 📋 Generate short notes")
        print("5. 🚪 Exit")

        choice = input("\nEnter choice (1-5): ").strip()

        if choice == "1":
            print("\n🤖 Study Buddy ready! Type 'quit' to go back\n")
            while True:
                question = input("You: ")
                if question.lower() == "quit":
                    break
                answer = ask_question(question, collection)
                print(f"\n🤖 Study Buddy: {answer}\n")

        elif choice == "2":
            flashcards = generate_flashcards(collection)
            print(f"\n🃏 Generated {len(flashcards)} Flashcards!\n")
            for i, card in enumerate(flashcards, 1):
                print(f"\n📌 Card {i}/{len(flashcards)}: {card['question']}")
                input("   Press Enter to reveal answer...")
                print(f"   ✅ {card['answer']}")
                print("-" * 40)
            print("\n🎉 Flashcards complete!")

        elif choice == "3":
            print("\n" + "="*50)
            print("📝 FULL TOPIC KNOWLEDGE TEST")
            print("="*50)
            print("Answer all questions then see your final score.")
            input("Press Enter when ready...")

            questions = generate_quiz(collection)

            if not questions:
                print("❌ Could not generate quiz. Try again.")
                continue

            print(f"\n🚀 Starting! {len(questions)} questions\n")
            score = 0
            wrong_questions = []

            for i, q in enumerate(questions, 1):
                print(f"\n{'─'*40}")
                print(f"Question {i}/{len(questions)}")
                print(f"\n{q['question']}")
                for key, val in q["options"].items():
                    print(f"   {key}) {val}")
                user_ans = input("\nYour answer (A/B/C/D): ").upper().strip()
                if user_ans == q["answer"]:
                    print("✅ Correct!")
                    score += 1
                else:
                    print(f"❌ Wrong!")
                    wrong_questions.append(q)

            print(f"\n{'='*50}")
            print(f"🏆 FINAL SCORE: {score}/{len(questions)}")
            percentage = (score / len(questions)) * 100
            print(f"📊 Percentage: {percentage:.0f}%")

            if percentage >= 80:
                print("🌟 Excellent! You've mastered this topic!")
            elif percentage >= 60:
                print("👍 Good job! Review the topics you missed.")
            elif percentage >= 40:
                print("📚 Keep studying! You're getting there.")
            else:
                print("💪 Don't give up! Re-read your notes and try again.")

            if wrong_questions:
                print(f"\n📖 Review — Questions You Got Wrong:\n")
                for i, q in enumerate(wrong_questions, 1):
                    print(f"{i}. {q['question']}")
                    print(f"   ✅ Correct Answer: {q['answer']}) {q['options'].get(q['answer'], '')}")
                    if q.get('explanation'):
                        print(f"   💡 Why: {q['explanation']}")

        elif choice == "4":
            notes = generate_notes(collection)
            print("\n" + "="*50)
            print(notes)
            print("="*50)

        elif choice == "5":
            print("\n👋 Goodbye! Keep studying!")
            break

        else:
            print("❌ Invalid choice. Enter 1-5.")