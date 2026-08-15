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
    - Weekly mileage should not increase more than 10% per week
    - Include a taper of 2-3 weeks before race day
    - Tempo runs build lactate threshold, intervals build speed
    - Recovery days are as important as hard days
    
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
    
    Generate the complete plan for all {user_summary['weeks_until_race']} weeks.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,  # low temperature = more consistent structured output
        max_tokens=4000
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