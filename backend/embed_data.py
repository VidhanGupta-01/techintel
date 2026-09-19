"""
Precomputes OpenAI embeddings for every patent and publication abstract, and
saves them to embeddings_cache.json. Run this once after seeding the database
(python data_gen.py), and again any time the underlying data changes.

This is a separate, offline step -- NOT run on every request -- because
embedding 450 rows on every search would be slow and needlessly expensive.
"""
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from database import SessionLocal
from models import Patent, Publication

load_dotenv()

EMBED_MODEL = "text-embedding-3-small"  # cheap, good enough for a project this size
CACHE_FILE = "embeddings_cache.json"


def embed_text(client: OpenAI, text: str) -> list[float]:
    response = client.embeddings.create(model=EMBED_MODEL, input=text)
    return response.data[0].embedding


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set. Add it to your .env file first.")
        return

    client = OpenAI()
    db = SessionLocal()

    patents = db.query(Patent).all()
    pubs = db.query(Publication).all()

    cache = {"patents": {}, "publications": {}}

    print(f"Embedding {len(patents)} patents...")
    for i, p in enumerate(patents):
        text = f"{p.title}. {p.abstract}"
        cache["patents"][p.id] = embed_text(client, text)
        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{len(patents)} done")

    print(f"Embedding {len(pubs)} publications...")
    for i, pub in enumerate(pubs):
        text = f"{pub.title}. {pub.abstract}"
        cache["publications"][pub.id] = embed_text(client, text)
        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{len(pubs)} done")

    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

    db.close()
    print(f"Done. Saved {len(cache['patents'])} patent + {len(cache['publications'])} publication embeddings to {CACHE_FILE}")


if __name__ == "__main__":
    main()
