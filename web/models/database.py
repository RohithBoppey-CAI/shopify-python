# web/models/database.py
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import settings
import os

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


def create_folders(folders=[]):
    """
    Takes in a list of folder names, and creates them in the root directory where the code is running.
    """
    for folder in folders:
        try:
            os.makedirs(folder, exist_ok=True)
            print(f"Created or already exists: {folder}")
        except Exception as e:
            print(f"Failed to create {folder}: {e}")


def remove_shopify_db():
    """
    Removes the existing SQLite database file.
    Use with caution as this will delete all data.
    """
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed database file at {db_path}")
    else:
        print(f"No database file found at {db_path} to remove.")
