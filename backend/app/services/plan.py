
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
        else "Unknown - heart rate data unavailable"
    )

  
    ################################################
    #week untill race
    ################################################

    today = date.today()

    days_until_race = (user_plan_info.race_date - today).days

    if days_until_race <= 0:
        return 0

    weeks_until_race = days_until_race // 7

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

    #################################################################
    #goal time pace
    #################################################################

    goal_time_pace =  (user_plan_info.goal_time_min * 60 )/ user_plan_info.goal_race_km

    user_summary={
          "average_weekly_km": avg_weekly_km, 
          "average_pace_sec_per_km": avg_pace_sec_per_km,
          "longest_recent_run_km": longest_recent_run_km, 
          "zone_2_percentage": zone_2_percentage, 
          "training_consistancy": training_consistency, 
          "fitness_score": fitness_score,
          "goal_race_km": user_plan_info.goal_race_km,
          "goal_time_min": user_plan_info.goal_time_min,
          "race_date": user_plan_info.race_date,
          "training_days_per_week": user_plan_info.training_days_per_week,
          "available_days": user_plan_info.available_days,
          "weeks_until_race": weeks_until_race,
          "goal_time_pace_sec": goal_time_pace,
          "current_pace_per_sec": user_plan_info.current_5k_pace
    }

    return user_summary

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

    if zone_2_percentage is not int:
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

#######################################################
#generate training plan
########################################################

def generate_training_plan(summary):

    total_weeks = summary["weeks_until_race"]
    race_distance = summary["goal_race_km"]
    training_days = summary["training_days_per_week"]

    phases = determine_phases(total_weeks)

    starting_volume = calculate_starting_volume(summary)

    paces = calculate_training_paces(
        summary["goal_time_pace_sec"],
        summary["average_pace_sec_per_km"],
        summary["current_pace_per_sec"]
    )

    plan = []

    previous_volume = starting_volume
    previous_long_run = starting_volume * 0.4

    for week_number in range(1, total_weeks + 1):

        phase = determine_week_phase(
            week_number,
            phases
        )

        weekly_volume = calculate_weekly_volume(
            starting_volume,
            week_number,
            previous_volume,
            phase
        )

        long_run = calculate_long_run(
            previous_long_run,
            week_number,
            race_distance,
            phase
        )

        sessions = generate_week_sessions(
            week_number=week_number,
            weekly_volume=weekly_volume,
            long_run=long_run,
            training_days=training_days,
            available_days=summary["available_days"],
            phase=phase,
            paces=paces,
            current_pace=summary["current_pace_per_sec"],
            goal_pace=summary["goal_time_pace_sec"],
            total_weeks=summary["weeks_until_race"]
        )

        plan.append({
            "week_number": week_number,
            "phase": phase,
            "total_km": round(weekly_volume, 1),
            "sessions": sessions
        })

        if not is_recovery_week(week_number, phase):
            previous_volume = weekly_volume
            previous_long_run = long_run

    return plan

########################################################
# break the total nr of weeks into stages
#######################################################

def determine_phases(total_weeks):
    taper_weeks = 2
    remaining = total_weeks - taper_weeks

    base_weeks = max(2, round(remaining * 0.30))
    build_weeks = max(2, round(remaining * 0.40))
    race_weeks = remaining - base_weeks - build_weeks

    return {
        "base": base_weeks,
        "build": build_weeks,
        "race_specific": race_weeks,
        "taper": taper_weeks
    }

def determine_week_phase(week_number, phases):
    base_end = phases["base"]

    build_end = base_end + phases["build"]

    race_end = build_end + phases["race_specific"]

    if week_number <= base_end:
        return "base"

    if week_number <= build_end:
        return "build"

    if week_number <= race_end:
        return "race_specific"

    return "taper"

def is_recovery_week(week_number, phase):
    if phase == "taper":
        return False

    return week_number % 4 == 0

##################################################
# calculate starting volume
##################################################

def calculate_starting_volume(summary):
    average = summary["average_weekly_km"]
    consistency = summary["training_consistancy"]
    longest_run = summary["longest_recent_run_km"]

    if consistency <= 2:
        # Detrained runner
        return min(average * 2, longest_run * 2, 20)

    return average

###################################################
# calculate the paces to train at 
###################################################

def calculate_training_paces(goal_pace, average_pace, current_pace):

    current_pace = min(current_pace, average_pace + 60)

    pace_gap = max(0, current_pace - goal_pace)
  
    # Start training paces from current fitness
    easy = current_pace + 60
    long_run = current_pace + 45
    

    # Quality sessions sit between current fitness and goal pace
    tempo = current_pace - (pace_gap * 0.10)
    interval = current_pace - (pace_gap * 0.20)

    return {
        "easy": round(easy),
        "long_run": round(long_run),
        "tempo": round(tempo),
        "race": round(goal_pace),
        "interval": round(interval),
    }

#################################################
#calculate weekly volume progression
#################################################

