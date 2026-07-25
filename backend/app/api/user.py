from fastapi import APIRouter, Depends, FastAPI, status, HTTPException
from app.schemas.UserSchema import CreateUser, Token, UserOut
from app.core.database import get_db
from app.core.security import hash_password, verify_password, verify_password, create_access_token
from app.models import UserModel
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/user"
)

@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def user_signup(user: CreateUser, db: Session = Depends(get_db) ):
    
        
    existing_user = db.query(UserModel.User).filter(UserModel.User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    

    hashed_password = hash_password(user.password)
    user.password = hashed_password  

    new_user = UserModel.User(**user.dict())  
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
def user_login(user_credentials: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    
    user = db.query(UserModel.User).filter(
        UserModel.User.email == user_credentials.username).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Invalid Credentials!")
    
    if not verify_password(user_credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Invalid Credentials")
    
    access_token = create_access_token(data={"user_id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}
