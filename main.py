"""
FastAPI backend for the ShopSphere support assistant.

This is a thin HTTP wrapper around src/pipeline.py - all routing, RAG,
SQL-tool, and LLM logic is unchanged from the Streamlit version. Only the
interface changes: a React frontend now calls this instead of Streamlit
rendering directly in-process.

Run with:
    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.pipeline import handle_query

app = FastAPI(title="ShopSphere Support Assistant API")

# The React dev server runs on a different origin (localhost:5173), so it
# needs CORS access to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    query: str


class Source(BaseModel):
    source: str
    distance: float


class ChatResponse(BaseModel):
    answer: str
    route: str
    sources: list[Source]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    result = handle_query(request.query)
    return {
        "answer": result["answer"],
        "route": result["route"],
        "sources": result["sources"],
    }