def calculate_weekly_volume(
    starting_volume,
    week_number,
    previous_volume,
    phase
):
    if week_number == 1:
        return starting_volume

    # Recovery week
    if is_recovery_week(week_number, phase):
        return previous_volume * 0.80

    # Taper
    if phase == "taper":
        return previous_volume * 0.70

    # Base phase
    if phase == "base":
        return previous_volume * 1.05

    # Build phase
    if phase == "build":
        return previous_volume * 1.08

    # Race-specific phase
    if phase == "race_specific":
        return previous_volume * 1.05

    return previous_volume

##################################################
#choose between tempo and interval weekly for quality session
#################################################

def choose_quality_session(week_number):
    if week_number % 2 == 0:
        return "tempo"

    return "interval"

######################################################
#calculate log run distance graduatly increasing
######################################################

def calculate_long_run(
    previous_long_run,
    week_number,
    race_distance,
    phase
):
    if phase == "recovery":
        return previous_long_run * 0.8

    if phase == "taper":
        return previous_long_run * 0.7

    long_run = previous_long_run * 1.08

    # Don't let it exceed the race-specific ceiling
    max_long_run = race_distance * 0.9

    return min(long_run, max_long_run)

##############################################################
#calculate increase in pace 
#############################################################

def progress_training_pace(
    base_pace,
    current_pace,
    goal_pace,
    week_number,
    total_weeks,
    workout_type,
    phase
):
    max_progression = {
        "easy": 0.15,
        "long_run": 0.10,
        "tempo": 0.55,
        "interval": 0.85,
        "race": 1.00,
    }

    target_progression = max_progression.get(workout_type, 0.15)

    # Slow progression during base,
    # normal progression during build,
    # strongest progression during race-specific phase.
    phase_multiplier = {
        "base": 0.5,
        "build": 1.1,
        "race_specific": 1.2,
        "taper": 0.0,
    }

    multiplier = phase_multiplier.get(phase, 1.0)

    progress = min(week_number / total_weeks, 1.0)

    pace_gap = max(0, current_pace - goal_pace)

    improvement = (
        pace_gap
        * target_progression
        * progress
        * multiplier
    )

    progressed_pace = base_pace - improvement

    return round(progressed_pace)

################################################################
#generate weekly sessions
################################################################

def generate_week_sessions(
    week_number,
    weekly_volume,
    long_run,
    training_days,
    available_days,
    phase,
    paces,
    current_pace,
    goal_pace,
    total_weeks
):
    quality_type = choose_quality_session(week_number)

    def get_pace(workout_type):
        return progress_training_pace(
            base_pace=paces[workout_type],
            current_pace=current_pace,
            goal_pace=goal_pace,
            week_number=week_number,
            total_weeks=total_weeks,
            workout_type=workout_type,
            phase=phase
        )

    if training_days == 3:

        easy_km = weekly_volume * 0.30
        quality_km = weekly_volume * 0.25

        return [
            {
                "day": available_days[0],
                "type": "easy",
                "distance_km": round(easy_km, 1),
                "pace_sec_per_km": get_pace("easy")
            },
            {
                "day": available_days[1],
                "type": quality_type,
                "distance_km": round(quality_km, 1),
                "pace_sec_per_km": get_pace(quality_type)
            },
            {
                "day": available_days[2],
                "type": "long_run",
                "distance_km": round(long_run, 1),
                "pace_sec_per_km": get_pace("long_run")
            }
        ]

    if training_days == 4:

        easy_km = weekly_volume * 0.20
        quality_km = weekly_volume * 0.20
        easy_km_2 = weekly_volume * 0.15

        return [
            {
                "day": available_days[0],
                "type": "easy",
                "distance_km": round(easy_km, 1),
                "pace_sec_per_km": get_pace("easy")
            },
            {
                "day": available_days[1],
                "type": quality_type,
                "distance_km": round(quality_km, 1),
                "pace_sec_per_km": get_pace(quality_type)
            },
            {
                "day": available_days[2],
                "type": "easy",
                "distance_km": round(easy_km_2, 1),
                "pace_sec_per_km": get_pace("easy")
            },
            {
                "day": available_days[3],
                "type": "long_run",
                "distance_km": round(long_run, 1),
                "pace_sec_per_km": get_pace("long_run")
            }
        ]

    if training_days == 5:

        easy_km = weekly_volume * 0.18
        quality_km = weekly_volume * 0.18
        easy_km_2 = weekly_volume * 0.15
        easy_km_3 = weekly_volume * 0.14

        return [
            {
                "day": available_days[0],
                "type": "easy",
                "distance_km": round(easy_km, 1),
                "pace_sec_per_km": get_pace("easy")
            },
            {
                "day": available_days[1],
                "type": quality_type,
                "distance_km": round(quality_km, 1),
                "pace_sec_per_km": get_pace(quality_type)
            },
            {
                "day": available_days[2],
                "type": "easy",
                "distance_km": round(easy_km_2, 1),
                "pace_sec_per_km": get_pace("easy")
            },
            {
                "day": available_days[3],
                "type": "easy",
                "distance_km": round(easy_km_3, 1),
                "pace_sec_per_km": get_pace("easy")
            },
            {
                "day": available_days[4],
                "type": "long_run",
                "distance_km": round(long_run, 1),
                "pace_sec_per_km": get_pace("long_run")
            }
        ]
    
    # TO DO LIST:
    # - available training days must be between 3 to 5