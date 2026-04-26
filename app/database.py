import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Define o SQLite como padrão se a variável de ambiente não existir
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./sensevision.db"
)

# O SQLite exige essa flag para não bloquear threads concorrentes no FastAPI
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()