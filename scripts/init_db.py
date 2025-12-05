"""
Initialize the database - creates all tables
"""
from models.database import Base, engine, init_db

if __name__ == "__main__":
    init_db()
