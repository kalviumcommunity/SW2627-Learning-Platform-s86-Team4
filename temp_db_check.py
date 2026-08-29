from backend.database.db import SessionLocal, Base, engine
from backend.models.models import User
from backend.services.auth_service import get_password_hash

Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    user = User(username='dbtestuser', email='dbtest@example.com', hashed_password=get_password_hash('Test123!'))
    db.add(user)
    db.commit()
    db.refresh(user)
    print('user created', user.id)
except Exception as e:
    db.rollback()
    print('DB ERROR:', repr(e))
finally:
    db.close()
