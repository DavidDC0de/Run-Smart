from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_hostname: str
    database_port: str
    database_password: str
    database_name: str
    database_username: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    strava_client_id: str
    strava_client_secret: str
    strava_redirect_uri: str

    open_ai_key: str

    class Config:
        env_file = ".env"

settings = Settings()