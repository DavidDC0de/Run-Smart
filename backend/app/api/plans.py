from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.UserModel import User
from app.schemas.PlanSchema import GeneratePlan
from app.services.plan import calculate_fitness_summary, generate_training_plan
from app.services.AI_plan_generator import explaining_programme_ai

router = APIRouter(prefix="/plans")


@router.post("/generate")
def generate_plan(user_plan_info: GeneratePlan, 
                  current_user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):

    #calculate fitness level of user
    user_summary = calculate_fitness_summary(current_user.id, db, user_plan_info)

    #generate a full training programme 
    training_plan = generate_training_plan(current_user.id, user_summary, db)
    
    #explain week by week using ai
    explanation = explaining_programme_ai(
        training_plan[0],
        runner_context=f"- Goal: complete a {user_plan_info.goal_race_km}\n- Recent history: this is week {training_plan[0]["week_number"]}, no prior sessions logged yet"
    )
    print(explanation)
    
    return training_plan
