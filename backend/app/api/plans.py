from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.UserModel import User
from app.schemas.PlanSchema import GeneratePlan
from app.services.plan import calculate_fitness_summary, generate_training_plan
#from app.services.AI_plan_generator import generate_training_plan

router = APIRouter(prefix="/plans")


@router.post("/generate")
def generate_plan(user_plan_info: GeneratePlan, 
                  current_user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):

    user_summary = calculate_fitness_summary(current_user.id, db, user_plan_info)
    training_plan = generate_training_plan(user_summary)
    return training_plan
