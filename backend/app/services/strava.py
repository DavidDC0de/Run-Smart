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
    response = httpx.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers=headers,
        params={"per_page": 100}
    )

    return response

def process_activity(raw_activity: dict, user_id: int):
    # convert raw Strava fields to your table fields
    # distance meters to km
    # moving_time seconds to minutes
    # calculate pace from speed
    # return Activity object ready to save
    pass

def sync_all_activities(user: User, db: Session):
    # call get_strava_activities
    # loop through each one
    # call process_activity on each
    # save to database
    # skip if activity_id already exists to avoid duplicates
    pass



'''
{"https://www.strava.com/api/v3/activities/130058894?include_all_efforts=true"}
{
    "id"
    "start_date"
    "distance"
    "moving_time"
    "total_elevation_gain"
    "average_speed" #m/sec
}
{"$ http get "https://www.strava.com/api/v3/activities/{id}/zones" "Authorization: Bearer [[token]]""} #not sure how to find how much time was spent in each zone

[ {
  "score" : 0,
  "sensor_based" : true,
  "custom_zones" : true,
  "max" : 1,
  "distribution_buckets" : "",
  "type" : "heartrate",
  "points" : 6
} ]
'''

#after that is activity_type there is no way to get that from strava so when initially loading all info its all gonna be just 
#blank ... i will need to figure out a way to tell what is a long run, easy run, tempo and all that 
#that way if a user wants to change their programm and feed it back inot the ai the ai can see what was an easy run or a tempo and so on...

#next field is percieved effort this ties in with activity type, i think when i originally save the data from strava it will be blank
#however if this is a run which was done on my app where users can selct the effort i will save that localluy for a bit and then add it to the table
#meaning that i can do the same with activity type

#next field is created at, this will stay blank for all the strava initial connect but then i can add this with every new run that was done through my app
