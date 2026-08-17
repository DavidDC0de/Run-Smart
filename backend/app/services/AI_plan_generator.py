from openai import OpenAI
from app.core.config import settings
import json

client = OpenAI(api_key = settings.open_ai_key)

def generate_training_plan(user_summary: dict):

    # System prompt encodes the coaching knowledge
    system_prompt = """
    You are an expert running coach with knowledge of periodisation, 
    heart rate training zones, and race-specific preparation.
    
    Training principles you follow:
    - 80/20 rule: 80% of runs should be easy (zone 1-2), 20% hard
    - Long run is the cornerstone of marathon/half training
    - Weekly total km should not increase more than 10% week-over-week
    - Long run distance specifically should not increase more than ~10% week-over-week
      and should be capped independently of total km growth, since it carries
      the highest injury risk of any single session
    - Include a taper of 2-3 weeks before race day: reduce total volume while
      keeping some intensity, so fitness is retained but fatigue is shed
    - Tempo runs build lactate threshold (important for when runner's goal_race_km is long distance),
      intervals build speed (important for when runner's goal race time: "goal_time_min" in minutes is close or lower than average pace in seconds per km: "average_pace_sec_per_km")
    - Recovery days are as important as hard days
    - Never schedule more than 3-4 consecutive training days without a rest day
    - All distances including total_km and distance_km are in kilometres, all paces in seconds per kilometre
    - Every training week (except recovery/deload/taper weeks) must include
      at least one quality session that is either "tempo" or "interval" —
      never a week of only "easy" and "long_run" sessions
    - Do not schedule tempo and interval in the same week back-to-back unless
      the plan is in its final peak/race-specific phase — early weeks should
      alternate which quality type appears
    - Across any 4-week block, include both tempo and interval sessions at
      least once each, not just one repeated every week
    
    Heart rate zone scale (use these consistently for target_heart_rate_zone):
    1 = very easy / recovery
    2 = easy / aerobic base (most 80% volume lives here)
    3 = moderate / steady
    4 = tempo / threshold
    5 = hard / interval / VO2max

    You must return ONLY valid JSON matching this exact structure:
    {
        "plan_summary": "string",
        "weeks": [
            {
                "week_number": int,
                "total_km": float,
                "sessions": [
                    {
                        "day": "string",
                        "session_type": "easy|tempo|interval|long_run|rest",
                        "distance_km": float,
                        "target_pace_sec_per_km": int,
                        "target_heart_rate_zone": int,
                        "description": "string"
                    }
                ]
            }
        ]
    }
    Return nothing else. No markdown, no explanation, just the JSON.
    """
    
    # User prompt contains the actual data
    user_prompt = f"""
    Generate a training plan for this runner:
    
    Current fitness:
    - Fitness score: {user_summary['fitness_score']}/100
    - Average weekly km: {user_summary['average_weekly_km']}
    - Average pace: {user_summary['average_pace_sec_per_km']} seconds per km
    - Longest recent run: {user_summary['longest_recent_run_km']} km
    - Zone 2 training percentage: {user_summary['zone_2_percentage']}%
    - Training consistency: {user_summary['training_consistancy']} of last 8 weeks
    
    Goals:
    - Race distance: {user_summary['goal_race_km']} km
    - Target finish time: {user_summary['goal_time_min']} minutes
    - Race date: {user_summary['race_date']}
    - Weeks until race: {user_summary['weeks_until_race']}
    - Training days per week: {user_summary['training_days_per_week']}
    - Available days: {', '.join(user_summary['available_days'])}
    
    Generate the complete plan for all {user_summary['weeks_until_race']} weeks,
    using exactly {user_summary['training_days_per_week']} training days per week
    chosen from the available days listed above. This day count is already
    capped at 4-5 and reconciled with the runner's request, so use it as-is
    without adjusting it further.

    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,  # low temperature = more consistent structured output
        max_tokens=16000
    )
    
    # Extract the text response
    
    raw_response = response.choices[0].message.content
    
    
    # Parse JSON — this is where you validate the structure
    try:
        plan_data = json.loads(raw_response)
    except json.JSONDecodeError:
        # retry logic would go here
        raise ValueError("LLM returned invalid JSON")
    
    return plan_data