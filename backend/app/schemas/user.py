from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr #to create a schema 


class CreateUser(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    id: Optional[int]=None
