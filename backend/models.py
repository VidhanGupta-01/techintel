from sqlalchemy import Column, Integer, String
from database import Base

class Patent(Base):
    __tablename__ = "patents"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    abstract = Column(String)
    date = Column(String)
    category = Column(String, index=True)
    trl = Column(Integer)
    inventor = Column(String)

class Publication(Base):
    __tablename__ = "publications"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    abstract = Column(String)
    date = Column(String)
    category = Column(String, index=True)
    citations = Column(Integer)
