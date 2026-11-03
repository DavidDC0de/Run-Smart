from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.ExplanationModel import WeekExplanation
from app.models.PlanModel import TrainingPlan
from app.models.SessionModel import Session as TrainingSession
from app.models.UserModel import User
from app.schemas.PlanSchema import (
    ExplanationOut,
    GenerateManualPlan,
    GeneratePlan,
    PlanDetailOut,
    PlanSummaryOut,
    SessionOut,
    WeekOut,
)
from app.services.AI_plan_generator import explaining_programme_ai
from app.services.plan import (
    NotEnoughDataError,
    build_manual_fitness_summary,
    calculate_fitness_summary,
    determine_phases,
    determine_week_phase,
    generate_training_plan,
)

router = APIRouter(prefix="/plans", tags=["Plans"])


# ----------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------
def get_owned_plan(db: Session, plan_id: int, user: User) -> TrainingPlan:
    # Returns 404 for plans that don't exist AND plans owned by someone else,
    # so nobody can discover other users' plan ids.
    plan = (
        db.query(TrainingPlan)
        .filter(TrainingPlan.id == plan_id, TrainingPlan.user_id == user.id)
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


def summary_fields(plan: TrainingPlan) -> dict:
    return {
        "id": plan.id,
        "goal_race_km": plan.goal_race_km,
        "goal_time_min": plan.goal_time_min,
        "race_date": plan.race_date.date(),
        "weeks_until_race": plan.weeks_until_race,
        "training_days_per_week": plan.training_days_per_week,
        "status": plan.status,
        "created_at": plan.created_at,
    }


def build_plan_detail(db: Session, plan: TrainingPlan) -> PlanDetailOut:
    rows = (
        db.query(TrainingSession)
        .filter(TrainingSession.plan_id == plan.id)
        .order_by(TrainingSession.week_number, TrainingSession.id)
        .all()
    )

    # Phase isn't stored, but it's fully determined by the plan length
    phases = determine_phases(plan.weeks_until_race)

    by_week: dict[int, list] = {}
    for row in rows:
        by_week.setdefault(row.week_number, []).append(row)

    weeks = []
    for week_number in sorted(by_week):
        sessions = [
            SessionOut(
                day=r.day_of_week,
                type=r.session_type,
                distance_km=r.target_distance,
                pace_sec_per_km=round(r.target_pace),
            )
            for r in by_week[week_number]
        ]
        weeks.append(
            WeekOut(
                week_number=week_number,
                phase=determine_week_phase(week_number, phases),
                total_km=round(sum(s.distance_km for s in sessions), 1),
                sessions=sessions,
            )
        )

    return PlanDetailOut(**summary_fields(plan), weeks=weeks)


# ----------------------------------------------------------------
# Create plans
# ----------------------------------------------------------------
@router.post("/generate", response_model=PlanDetailOut, status_code=201)
def generate_plan(
    user_plan_info: GeneratePlan,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        user_summary = calculate_fitness_summary(current_user.id, db, user_plan_info)
    except NotEnoughDataError as e:
        raise HTTPException(status_code=400, detail=str(e))

    plan_id = generate_training_plan(current_user.id, user_summary, db)
    return build_plan_detail(db, get_owned_plan(db, plan_id, current_user))


@router.post("/generate_manual", response_model=PlanDetailOut, status_code=201)
def generate_manual_plan(
    plan_info_manual: GenerateManualPlan,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_summary = build_manual_fitness_summary(plan_info_manual)

    plan_id = generate_training_plan(current_user.id, user_summary, db)
    return build_plan_detail(db, get_owned_plan(db, plan_id, current_user))


# ----------------------------------------------------------------
# Read plans
# ----------------------------------------------------------------
@router.get("", response_model=list[PlanSummaryOut])
def list_plans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plans = (
        db.query(TrainingPlan)
        .filter(TrainingPlan.user_id == current_user.id)
        .order_by(TrainingPlan.created_at.desc())
        .all()
    )
    return [PlanSummaryOut(**summary_fields(p)) for p in plans]


@router.get("/{plan_id}", response_model=PlanDetailOut)
def get_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return build_plan_detail(db, get_owned_plan(db, plan_id, current_user))


@router.delete("/{plan_id}", status_code=204)
def delete_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = get_owned_plan(db, plan_id, current_user)
    db.query(WeekExplanation).filter(WeekExplanation.plan_id == plan.id).delete()
    db.query(TrainingSession).filter(TrainingSession.plan_id == plan.id).delete()
    db.delete(plan)
    db.commit()
    return Response(status_code=204)


# ----------------------------------------------------------------
# AI explanation (generated on first request, then saved)
# ----------------------------------------------------------------
@router.get("/{plan_id}/weeks/{week_number}/explanation", response_model=ExplanationOut)
def get_week_explanation(
    plan_id: int,
    week_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = get_owned_plan(db, plan_id, current_user)

    saved = (
        db.query(WeekExplanation)
        .filter(WeekExplanation.plan_id == plan.id, WeekExplanation.week_number == week_number)
        .first()
    )
    if saved:
        return ExplanationOut(plan_id=plan.id, week_number=week_number, explanation=saved.explanation)

    detail = build_plan_detail(db, plan)
    week = next((w for w in detail.weeks if w.week_number == week_number), None)
    if week is None:
        raise HTTPException(status_code=404, detail="Week not found in this plan")

    goal_time = f" in {plan.goal_time_min:.0f} minutes" if plan.goal_time_min else ""
    context = (
        f"- Goal: complete a {plan.goal_race_km} km race{goal_time}\n"
        f"- This is week {week_number} of {plan.weeks_until_race} in their plan"
    )

    try:
        text = explaining_programme_ai(week.model_dump(), runner_context=context)
    except Exception:
        raise HTTPException(status_code=502, detail="Could not generate the explanation right now. Try again shortly.")

    db.add(WeekExplanation(plan_id=plan.id, week_number=week_number, explanation=text))
    try:
        db.commit()
    except IntegrityError:
        # two requests raced; the other one saved first, so use its version
        db.rollback()
        existing = (
            db.query(WeekExplanation)
            .filter(WeekExplanation.plan_id == plan.id, WeekExplanation.week_number == week_number)
            .first()
        )
        if existing:
            text = existing.explanation

    return ExplanationOut(plan_id=plan.id, week_number=week_number, explanation=text)