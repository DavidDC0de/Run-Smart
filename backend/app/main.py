from fastapi import FastAPI
from app.api import user, strava, plans


app = FastAPI()

app.include_router(user.router)
app.include_router(strava.router)
app.include_router(plans.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}