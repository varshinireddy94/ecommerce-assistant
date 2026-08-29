# ShopSphere Support Assistant

A hybrid e-commerce customer support chatbot combining **semantic routing, RAG, controlled SQL tools, and LLM-based response generation** to handle policy, order, product, hybrid, and conversational queries.

The system uses **GPT-OSS-120B via Groq** for language understanding and response generation, **Sentence Transformers** for semantic routing and policy retrieval, **ChromaDB** for the policy knowledge base, and **SQLite** for structured e-commerce data.

---

## Architecture

```text
                              User
                               |
                               v
                         React + Vite
                               |
                         POST /chat
                               |
                               v
                         FastAPI Backend
                               |
                         src/pipeline.py
                               |
             +-----------------+-----------------+
             |                 |                 |
             v                 v                 v
       Semantic Router     Policy RAG        SQL Tools
             |                 |                 |
             |             ChromaDB          SQLite
             |                 |                 |
             +-----------------+-----------------+
                               |
                               v
                        GPT-OSS-120B
                           via Groq
                               |
                               v
                         Final Response
```

### Query Routing

```text
User Query
    |
    v
Semantic Router
    |
    +---- POLICY --------> ChromaDB RAG
    |
    +---- ORDER/PRODUCT -> Predefined SQL Tool
    |
    +---- HYBRID --------> SQL + RAG
    |
    +---- SMALL TALK ----> LLM
```

The LLM does **not execute arbitrary SQL**. It identifies the required operation and parameters, while the backend executes predefined, read-only, parameterized SQL tools.

---

## Key Features

### 🔀 Semantic Query Routing

Uses **Sentence Transformers (`all-MiniLM-L6-v2`)** to classify user queries into:

- Policy
- Order / Product
- Hybrid
- Small Talk

### 📚 Policy RAG

E-commerce policy documents are:

```text
Policy Documents
      ↓
Chunking
      ↓
Sentence Transformer Embeddings
      ↓
ChromaDB
      ↓
Top-k Relevant Policy Chunks
      ↓
GPT-OSS-120B
```

The retrieved context is used to generate grounded policy responses.

### 🗄️ Controlled SQL Tools

Provides predefined, read-only operations for common e-commerce queries such as:

- Order status
- Order items
- Order totals
- Delivery information
- Product details
- Product search
- Customer orders

SQL queries are **parameterized and predefined**, preventing unrestricted LLM-generated SQL execution.

### 🔗 Hybrid Reasoning

Handles queries that require both structured transaction data and unstructured policy knowledge.

Example:

> "Can I return the product from my order?"

The system can retrieve:

```text
Order / Product Information → SQLite
Return Policy              → ChromaDB
                              ↓
                         GPT-OSS-120B
                              ↓
                         Final Answer
```

### 🛡️ Controlled Database Access

Database access is restricted through:

- Predefined SQL operations
- Parameterized queries
- Read-only operations
- Input validation
- Restricted data returned to the LLM

### 💬 Conversational Interface

A **React + TypeScript** frontend communicates with the Python backend through FastAPI.

---

## Technology Stack

| Component | Technology |
|---|---|
| LLM | GPT-OSS-120B |
| LLM Provider | Groq |
| Embeddings | Sentence Transformers |
| Embedding Model | all-MiniLM-L6-v2 |
| Vector Database | ChromaDB |
| Structured Database | SQLite |
| Backend | FastAPI |
| Frontend | React + TypeScript + Vite |
| Styling | Tailwind CSS |
| Dataset | Olist Brazilian E-Commerce Dataset |

---

## Dataset

The structured database is built from the **Olist Brazilian E-Commerce Dataset**.

Current database contains:

- **99,441 orders**
- **112,650 order items**
- **32,951 products**
- **99,441 customers**
- **73 product categories**

### Database Schema

```text
customers
     |
     +---- orders
              |
              +---- order_items
                         |
                         +---- products
```

The unstructured knowledge base contains e-commerce policies covering:

```text
Cancellation
Returns
Refunds
Shipping
Warranty
```

---

## Project Structure

```text
ecommerce-assistant/
│
├── backend/
│   ├── src/
│   │   ├── router.py
│   │   ├── rag.py
│   │   ├── tools.py
│   │   ├── llm.py
│   │   └── pipeline.py
│   │
│   └── main.py
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── services/
│   │   └── App.tsx
│   ├── package.json
│   └── ...
│
├── data/
│   ├── ecommerce.db
│   └── chroma_db/
│
├── policies/
│   ├── cancellation/
│   ├── refunds/
│   ├── returns/
│   ├── shipping/
│   └── warranty/
│
├── scripts/
│   ├── create_database.py
│   ├── build_rag.py
│   ├── create_translation.py
│   ├── inspect_data.py
│   ├── check_categories.py
│   └── check_policy_corpus.py
│
├── tests/
│   ├── test_database.py
│   ├── test_tools.py
│   └── run_eval.py
│
├── .env.example
├── .gitignore
├── categories.txt
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd ecommerce-assistant
```

### 2. Install backend dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Groq API

Create a `.env` file:

```text
GROQ_API_KEY=your_api_key_here
```

### 4. Create the database

```bash
python scripts/create_database.py
```

### 5. Build the policy vector database

```bash
python scripts/build_rag.py
```

This creates the ChromaDB vector store from the policy corpus.

### 6. Start the FastAPI backend

```bash
uvicorn backend.main:app --reload --port 8000
```

Check the health endpoint:

```text
http://localhost:8000/health
```

Expected response:

```json
{"status": "ok"}
```

---

## Frontend Setup

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the URL displayed by Vite, usually:

```text
http://localhost:5173
```

---

## Example Queries

### Policy

```text
What is the return policy for electronics?
```

### Order

```text
Where is my order 53cdb2fc8bc7dce0b6741e2150273451?
```

### Product

```text
Show me products from the electronics category.
```

### Refund

```text
My refund has not arrived. What should I do?
```

### Hybrid

```text
Can I return the product from my order?
```

### Small Talk

```text
Hello, can you help me?
```

---

## Evaluation

The evaluation pipeline measures different components of the chatbot:

- Semantic routing accuracy
- Policy retrieval performance
- SQL tool selection
- Tool execution success
- End-to-end response behavior

Run:

```bash
python -m tests.run_eval
```

---

## Security Considerations

The chatbot does **not** provide the LLM with unrestricted database access.

The LLM only identifies the required operation and parameters. The backend then executes the corresponding predefined SQL tool.

All database operations use:

- Read-only SQL
- Parameterized queries
- Input validation
- Restricted tool access
- Limited data exposure

This prevents arbitrary SQL commands from being generated and executed against the database.

---

## Project Highlights

- Hybrid **RAG + SQL** customer-support architecture
- Semantic query routing using Sentence Transformers
- Policy retrieval using ChromaDB
- Controlled database access through predefined SQL tools
- Hybrid reasoning across structured and unstructured data
- **GPT-OSS-120B via Groq** for language understanding and response generation
- Production-style **React + FastAPI** architecture
- Evaluation of routing, retrieval, tool selection, and end-to-end performance
