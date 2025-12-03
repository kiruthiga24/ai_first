from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    # Import models to register metadata, then create tables (for quickstart)
    import app.models.optimization as opt_model
    opt_model.Base.metadata.create_all(bind=engine)
