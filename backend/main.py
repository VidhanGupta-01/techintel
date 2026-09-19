import os
import json

import numpy as np
from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_
from dotenv import load_dotenv
from openai import OpenAI

from database import SessionLocal, engine, Base
from models import Patent, Publication

load_dotenv()  # picks up OPENAI_API_KEY from a local .env file if present

app = FastAPI(title="DRDO Tech Intelligence API v2")

# Allow CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI client. Reads OPENAI_API_KEY from the environment automatically.
openai_client = OpenAI() if os.environ.get("OPENAI_API_KEY") else None
OPENAI_MODEL = "gpt-4o-mini"  # cheap + fast; swap to "gpt-4o" for higher quality
EMBED_MODEL = "text-embedding-3-small"

# Load precomputed embeddings (built offline by embed_data.py) if the file exists.
# We don't embed on every request -- that would be slow and wasteful. Instead we
# embed the DB once, cache it to disk, and only embed the user's live query at
# search time (one cheap call) to compare against the cache.
_EMBEDDINGS_CACHE = {"patents": {}, "publications": {}}
if os.path.exists("embeddings_cache.json"):
    with open("embeddings_cache.json") as f:
        _EMBEDDINGS_CACHE = json.load(f)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# Dependency to get the DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def read_root():
    return {"status": "ok", "message": "DRDO Technology Intelligence API v2 is running with SQLite."}


@app.get("/api/overview")
def get_overview(db: Session = Depends(get_db)):
    patents = db.query(Patent).all()
    pubs = db.query(Publication).all()

    total_patents = len(patents)
    avg_trl = sum(p.trl for p in patents) / max(total_patents, 1)

    # Get unique active sectors
    active_sectors = list(set([p.category for p in patents]))

    return {
        "total_patents": total_patents,
        "total_publications": len(pubs),
        "average_trl": round(avg_trl, 1),
        "active_sectors": active_sectors
    }


@app.get("/api/scurve")
def get_scurve_data():
    # Mock data for an S-curve (Adoption over time)
    years = list(range(2010, 2027))
    return {
        "labels": years,
        "values": [2, 5, 12, 25, 45, 75, 120, 180, 250, 320, 380, 420, 450, 470, 480, 485, 488]
    }


@app.get("/api/search")
def search_technologies(q: str = Query(..., description="Search keyword"), db: Session = Depends(get_db)):
    search_query = f"%{q}%"
    patents = db.query(Patent).filter(
        or_(Patent.title.ilike(search_query), Patent.category.ilike(search_query))
    ).all()

    pubs = db.query(Publication).filter(
        or_(Publication.title.ilike(search_query), Publication.category.ilike(search_query))
    ).all()

    avg_trl = sum(p.trl for p in patents) / max(len(patents), 1) if patents else 0
    active_sectors = list(set([p.category for p in patents]))

    return {
        "results": {
            "total_patents": len(patents),
            "total_publications": len(pubs),
            "average_trl": round(avg_trl, 1),
            "active_sectors": active_sectors
        }
    }


@app.get("/api/semantic-search")
def semantic_search(q: str = Query(..., description="Natural language query"), top_k: int = 5, db: Session = Depends(get_db)):
    """
    Meaning-based search: finds patents/publications related in MEANING to the
    query, even if they share no keywords. Complements /api/search (exact
    keyword match) rather than replacing it -- e.g. searching "AI safety risk"
    can surface an abstract about "mitigating unintended model behavior" that
    keyword search would miss entirely.
    """
    if not _EMBEDDINGS_CACHE["patents"] and not _EMBEDDINGS_CACHE["publications"]:
        return {
            "error": "No embeddings cache found. Run `python embed_data.py` once to build it first.",
            "results": []
        }

    if openai_client is None:
        return {"error": "OPENAI_API_KEY is not set.", "results": []}

    try:
        query_embedding = openai_client.embeddings.create(model=EMBED_MODEL, input=q).data[0].embedding
    except Exception as e:
        return {"error": f"Embedding the query failed ({type(e).__name__}).", "results": []}

    scored = []
    for pid, vec in _EMBEDDINGS_CACHE["patents"].items():
        scored.append(("patent", pid, _cosine_similarity(query_embedding, vec)))
    for pubid, vec in _EMBEDDINGS_CACHE["publications"].items():
        scored.append(("publication", pubid, _cosine_similarity(query_embedding, vec)))

    scored.sort(key=lambda x: x[2], reverse=True)
    top_matches = scored[:top_k]

    results = []
    for kind, item_id, score in top_matches:
        if kind == "patent":
            record = db.query(Patent).filter(Patent.id == item_id).first()
        else:
            record = db.query(Publication).filter(Publication.id == item_id).first()
        if record:
            results.append({
                "type": kind,
                "title": record.title,
                "category": record.category,
                "date": record.date,
                "similarity": round(score, 3)
            })

    return {"results": results}


