from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from app.services.strava import get_strava_activities
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.UserModel import User
import httpx
from datetime import datetime

router = APIRouter(prefix="/strava", tags=["Strava"])


@router.get("/connect")
def connect_strava(current_user: User = Depends(get_current_user)):
    strava_auth_url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={settings.strava_client_id}"
        "&response_type=code"
        f"&redirect_uri={settings.strava_redirect_uri}"
        "&approval_prompt=force"
        "&scope=activity:read_all"
        f"&state={current_user.id}"
    )
    return RedirectResponse(strava_auth_url)

'''
FOR TESTING ONLY:
@router.get("/connect")
def connect_strava(token: str, db: Session = Depends(get_db)):
    from app.core.security import verify_access_token
    from fastapi import HTTPException, status
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    user_id = verify_access_token(token, credentials_exception)
    
    strava_auth_url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={settings.strava_client_id}"
        "&response_type=code"
        f"&redirect_uri={settings.strava_redirect_uri}"
        "&approval_prompt=force"
        "&scope=activity:read_all"
        f"&state={user_id.id}"
    )
    return RedirectResponse(strava_auth_url)
'''

@router.get("/callback")
def strava_callback(code: str, state: int, db: Session = Depends(get_db)):
    user_id = int(state)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
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
    
    user.strava_access_token = token_data["access_token"]
    user.strava_refresh_token = token_data["refresh_token"]
    user.strava_athlete_id = str(token_data["athlete"]["id"])
    user.strava_token_expires_at = datetime.fromtimestamp(token_data["expires_at"])
    
    db.commit()
    db.refresher(user)

    activities = get_strava_activities(user, db)
    
    return {"message": "Strava connected successfully", "activities found:": len(activities)}

@router.get("/sync")
def sync_activities(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    activities = get_strava_activities(current_user, db)
    
    return {"activities_found": str(activities)}