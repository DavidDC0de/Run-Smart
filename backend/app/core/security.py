from sqlachemy import create_engine 
import DATABASE_URL from .env

engine = create_engine(DATABASE_URL)