def _rule_based_fallback(topic: str, total_patents: int, avg_trl: float) -> dict:
    """The original templated summary, now shaped as structured fields to match the AI path."""
    volume_statement = "significant global R&D investment" if total_patents > 20 else "emerging, early-stage interest"

    if avg_trl >= 7:
        maturity = "Highly mature (TRL 7+), primed for tactical deployment and commercialization."
    elif avg_trl >= 4:
        maturity = "Prototyping and validation phase (TRL 4-6). Field-ready applications expected within 2-3 years."
    else:
        maturity = "Highly theoretical (TRL 1-3). Continued monitoring of academic publications is recommended."

    return {
        "headline": f"{topic.title()}: {volume_statement.capitalize()}",
        "maturity": maturity,
        "recommendation": f"Based on {total_patents} patent filings, this trajectory aligns with standard S-curve adoption rates observed in similar technologies."
    }


@app.get("/api/generate-insight")
def generate_insight(q: str = Query("", description="Search keyword"), db: Session = Depends(get_db)):
    """Real AI Insight Generator: asks an LLM to write a strategic briefing grounded in the current database."""
    search_query = f"%{q}%" if q else "%"

    patents = db.query(Patent).filter(
        or_(Patent.title.ilike(search_query), Patent.category.ilike(search_query))
    ).all()
    pubs = db.query(Publication).filter(
        or_(Publication.title.ilike(search_query), Publication.category.ilike(search_query))
    ).all()

    if not patents and not pubs:
        return {
            "insight": {
                "headline": f"No data found for '{q or 'this query'}'",
                "maturity": "Insufficient data available in the current database to assess readiness.",
                "recommendation": "Recommend broadening the search parameters."
            },
            "source": "no_data"
        }

    total_patents = len(patents)
    total_pubs = len(pubs)
    avg_trl = sum(p.trl for p in patents) / max(total_patents, 1) if patents else 0
    categories = sorted(set(p.category for p in patents) | set(pub.category for pub in pubs))
    topic = q if q else "all monitored sectors"

    # If there's no API key configured, skip straight to the fallback rather than erroring
    if openai_client is None:
        return {
            "insight": _rule_based_fallback(topic, total_patents, avg_trl),
            "source": "fallback",
            "note": "OPENAI_API_KEY is not set, showing rule-based summary."
        }

    sample_patents = [f"- {p.title} (TRL {p.trl}, filed {p.date}, inventor {p.inventor})" for p in patents[:8]]
    sample_pubs = [f"- {pub.title} ({pub.citations} citations, published {pub.date})" for pub in pubs[:8]]

    # Few-shot example: shows the model the EXACT JSON shape and tone we want, not just a description of it.
    # Models are much more reliable at matching a concrete example than a schema description alone.
    example_output = {
        "headline": "Cybersecurity: Sustained R&D momentum with maturing deployment readiness",
        "maturity": "Patents cluster around TRL 5-6, indicating active prototyping with several nearing field validation.",
        "recommendation": "Recommend continued monitoring; allocate exploratory budget as TRL trends toward 7 over the next 12-18 months."
    }

    prompt = f"""You are a technology intelligence analyst. Based ONLY on the data below, produce a strategic briefing on "{topic}". Do not invent facts beyond what is given.

Data summary:
- Total matching patents: {total_patents}
- Total matching publications: {total_pubs}
- Average Technology Readiness Level (TRL) of patents: {avg_trl:.1f} (scale 1-9, where 9 is fully deployed/operational)
- Categories represented: {', '.join(categories) if categories else 'none'}

Sample patents:
{chr(10).join(sample_patents) if sample_patents else 'None'}

Sample publications:
{chr(10).join(sample_pubs) if sample_pubs else 'None'}

Respond with ONLY raw JSON (no markdown fences, no commentary before or after) matching exactly this shape and tone:
{json.dumps(example_output, indent=2)}

Rules:
- "headline": under 12 words, states the core verdict.
- "maturity": 1-2 sentences on R&D volume and TRL-based readiness.
- "recommendation": 1 sentence of outlook or action.
- Ground every claim in the data above. If data is sparse, say so plainly rather than padding."""

    try:
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=400,
            response_format={"type": "json_object"},  # forces valid JSON output, no fences to strip
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.choices[0].message.content.strip()

        try:
            insight = json.loads(raw_text)
            # Sanity-check the shape before trusting it downstream
            if not all(k in insight for k in ("headline", "maturity", "recommendation")):
                raise ValueError("Missing expected keys in model output")
        except (json.JSONDecodeError, ValueError):
            # Model didn't follow the format this time -- fall back rather than serve broken JSON
            return {
                "insight": _rule_based_fallback(topic, total_patents, avg_trl),
                "source": "fallback",
                "note": "AI response was not valid structured JSON, showing rule-based summary."
            }

        return {"insight": insight, "source": "openai"}
    except Exception as e:
        return {
            "insight": _rule_based_fallback(topic, total_patents, avg_trl),
            "source": "fallback",
            "note": f"AI generation failed ({type(e).__name__}), showing rule-based summary."
        }


@app.get("/api/patents")
def get_patents(db: Session = Depends(get_db), limit: int = 50):
    patents = db.query(Patent).limit(limit).all()
    return patents
