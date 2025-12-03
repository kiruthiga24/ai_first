from fastapi import APIRouter, Depends, HTTPException
from app.schemas.optimizer import OptimizeRequest, OptimizeResponse
from app.services.optimizer_service import SQLOptimizerService
from app.db.session import SessionLocal
from sqlalchemy.orm import Session
from app.models.optimization import Optimization

router = APIRouter()
service = SQLOptimizerService()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest, db: Session = Depends(get_db)):
    print("inside backend")
    print(req.sql)
    print(req.table)
    if not req.sql.strip():
        raise HTTPException(status_code=400, detail="SQL is required")

    # result = service.stats(req.sql)
    result = service.optimize(req.sql, table_id=req.table)

    # persist record
    try:
        rec = Optimization(
            original_sql=result["original_sql"],
            optimized_sql=result["optimized_sql"],
            diff=result.get("diff"),
            stats_before=result.get("stats_before"),
            stats_after=result.get("stats_after"),
        )
        db.add(rec)
        db.commit()
    except Exception as e:
        # log, but do not fail the optimization
        print("DB save error:", e)

    return result
