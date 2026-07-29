from fastapi import FastAPI
from app.api import user, strava


app = FastAPI()

app.include_router(user.router)
app.include_router(strava.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}