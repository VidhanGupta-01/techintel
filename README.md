# TechIntel — Technology Intelligence Dashboard

A full-stack dashboard that tracks patent and publication activity across emerging tech sectors (Quantum Computing, Generative AI, Drone Swarms, Advanced Materials, Cybersecurity), and generates AI-written strategic briefings grounded in that data.

## Tech stack

- **Backend:** FastAPI + SQLAlchemy + SQLite
- **Frontend:** React 19 + Vite + Recharts
- **AI:** OpenAI API (`gpt-4o-mini` for generation, `text-embedding-3-small` for semantic search)
- **Deployment:** Azure App Service (backend) + Azure Static Web Apps (frontend)

## Features

- **Overview stats** — aggregate patent/publication counts, average Technology Readiness Level (TRL), active sectors
- **Keyword search** — exact-match search across titles and categories
- **Semantic search** — meaning-based search using embeddings + cosine similarity, for queries that share no keywords with the source text (e.g. "AI safety risk" matching an abstract about "mitigating unintended model behavior")
- **AI-generated strategic briefings** — an LLM writes a structured `{headline, maturity, recommendation}` analysis grounded in the actual filtered data, not free-form guessing

## Architecture decisions

**Why direct prompt grounding instead of RAG with chunking.** The source data here is structured SQL rows (patent title, abstract, TRL, category), not large unstructured documents. Chunking exists to split oversized text so it fits a model's context window and to make retrieval more precise — neither problem applies here, since a SQL `ILIKE` filter is already exact, cheap retrieval, and the resulting rows are small enough to paste directly into a prompt. Adding a vector database and chunking pipeline here would be complexity with no matching problem to solve.

**Where embeddings do earn their place: semantic search.** Keyword search has a real blind spot — it can't match related *meaning* without shared words. Since abstracts are short (no chunking needed) and the dataset is small (~450 rows), embeddings are computed once offline (`embed_data.py`) and cached to a JSON file, rather than requiring a dedicated vector database.

**Structured output over free text.** `/api/generate-insight` prompts the model with a concrete JSON example (few-shot) and validates the shape of what comes back, so the frontend can render distinct sections instead of parsing a prose blob.

**Graceful degradation.** If the API key is missing, the call fails, or the model returns malformed JSON, the endpoint falls back to a deterministic rule-based summary rather than erroring out. The response includes a `source` field (`openai` / `fallback` / `no_data`) so failures are visible rather than silent.

## API endpoints

| Endpoint | Description |
|---|---|
| `GET /api/overview` | Aggregate stats across all data |
| `GET /api/search?q=` | Exact keyword search |
| `GET /api/semantic-search?q=&top_k=` | Meaning-based search via embeddings |
| `GET /api/generate-insight?q=` | AI-generated structured briefing |
| `GET /api/scurve` | Mock technology adoption curve data |
| `GET /api/patents?limit=` | List patents |

## Setup

### Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # then add your OPENAI_API_KEY
python data_gen.py     # seeds the database with mock data
python embed_data.py   # builds the semantic search index (needs a funded API key)
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Evaluation

`eval_insight.py` runs a fixed set of known queries against the live server and checks:
1. The response has the expected structure (`headline`, `maturity`, `recommendation`)
2. Whether the response actually came from the model or silently fell back (`source` field) — this catches a failure mode that looks fine at a glance but isn't
3. Whether ground-truth numbers from the database (e.g. patent count) actually appear in the generated text, as a basic groundedness/hallucination check

```bash
python eval_insight.py
```

## Known limitations / future work

- No caching yet — identical repeated queries re-hit the API rather than reusing a prior response
- The mock dataset (`data_gen.py`) generates synthetic patents/publications; this isn't connected to a real patent database
- The groundedness check in `eval_insight.py` is a simple heuristic (does the exact number appear in the text), not a rigorous hallucination detector

## A note on security

An earlier version of this project accidentally committed a `.env` file containing a live API key to this public repository. The key was revoked immediately upon discovery, and the file was removed from git tracking. `.env` is correctly listed in `.gitignore` going forward — the original issue was that the file had already been committed once before the ignore rule existed, and `.gitignore` cannot retroactively untrack a file already in git's history.
