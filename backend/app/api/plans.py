from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.UserModel import User
from app.schemas.PlanSchema import GeneratePlan

router = APIRouter(prefix="/plans")


@router.post("/generate")
def generate_plan(user_plan_info: GeneratePlan, current_user: User = Depends(get_current_user)):
    
    return user_plan_info
