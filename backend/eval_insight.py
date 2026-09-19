"""
A basic eval harness for /api/generate-insight.

Why this matters: an LLM output "looking right" isn't the same as it BEING
right. This script runs a fixed set of known queries against the running
server and checks the response against ground truth pulled directly from the
database -- catching two failure modes an eyeball check would miss:

  1. Hallucination -- the model states a number that doesn't match the DB
     (e.g. claims "200 patents" when there are actually 30).
  2. Silent fallback -- the AI path failed and the rule-based fallback quietly
     took over. This is easy to miss if you only glance at the text, since the
     fallback text is written to look plausible.

Run this with the backend server already running (python -m uvicorn main:app).
"""
import re
import sys

import requests
from sqlalchemy import or_

from database import SessionLocal
from models import Patent, Publication

BASE_URL = "http://127.0.0.1:8000"

# A handful of known queries. In a bigger project this would live in its own
# file and grow over time as you find new edge cases (e.g. once you'd found
# the empty-query bug, you'd add "" here permanently to stop it recurring).
TEST_QUERIES = ["Quantum", "Generative AI", "Drone Swarms", "Cybersecurity", "Nonexistent Topic XYZ"]


def get_ground_truth(db, q):
    search_query = f"%{q}%"
    patents = db.query(Patent).filter(
        or_(Patent.title.ilike(search_query), Patent.category.ilike(search_query))
    ).all()
    total_patents = len(patents)
    avg_trl = sum(p.trl for p in patents) / max(total_patents, 1) if patents else 0
    return total_patents, avg_trl


def extract_numbers(text):
    return set(re.findall(r'\d+', text))


def run_eval():
    db = SessionLocal()
    passed, failed = 0, 0

    for q in TEST_QUERIES:
        print(f"\n--- Query: '{q}' ---")
        try:
            resp = requests.get(f"{BASE_URL}/api/generate-insight", params={"q": q}, timeout=15)
            data = resp.json()
        except Exception as e:
            print(f"  FAIL: request error ({e})")
            failed += 1
            continue

        # Check 1: response has the expected shape at all
        insight = data.get("insight")
        if not insight or not all(k in insight for k in ("headline", "maturity", "recommendation")):
            print(f"  FAIL: missing expected keys. Got: {data}")
            failed += 1
            continue

        # Check 2: flag (don't fail) if it silently used the fallback -- you want to KNOW this, not just accept it
        source = data.get("source", "unknown")
        if source != "openai":
            print(f"  WARNING: source='{source}', not a real AI response. Note: {data.get('note')}")

        # Check 3: groundedness -- does the DB's actual patent count appear anywhere in the text?
        # This is a simple heuristic, not proof of zero hallucination, but it catches the obvious cases.
        total_patents, avg_trl = get_ground_truth(db, q)
        full_text = f"{insight['headline']} {insight['maturity']} {insight['recommendation']}"
        mentioned_numbers = extract_numbers(full_text)

        if total_patents > 0 and str(total_patents) not in mentioned_numbers and source == "openai":
            print(f"  WARNING: DB shows {total_patents} patents, but that number doesn't appear in the output. Possible drift from source data.")

        print(f"  headline: {insight['headline']}")
        print(f"  (ground truth: {total_patents} patents, avg TRL {avg_trl:.1f})")
        print("  PASSED (structure valid)")
        passed += 1

    db.close()
    print(f"\n=== {passed}/{len(TEST_QUERIES)} queries returned valid structured responses ===")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    run_eval()
