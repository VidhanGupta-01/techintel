import random
from datetime import datetime, timedelta
from database import SessionLocal, engine, Base
from models import Patent, Publication

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

def seed_database():
    db = SessionLocal()
    
    # Check if data already exists to avoid duplicates
    if db.query(Patent).first():
        print("Database already seeded!")
        db.close()
        return

    categories = ["Quantum Computing", "Generative AI", "Drone Swarms", "Advanced Materials", "Cybersecurity"]
    
    print("Generating and inserting patents...")
    for i in range(150):
        category = random.choice(categories)
        trl = random.randint(3, 8) if category != "Generative AI" else random.randint(7, 9)
        
        patent = Patent(
            id=f"PAT-{random.randint(10000, 99999)}",
            title=f"System and Method for {category} Optimization",
            abstract=f"This invention relates to a novel approach in {category}, significantly improving efficiency and reducing costs by employing advanced algorithmic structures and novel materials...",
            date=(datetime.now() - timedelta(days=random.randint(10, 3000))).strftime("%Y-%m-%d"),
            category=category,
            trl=trl,
            inventor=f"Dr. {random.choice(['Smith', 'Johnson', 'Kumar', 'Patel', 'Wang', 'Garcia'])}"
        )
        db.add(patent)

    print("Generating and inserting publications...")
    for i in range(300):
        category = random.choice(categories)
        pub = Publication(
            id=f"PUB-{random.randint(10000, 99999)}",
            title=f"A Review of Recent Advancements in {category}",
            abstract=f"In this paper, we explore the state-of-the-art developments in {category}. We analyze current limitations and propose theoretical frameworks to advance the technology readiness...",
            date=(datetime.now() - timedelta(days=random.randint(10, 3000))).strftime("%Y-%m-%d"),
            category=category,
            citations=random.randint(0, 500)
        )
        db.add(pub)

    # Commit all the transactions at once
    db.commit()
    db.close()
        
    print("Successfully seeded SQLite database with 150 patents and 300 publications.")

if __name__ == "__main__":
    seed_database()
