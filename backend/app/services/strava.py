import httpx
from sqlalchemy.orm import Session
from app.models.ActivityModel import Activity
from app.models.UserModel import User
from app.core.config import settings
from datetime import date, datetime, timezone
from app.core.database import get_db
from fastapi import Depends


def refresh_token_if_needed(user: User, db: Session):
    date_now = datetime.now(timezone.utc)
    if isinstance(user.strava_token_expires_at, datetime):
        token_expiry_date = user.strava_token_expires_at
    else:
        token_expiry_date = datetime.fromisoformat(str(user.strava_token_expires_at))

    if token_expiry_date.tzinfo is None:
        token_expiry_date = token_expiry_date.replace(tzinfo=timezone.utc)
    
    if date_now > token_expiry_date:
        response = httpx.post(
            "https://www.strava.com/oauth/token",
            data = {
                "client_id": settings.strava_client_id,
                "client_secret": settings.strava_client_secret,
                "grant_type": "refresh_token",
                "refresh_token": user.strava_refresh_token
            }
        )

        
        token_data = response.json()
        user.strava_access_token = token_data["access_token"]
        user.strava_refresh_token = token_data["refresh_token"]
        user.strava_token_expires_at = datetime.fromtimestamp(token_data["expires_at"])
            
        db.commit()
    

def get_strava_activities(user: User, db: Session):
   
    refresh_token_if_needed(user, db)

    headers = {"Authorization": f"Bearer {user.strava_access_token}"}
    activity_response = httpx.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers=headers,
        params={"per_page": 100}
    )
   
    process_activity(activity_response.json(), user, db)
    return activity_response

def process_activity(raw_activity: dict, user: User, db: Session):
    
    for run in raw_activity:
        
        # check if activity already exists to avoid duplicates
        existing = db.query(Activity).filter(Activity.activity_id == run["id"]).first()
        if existing:
            continue
            
        # get heart rate zones
        headers = {"Authorization": f"Bearer {user.strava_access_token}"}
        zones_response = httpx.get(
            f"https://www.strava.com/api/v3/activities/{run['id']}/zones",
            headers=headers,
        )
        zones = zones_response.json()
        
        zone_1 = zone_2 = zone_3 = zone_4 = zone_5 = 0
        for zone_type in zones:
            if zone_type.get("type") == "heartrate":
                buckets = zone_type.get("distribution_buckets", [])
                if len(buckets) >= 5:
                    zone_1 = buckets[0]["time"] / 60
                    zone_2 = buckets[1]["time"] / 60
                    zone_3 = buckets[2]["time"] / 60
                    zone_4 = buckets[3]["time"] / 60
                    zone_5 = buckets[4]["time"] / 60

        new_activity = Activity(
            activity_id=run["id"],
            user_id=user.id,
            date=run["start_date"],
            distance_meters=run["distance"],
            duration_minutes=run["moving_time"] / 60,
            total_elevation_gain=run["total_elevation_gain"],
            average_pace_seconds=(run["moving_time"] / (run["distance"] / 1000)) if run["distance"] > 0 else 0,
            max_heart_rate=run.get("max_heartrate", 0),
            heart_rate_zone_1_minutes=zone_1,
            heart_rate_zone_2_minutes=zone_2,
            heart_rate_zone_3_minutes=zone_3,
            heart_rate_zone_4_minutes=zone_4,
            heart_rate_zone_5_minutes=zone_5,
        )
        
        db.add(new_activity)
    
    db.commit()

    
