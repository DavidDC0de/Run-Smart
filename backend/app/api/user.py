from fastapi import APIRouter, Depends, FastAPI, status, HTTPException
from app.schemas.UserSchema import CreateUser, UserOut
from app.core.database import get_db
from app.core.security import hash_password
from app.models import UserModel

router = APIRouter(
    prefix="/user"
)

@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def user_signup(user: CreateUser, db: status = Depends(get_db) ):
    
        
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