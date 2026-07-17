from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import SessionLocal, engine, Base
from models import Patent, Publication

app = FastAPI(title="DRDO Tech Intelligence API v2")

# Allow CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.get("/api/generate-insight")
def generate_insight(q: str = Query("", description="Search keyword"), db: Session = Depends(get_db)):
    """Simulated AI Insight Generator based on database metrics."""
    search_query = f"%{q}%" if q else "%"
    
    patents = db.query(Patent).filter(
        or_(Patent.title.ilike(search_query), Patent.category.ilike(search_query))
    ).all()
    
    if not patents:
        return {"insight": "Insufficient data available in the current database to generate a conclusive intelligence report on this topic. Recommend broadening the search parameters."}

    total_patents = len(patents)
    avg_trl = sum(p.trl for p in patents) / max(total_patents, 1)
    
    # Rule-based generation logic
    volume_statement = "significant global R&D investment" if total_patents > 20 else "emerging, early-stage interest"
    
    if avg_trl >= 7:
        readiness_statement = "The technology is highly mature (TRL 7+) and is primed for immediate tactical deployment and commercialization."
    elif avg_trl >= 4:
        readiness_statement = "The technology is currently in the prototyping and validation phase (TRL 4-6). Expect field-ready applications within the next 2-3 years."
    else:
        readiness_statement = "The technology remains highly theoretical (TRL 1-3). Continued monitoring of academic publications is recommended before committing heavy capital."

    topic = q if q else "across all monitored sectors"
    
    generated_report = (
        f"**Strategic Analysis for '{topic}':**\n\n"
        f"Based on the analysis of {total_patents} patent filings, there is {volume_statement} in this domain. "
        f"{readiness_statement} "
        f"Our simulated models suggest this trajectory aligns closely with standard S-curve adoption rates observed in similar critical technologies."
    )
    
    return {"insight": generated_report}

@app.get("/api/patents")
def get_patents(db: Session = Depends(get_db), limit: int = 50):
    patents = db.query(Patent).limit(limit).all()
    return patents
