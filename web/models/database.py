# web/models/database.py
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    shop_url = Column(String, unique=True, index=True, nullable=False)
    access_token = Column(String, nullable=False)


def create_db_and_tables():
    """
    Creates the database and all tables defined.
    This is called once on application startup.
    """
    print("[DEBUG] Initializing database and creating tables if they don't exist...")
    Base.metadata.create_all(bind=engine)
