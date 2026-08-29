# ShopSphere Support Assistant

Hybrid e-commerce support chatbot: semantic routing over policy (RAG),
order/product (SQL tools), hybrid, and small-talk queries, answered by
Llama 3.3-70B via Groq.

## Architecture

```
React (Vite, localhost:5173)
        |  fetch POST /chat
        v
FastAPI (localhost:8000)  ->  src/pipeline.py
                                  |
                  +---------------+----------------+
                  |               |                |
            src/router.py   src/rag.py        src/tools.py
          (semantic router)  (ChromaDB RAG)   (9 SQL tools, SQLite)
                                  |
                            src/llm.py  (Groq / Llama 3.3-70B)
```

`app.py` (Streamlit) is kept in the repo as a lightweight fallback UI -
both it and the React app call the exact same `src/pipeline.py`, so
nothing about the underlying logic changes between them.

## 1. Backend setup

```bash
pip install -r requirements.txt
cp .env.example .env      # then fill in GROQ_API_KEY
export GROQ_API_KEY=your_key_here   # or use a .env loader of your choice

# one-time setup if you haven't already built these locally:
python create_database.py
python build_rag.py

uvicorn main:app --reload --port 8000
```

Check it's up: `curl http://localhost:8000/health` -> `{"status": "ok"}`

## 2. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Open the printed URL (usually `http://localhost:5173`).

## 3. (Optional) Streamlit fallback

```bash
streamlit run app.py
```

## 4. Evaluation

```bash
python -m tests.run_eval
```

Routing and retrieval metrics run offline. Tool-selection and
end-to-end metrics require `GROQ_API_KEY` to be set (they call the LLM).
