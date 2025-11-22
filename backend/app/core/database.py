from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL 
IS_DEV = settings.FRONTEND_URL.startswith("http://localhost")
engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=IS_DEV, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
