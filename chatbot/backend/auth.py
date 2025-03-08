from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from database import SessionLocal, engine, Base
from models import User
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
GOOGLE_CLIENT_ID=os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET=os.getenv("GOOGLE_CLIENT_SECRET")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES =  os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class GoogleLoginRequest(BaseModel):
    token: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
        
    # Update login method for email login
    if user.login_method != 'email':
        user.login_method = 'email'
        db.commit()
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "login_method": user.login_method
    }

@router.get("/users/me")
async def read_users_me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "display_name": getattr(user, "display_name", user.username)  # Fallback to username
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/validate-token")
async def validate_token(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
            
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
            
        # Update token expiration
        new_token = create_access_token(
            data={"sub": email, "login_method": user.login_method},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        return {
            "valid": True,
            "access_token": new_token,
            "user": {
                "email": user.email,
                "display_name": user.display_name,
                "username": user.username
            }
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/google-login")
async def google_login(request: GoogleLoginRequest, db: Session = Depends(get_db)):
    try:
        # Verify the Google token with clock skew allowance
        idinfo = id_token.verify_oauth2_token(
            request.token,
            requests.Request(),
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10
        )
        
        # Debug logging
        print(f"Google token verification successful. Token info: {idinfo.get('sub')[:5]}...")
        
        if idinfo['aud'] != GOOGLE_CLIENT_ID:
            print(f"Token audience mismatch: {idinfo.get('aud')} != {GOOGLE_CLIENT_ID}")
            raise ValueError('Wrong audience.')
            
        email = idinfo['email']
        if not email:
            raise ValueError('Email not found in token')
            
        # Get user details
        profile_image = idinfo.get('picture', '')
        given_name = idinfo.get('given_name', '')
        full_name = idinfo.get('name', '')
        
        # Find or create user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            # Create user with basic attributes
            user = User(
                email=email,
                username=full_name or email.split('@')[0]
            )
            
            # Try to set display_name if the model supports it
            try:
                user.display_name = given_name or full_name
            except AttributeError:
                print("User model doesn't have display_name attribute, skipping")
                
            # Try to set login_method if the model supports it
            try:
                user.login_method = 'google'
            except AttributeError:
                print("User model doesn't have login_method attribute, skipping")
                
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Try to update login_method if the model supports it
            try:
                if user.login_method != 'google':
                    user.login_method = 'google'
                    db.commit()
            except AttributeError:
                print("User model doesn't have login_method attribute, skipping")
        
        # Create access token with proper type conversion for expiration
        access_token = create_access_token(
            data={"sub": user.email, "login_method": getattr(user, "login_method", "google")},
            expires_delta=timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES or 15))
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "profile_image": profile_image,
            "username": full_name,
            "display_name": getattr(user, "display_name", user.username),  # Safely get display_name
            "email": email,
            "login_method": getattr(user, "login_method", "google")  # Safely get login_method
        }
        
    except ValueError as e:
        print(f"Google login error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        print(f"Unexpected error during Google login: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail="Internal server error during authentication"
        )
