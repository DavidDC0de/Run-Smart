from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.UserModel import User
import httpx

router = APIRouter(prefix="/strava", tags=["strava"])
#current_user: User = Depends(get_current_user)
@router.get("/connect")
def connect_strava():
    strava_auth_url = (
        f"https://www.strava.com/oauth/authorize"   #strava oauth
        f"?client_id={settings.strava_client_id}"   #which app is requesting the data
        f"&redirect_uri=http://localhost:8000/strava/callback"   #redirect user
        f"&response_type=code"   #request code back from strava
        f"&scope=activity:read_all"   #permission
    )
    return RedirectResponse(strava_auth_url)


@router.get("/callback")
def strava_callback(code: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    
    # Exchange code for tokens
    response = httpx.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": settings.strava_client_id,
            "client_secret": settings.strava_client_secret,
            "code": code,
            "grant_type": "authorization_code"
        }
    )
    
    token_data = response.json()
    
    # Save tokens to user in database
    current_user.strava_access_token = token_data["access_token"]
    current_user.strava_refresh_token = token_data["refresh_token"]
    current_user.strava_athlete_id = str(token_data["athlete"]["id"])
    
    db.commit()
    
    return {"message": "Strava connected successfully"}