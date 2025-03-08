from fastapi import FastAPI, Depends, HTTPException, Request, File, UploadFile
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from database import SessionLocal, engine, Base
from models import User, Message, ChatThread
from auth import router as auth_router
import openai
from datetime import timedelta, datetime
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import logging
import os
from openai_service import OpenAIService
from gemini_service import GeminiService
from fastapi.responses import JSONResponse
import traceback
from chat_endpoint import app as chat_app
from google.oauth2 import id_token
from google.auth.transport import requests
import base64
from PIL import Image
import io
from image_analyzer import ImageAnalyzer


from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import the logging config
from logging_config import setup_logging

# Initialize enhanced logging
loggers = setup_logging()
logger = loggers["main"]
model_logger = loggers["model"]

logger.info("Starting application with enhanced logging")

# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Include the chat endpoint with explicit prefix
app.mount("/chat_api", chat_app)

# OAuth2 setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
GOOGLE_CLIENT_ID=os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET=os.getenv("GOOGLE_CLIENT_SECRET")

# Environment variables
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Set OpenAI API key
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
openai.api_key = OPENAI_API_KEY

# Initialize OpenAI service
openai_service = OpenAIService(OPENAI_API_KEY)

# Initialize Gemini service
gemini_service = GeminiService(os.environ.get("GEMINI_API_KEY"))

# Set default image analysis model to Gemini
os.environ["PREFERRED_IMAGE_MODEL"] = "gemini"

# Initialize our own ImageAnalyzer with both services
image_analyzer = ImageAnalyzer(
    openai_service=openai_service,
    gemini_service=gemini_service,
    vision_api_key=os.environ.get("GOOGLE_VISION_API_KEY")
)

# Request models
class MessageRequest(BaseModel):
    sender: str
    content: str

class GoogleLoginRequest(BaseModel):
    token: str

# CORS setup with explicit origins
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Update CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Middleware to log all requests for debugging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug(f"Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    logger.debug(f"Response status: {response.status_code}")
    return response

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

@app.get("/")
async def root():
    return {"message": "Welcome to the ChatBot API"}

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == form_data.username).first()
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect email or password")
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

@app.post("/google-login", response_model=dict)
async def google_login(request: GoogleLoginRequest, db: Session = Depends(get_db)):
    try:
        logger.debug(f"Received Google login request")
        
        # Add clock skew parameter to handle time synchronization issues
        idinfo = id_token.verify_oauth2_token(
            request.token,
            requests.Request(),
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10  # Allow 10 seconds of clock skew
        )
        
        # Log token info for debugging (excluding sensitive data)
        logger.debug(f"Token verified. Subject: {idinfo.get('sub')}, Issuer: {idinfo.get('iss')}")
        
        if idinfo.get('aud') != GOOGLE_CLIENT_ID:
            logger.error(f"Token audience mismatch: {idinfo.get('aud')} != {GOOGLE_CLIENT_ID}")
            raise ValueError('Wrong audience.')
            
        if 'email' not in idinfo:
            logger.error("Email not found in token")
            raise ValueError('Email not found in token')
            
        email = idinfo['email']
        picture = idinfo.get('picture')
        name = idinfo.get('name', email.split('@')[0])
        given_name = idinfo.get('given_name', '')
        
        # Find or create user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            # Create minimal user - don't include display_name if it's not in the model
            try:
                user = User(
                    email=email,
                    username=name,
                    login_method='google'
                )
                # Try to set display_name if model supports it
                try:
                    user.display_name = given_name or name
                except AttributeError:
                    logger.info("User model doesn't have display_name attribute, skipping")
                
                db.add(user)
                db.commit()
                db.refresh(user)
                logger.debug(f"Created new user: {user.email}")
            except Exception as e:
                logger.error(f"Error creating user: {str(e)}")
                raise
        elif hasattr(user, 'login_method') and user.login_method != 'google':
            # Update login method for existing users if the field exists
            user.login_method = 'google'
            db.commit()

        # Create access token
        access_token_expires = timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES or 15))
        access_token = create_access_token(
            data={"sub": user.email, "login_method": "google" if hasattr(user, 'login_method') else None},
            expires_delta=access_token_expires
        )

        # Safely get display_name or fall back to username
        display_name = getattr(user, 'display_name', user.username)
        login_method = getattr(user, 'login_method', 'google')
        
        logger.debug(f"Login successful for user: {user.email}")
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "profile_image": picture,
            "username": user.username,
            "display_name": display_name,
            "email": user.email,
            "login_method": login_method
        }
    except ValueError as e:
        error_msg = str(e)
        logger.error(f"Google login validation error: {error_msg}")
        raise HTTPException(status_code=400, detail=f"Invalid token: {error_msg}")
    except Exception as e:
        logger.error(f"Google login error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error during authentication")

@app.get("/users/me")
async def read_users_me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
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
            "username": user.username
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/debug-google-login")
async def debug_google_login(request: GoogleLoginRequest):
    """Debug endpoint to check what's being received from the frontend"""
    logger.debug(f"Received request body: {request}")
    return {"received": request.token}

@app.get("/api_test")
async def api_test():
    """Test endpoint to verify API is working"""
    return {
        "status": "ok",
        "endpoints": [
            {"path": "/chat_api/analyze_image/", "method": "POST", "description": "Analyze image"}
        ],
        "services": {
            "openai": openai_service is not None,
            "gemini": gemini_service is not None,
            "image_analyzer": image_analyzer is not None 
        }
    }

# Include auth router for SSO functionality
app.include_router(auth_router, prefix="")
