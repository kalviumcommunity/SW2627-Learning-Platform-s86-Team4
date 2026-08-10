import sys
from backend.database.db import Base, engine

def reset_database():
    try:
        print("Connecting to database and dropping existing tables...")
        Base.metadata.drop_all(bind=engine)
        print("Creating all tables with the updated schema...")
        Base.metadata.create_all(bind=engine)
        print("\nDatabase reset successfully! All tables recreated.")
    except Exception as e:
        print(f"\nError resetting database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    reset_database()
