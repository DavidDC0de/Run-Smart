
from sqlalchemy.orm import Session
from datetime import timedelta, datetime, date

from app.models.ActivityModel import Activity
from app.schemas.PlanSchema import GeneratePlan

def calculate_fitness_summary(user_id: int, db: Session, user_plan_info):

    cutoff = datetime.now(datetime.now().tzinfo) - timedelta(days=365)
    running_data = db.query(Activity).filter(Activity.user_id == user_id,
                                             Activity.date >= cutoff
                                             ).all()
    
    #################################################
    #average weekly km:
    #################################################

    total_km = sum(activity.distance_meters for activity in running_data) / 1000
    active_weeks = set()

    for activity in running_data:
        activity_date = activity.date.date()

        week_start = (
            activity_date - timedelta(days=activity_date.weekday())
        )

        active_weeks.add(week_start)

    num_active_weeks = len(active_weeks)

    avg_weekly_km = (
        total_km / num_active_weeks
        if num_active_weeks > 0
        else 0
    )

    ##############################################
    #averege pace
    ##############################################

    total_seconds = sum(activity.duration_minutes for activity in running_data) * 60
    total_meters = sum(activity.distance_meters for activity in running_data)

    avg_pace_sec_per_km = total_seconds / (total_meters / 1000)

    #################################################
    #longest run
    #################################################

    longest_recent_run_km = max(activity.distance_meters for activity in running_data)/ 1000

    ################################################
    #zone 2 minutes
    ################################################

    zone_2_minutes = sum(
    activity.heart_rate_zone_2_minutes or 0
    for activity in running_data
    )

    total_zone_minutes = sum(
        (activity.heart_rate_zone_1_minutes or 0) +
        (activity.heart_rate_zone_2_minutes or 0) +
        (activity.heart_rate_zone_3_minutes or 0) +
        (activity.heart_rate_zone_4_minutes or 0) +
        (activity.heart_rate_zone_5_minutes or 0)
        for activity in running_data
    )

    zone_2_percentage = (
        zone_2_minutes / total_zone_minutes * 100
        if total_zone_minutes > 0
        else None
    )

  
    ################################################
    #week untill race
    ################################################

    today = date.today()

    days_until_race = (user_plan_info.race_date - today).days

    if days_until_race <= 0:
        return 0

    weeks_untill_race = days_until_race // 7

    #################################################
    #training consistancy 
    #################################################


    now = datetime.now().date()

    # Monday of the current week
    current_week_start = now - timedelta(days=now.weekday())

    active_weeks = set()

    for activity in running_data:
        activity_date = activity.date.date()

        # Monday of the activity's week
        activity_week_start = (
            activity_date - timedelta(days=activity_date.weekday())
        )

        weeks_ago = (
            current_week_start - activity_week_start
        ).days // 7

        if 0 <= weeks_ago < 8:
            active_weeks.add(activity_week_start)

    training_consistency = len(active_weeks)
    fitness_score = calculate_fitness_score(avg_weekly_km,
                                            longest_recent_run_km,
                                            training_consistency,
                                            zone_2_percentage)

    return {
          "average_weekly_km": avg_weekly_km, 
          "average_pace_sec_per_km": avg_pace_sec_per_km,
          "longest_recent_run_km": longest_recent_run_km, 
          "zone_2_percentage": zone_2_percentage, 
          "training_consistancy": training_consistency, 
          "fitness_score": fitness_score,
          "goal_race_km": user_plan_info.goal_race_km,
          "goal_time_min": user_plan_info.goal_time_min,
          "race_date": user_plan_info.race_date,
          "week_untill_race": "pass",
          "training_days_per_week": user_plan_info.training_days_per_week,
          "available_days": user_plan_info.available_days,
          "weeks_until_race": weeks_untill_race
        }

def calculate_fitness_score(
    avg_weekly_km: float,
    longest_run_km: float,
    training_consistency: int,
    zone_2_percentage: float | None,
) -> int:

    # ---------------------------------------------------------
    # 1. Weekly volume score: 20-90
    #
    # 0-20 km   -> 20-35
    # 20-40 km  -> 35-55
    # 40-60 km  -> 55-75
    # 60+ km    -> 75-90
    # ---------------------------------------------------------

    if avg_weekly_km < 20:
        volume_score = 20 + (avg_weekly_km / 20) * 15

    elif avg_weekly_km < 40:
        volume_score = 35 + (
            (avg_weekly_km - 20) / 20
        ) * 20

    elif avg_weekly_km < 60:
        volume_score = 55 + (
            (avg_weekly_km - 40) / 20
        ) * 20

    else:
        volume_score = min(
            90,
            75 + ((avg_weekly_km - 60) / 40) * 15
        )

    # ---------------------------------------------------------
    # 2. Consistency adjustment: -10 to +5
    #
    # 0/8 weeks = -10
    # 2/8 weeks = -5
    # 4/8 weeks =  0
    # 6/8 weeks = +3
    # 8/8 weeks = +5
    # ---------------------------------------------------------

    consistency_adjustment = (
        (training_consistency / 8) * 15
    ) - 10

    # ---------------------------------------------------------
    # 3. Longest run adjustment: -3 to +5
    # ---------------------------------------------------------

    longest_run_score = min(
        5,
        (longest_run_km / 30) * 5
    )

    longest_run_adjustment = longest_run_score - 3

    # ---------------------------------------------------------
    # 4. Zone 2 adjustment: -3 to +3
    # ---------------------------------------------------------

    if zone_2_percentage is None:
        zone_2_adjustment = 0

    elif zone_2_percentage < 40:
        zone_2_adjustment = -3

    elif zone_2_percentage < 60:
        zone_2_adjustment = -1

    elif zone_2_percentage <= 80:
        zone_2_adjustment = 3

    elif zone_2_percentage <= 90:
        zone_2_adjustment = 1

    else:
        zone_2_adjustment = -1

    # ---------------------------------------------------------
    # Final score
    # ---------------------------------------------------------

    score = (
        volume_score
        + consistency_adjustment
        + longest_run_adjustment
        + zone_2_adjustment
    )

    return round(max(1, min(100, score)))