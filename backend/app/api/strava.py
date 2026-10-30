from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.UserModel import User
from app.services.strava import StravaError, get_strava_activities

router = APIRouter(prefix="/strava", tags=["Strava"])


# ----------------------------------------------------------------
# The "state" value travels through Strava and comes back to us.
# We sign it so nobody can forge it to attach a Strava account to
# someone else's user. It expires after 10 minutes.
# The claim is called "uid" (not "user_id") on purpose, so this
# token can never be used as a login token.
# ----------------------------------------------------------------
def create_state_token(user_id: int) -> str:
    payload = {
        "uid": user_id,
        "purpose": "strava_oauth",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def read_state_token(state: str) -> Optional[int]:
    try:
        payload = jwt.decode(state, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None
    if payload.get("purpose") != "strava_oauth":
        return None
    return payload.get("uid")


@router.get("/status")
def strava_status(current_user: User = Depends(get_current_user)):
    return {"connected": current_user.strava_access_token is not None}


@router.get("/connect")
def connect_strava(current_user: User = Depends(get_current_user)):
    # Returns the URL as JSON. The frontend sends the user there.
    # (A redirect can't carry the Authorization header from a browser.)
    params = {
        "client_id": settings.strava_client_id,
        "response_type": "code",
        "redirect_uri": settings.strava_redirect_uri,
        "approval_prompt": "force",
        "scope": "activity:read_all",
        "state": create_state_token(current_user.id),
    }
    return {"url": f"https://www.strava.com/oauth/authorize?{urlencode(params)}"}


@router.get("/callback")
def strava_callback(
    state: str,
    code: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    # Strava sends the user's browser here, so we always redirect
    # back to the frontend with a status instead of returning JSON.
    def back_to_frontend(result: str):
        return RedirectResponse(
            f"{settings.frontend_url}/strava/callback?status={result}",
            status_code=302,
        )

    user_id = read_state_token(state)
    if user_id is None:
        return back_to_frontend("invalid_state")

    if error or not code:
        return back_to_frontend("denied")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return back_to_frontend("invalid_state")

    try:
        response = httpx.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": settings.strava_client_id,
                "client_secret": settings.strava_client_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
            timeout=15,
        )
    except httpx.HTTPError:
        return back_to_frontend("strava_unavailable")

    if response.status_code != 200:
        return back_to_frontend("token_exchange_failed")

    token_data = response.json()

    user.strava_access_token = token_data["access_token"]
    user.strava_refresh_token = token_data["refresh_token"]
    user.strava_athlete_id = str(token_data["athlete"]["id"])
    user.strava_token_expires_at = datetime.fromtimestamp(
        token_data["expires_at"], tz=timezone.utc
    )

    db.commit()
    db.refresh(user)

    # We don't import activities here: it takes a while, so the frontend
    # calls /strava/sync next and shows a loading state.
    return back_to_frontend("connected")


@router.get("/sync")
def sync_activities(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.strava_access_token:
        raise HTTPException(status_code=400, detail="Strava is not connected")

    try:
        activities = get_strava_activities(current_user, db)
    except (httpx.HTTPError, StravaError):
        raise HTTPException(status_code=502, detail="Could not fetch activities from Strava")

    return {"activities_found": len(activities)}
