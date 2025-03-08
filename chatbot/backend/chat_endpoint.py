from fastapi import FastAPI, HTTPException, Depends, Body, APIRouter, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from database import SessionLocal
from models import User, ChatThread, Message
from schemas import ChatRequest, ChatResponse, ChatThreadCreate, ChatThread as ChatThreadSchema, Message as MessageSchema
import openai
import logging
from openai_service import OpenAIService
from gemini_service import GeminiService
from services.claude_service import ClaudeService
import os
import traceback
import json
import re  # Add this import for regex operations
import base64
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

openai.api_key = OPENAI_API_KEY

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

# Initialize AI services with the correct API keys
openai_service = OpenAIService(OPENAI_API_KEY)
gemini_service = GeminiService(GEMINI_API_KEY )
claude_service = ClaudeService()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper function to format message for frontend
def format_message_for_frontend(msg):
    return {
        "id": msg.id,
        "role": msg.sender,  # Convert 'sender' to 'role' for frontend
        "content": msg.content,
        "created_at": str(msg.created_at) if hasattr(msg, 'created_at') else None,
    }

# Helper function for title generation
def generate_title_from_message(message_content):
    """Generate a reasonable title from a user message."""
    # Clean the message content
    import re
    
    # Remove special characters, URLs, and extra spaces
    clean_message = re.sub(r'http\S+', '', message_content)
    clean_message = re.sub(r'[^\w\s.,?!-]', ' ', clean_message)
    clean_message = re.sub(r'\s+', ' ', clean_message).strip()
    
    # Try to extract a question as the title
    question_match = re.search(r'^.*?(\w.*?\?)', clean_message)
    if question_match and len(question_match.group(1)) <= 40:
        return question_match.group(1)
    
    # Otherwise use the first sentence or first 40 characters
    first_sentence = re.split(r'[.!?]', clean_message)[0].strip()
    if len(first_sentence) <= 40:
        return first_sentence
    
    return clean_message[:37] + '...' if len(clean_message) > 40 else clean_message

# Remove /chat_api prefix from routes since we're mounting the app under /chat_api in main.py
@app.post("/chat/", response_model=ChatResponse)
async def chat_with_gpt(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        user_id = request.user_id
        user_message = request.message

        # Retrieve or create user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(id=user_id, email=f"user{user_id}@example.com", username=f"User{user_id}")
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.debug(f"Created new user: {user}")

        # Retrieve or create chat thread
        chat_thread = db.query(ChatThread).filter(ChatThread.user_id == user_id).first()
        if not chat_thread:
            chat_thread = ChatThread(user_id=user_id, title="Chat Thread")
            db.add(chat_thread)
            db.commit()
            db.refresh(chat_thread)
            logger.debug(f"Created new chat thread: {chat_thread}")

        # Append user message to chat history
        user_message_entry = Message(thread_id=chat_thread.id, sender="user", content=user_message)
        db.add(user_message_entry)
        db.commit()
        db.refresh(user_message_entry)
        logger.debug(f"Added user message: {user_message_entry}")

        # Retrieve chat history
        chat_history = db.query(Message).filter(Message.thread_id == chat_thread.id).all()
        formatted_history = [{"role": "user" if msg.sender == "user" else "assistant", "content": msg.content} for msg in chat_history]

        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=formatted_history,
            max_tokens=500
        )

        bot_reply = response["choices"][0]["message"]["content"]

        # Append bot response to chat history
        bot_message_entry = Message(thread_id=chat_thread.id, sender="assistant", content=bot_reply)
        db.add(bot_message_entry)
        db.commit()
        db.refresh(bot_message_entry)
        logger.debug(f"Added bot message: {bot_message_entry}")

        return ChatResponse(
            user_id=user_id,
            bot_reply=bot_reply,
            chat_history=formatted_history + [{"role": "assistant", "content": bot_reply}]
        )

    except Exception as e:
        logger.error(f"Error in chat_with_gpt: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/create_thread/", response_model=ChatThreadSchema)
async def create_chat_thread(request: ChatThreadCreate, db: Session = Depends(get_db)):
    try:
        logger.debug(f"Creating thread with data: {request}")
        user_id = request.user_id
        title = request.title

        # Retrieve or create user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(id=user_id, email=f"user{user_id}@example.com", username=f"User{user_id}")
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.debug(f"Created new user: {user}")

        # Create new chat thread
        chat_thread = ChatThread(user_id=user_id, title=title)
        db.add(chat_thread)
        db.commit()
        db.refresh(chat_thread)
        logger.debug(f"Created new chat thread: {chat_thread}")

        return chat_thread
    except Exception as e:
        logger.error(f"Error in create_chat_thread: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error creating thread: {str(e)}")

@app.get("/chat/", response_model=List[ChatThreadSchema])
async def get_chat_threads(user_id: int, search: str = None, show_deleted: bool = False, db: Session = Depends(get_db)):
    try:
        logger.debug(f"Fetching threads for user_id: {user_id}, show_deleted: {show_deleted}, search: {search}")
        
        # Basic query
        query = db.query(ChatThread).filter(ChatThread.user_id == user_id)
        
        # Handle deleted filter - explicitly check for True/False
        if show_deleted is True:
            query = query.filter(ChatThread.is_deleted.is_(True))
        else:
            query = query.filter(ChatThread.is_deleted.is_(False))
            
        # Add search filter if provided
        if search:
            query = query.filter(ChatThread.title.ilike(f"%{search}%"))
            
        # Order by creation date
        query = query.order_by(ChatThread.created_at.desc())
        
        # Execute query
        chat_threads = query.all()
        logger.debug(f"Found {len(chat_threads)} threads")
        
        # Prepare response data
        result = []
        for thread in chat_threads:
            thread_data = {
                "id": thread.id,
                "title": thread.title,
                "user_id": thread.user_id,
                "is_deleted": thread.is_deleted,
                "created_at": str(thread.created_at)
            }
            
            # Get last message if exists
            last_message = db.query(Message).filter(
                Message.thread_id == thread.id
            ).order_by(Message.id.desc()).first()
            
            if last_message:
                thread_data["lastMessage"] = last_message.content[:100]
            
            result.append(thread_data)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in get_chat_threads: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error fetching threads: {str(e)}")

@app.get("/chat/{thread_id}/messages/")
async def get_messages(thread_id: int, user_id: int, db: Session = Depends(get_db)):
    try:
        chat_thread = db.query(ChatThread).filter(ChatThread.id == thread_id, ChatThread.user_id == user_id).first()
        if not chat_thread:
            raise HTTPException(status_code=404, detail="Chat thread not found")
        
        messages = db.query(Message).filter(Message.thread_id == thread_id).all()
        
        # Format messages for frontend
        formatted_messages = [format_message_for_frontend(msg) for msg in messages]
        logger.debug(f"Returning formatted messages: {formatted_messages}")
        
        return formatted_messages
    except Exception as e:
        logger.error(f"Error in get_messages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching messages: {str(e)}")

@app.post("/chat/{thread_id}/message/")
async def send_message(thread_id: int, request: dict = Body(...), db: Session = Depends(get_db)):
    """Send a message and get a response from the selected AI model"""
    
    try:
        user_id = request.get("user_id")
        user_message = request.get("message")
        model = request.get("model", "openai").lower()  # Default to OpenAI if not specified
        update_title = request.get("update_title", False)
        suggested_title = request.get("suggested_title", None)

        # Log the selected model with more visibility
        logger.info(f"⭐ MESSAGE REQUEST with MODEL: {model} ⭐")

        # Retrieve chat thread
        chat_thread = db.query(ChatThread).filter(ChatThread.id == thread_id, ChatThread.user_id == user_id).first()
        if not chat_thread:
            raise HTTPException(status_code=404, detail="Chat thread not found")

        # Append user message to chat history
        user_message_entry = Message(thread_id=chat_thread.id, sender="user", content=user_message)
        db.add(user_message_entry)
        db.commit()
        db.refresh(user_message_entry)
        logger.debug(f"Added user message: {user_message_entry}")

        # Check if we need to update the thread title
        if update_title or (chat_thread.title in ["New Chat", "New Conversation"]):
            new_title = suggested_title if suggested_title else generate_title_from_message(user_message)
            chat_thread.title = new_title
            db.commit()
            logger.debug(f"Updated thread title to: {new_title}")

        # Retrieve updated chat history
        chat_history = db.query(Message).filter(Message.thread_id == chat_thread.id).all()
        formatted_history = [{"role": "user" if msg.sender == "user" else "assistant", "content": msg.content} for msg in chat_history]

        # Generate response with appropriate model
        logger.info(f"🔴 GENERATING RESPONSE WITH MODEL: {model.upper()} 🔴")
        bot_reply = None
        
        try:
            if model == "gemini":
                logger.info("Using Gemini service for response generation")
                bot_reply = gemini_service.generate_response(formatted_history)
            elif model == "claude":
                logger.info("Using Claude service for response generation")
                bot_reply = claude_service.generate_response(formatted_history)
                logger.info("Claude response first 50 chars: " + bot_reply[:50])
            else:
                logger.info("Using OpenAI service for response generation")
                bot_reply = openai_service.generate_response(formatted_history)
                
            # Verify the response model matches the requested model
            if model == "claude" and not any(marker in bot_reply.lower() for marker in ["claude", "anthropic", "as claude", "i'm claude"]):
                logger.warning("⚠️ Claude response does not identify as Claude - forcing identification")
                bot_reply = "As Claude, I'd like to answer your question: " + bot_reply
                
            logger.info(f"✅ Successfully generated response with {model}")
        except Exception as e:
            logger.error(f"❌ Error generating response with {model} model: {str(e)}")
            # Fall back to alternative model if first choice fails
            try:
                # Try a different model if the requested one fails
                if model != "openai":
                    logger.info("Falling back to OpenAI service")
                    bot_reply = openai_service.generate_response(formatted_history)
                    model = "openai (fallback)"
                else:
                    # Try Claude as secondary fallback since it might be more reliable than Gemini
                    logger.info("Falling back to Claude service")
                    bot_reply = claude_service.generate_response(formatted_history)
                    model = "claude (fallback)"
            except Exception as fallback_error:
                logger.error(f"Fallback model also failed: {str(fallback_error)}")
                # Use rule-based fallback
                bot_reply = "I apologize, but I'm having trouble generating a response right now. Please try again later."
                model = "error-fallback"

        # Record bot response with model information
        bot_message_entry = Message(
            thread_id=chat_thread.id, 
            role="assistant", 
            sender="assistant",
            content=bot_reply,
            model=model  # Store which model generated this response
        )
        db.add(bot_message_entry)
        db.commit()
        db.refresh(bot_message_entry)
        logger.info(f"🟢 Added bot message with model {model}")

        # Get all messages including the new ones
        all_messages = db.query(Message).filter(Message.thread_id == thread_id).all()
        formatted_messages = [format_message_for_frontend(msg) for msg in all_messages]
        
        return formatted_messages
    except Exception as e:
        logger.error(f"Error in send_message: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/chat/{thread_id}/update/")
async def update_thread(thread_id: int, request: ChatThreadCreate, db: Session = Depends(get_db)):
    try:
        chat_thread = db.query(ChatThread).filter(
            ChatThread.id == thread_id,
            ChatThread.user_id == request.user_id
        ).first()
        
        if not chat_thread:
            raise HTTPException(status_code=404, detail="Chat thread not found")
            
        # Clean the title but don't truncate it
        chat_thread.title = request.title.strip()
        db.commit()
        db.refresh(chat_thread)
        return chat_thread
    except Exception as e:
        logger.error(f"Error updating thread: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/chat/{thread_id}/message/{message_id}/")
async def update_message(thread_id: int, message_id: int, request: dict = Body(...), db: Session = Depends(get_db)):
    try:
        # Verify the message belongs to the user and thread
        message = db.query(Message).filter(
            Message.id == message_id,
            Message.thread_id == thread_id,
            Message.sender == "user"  # Only allow editing user messages
        ).first()
        
        if not message:
            raise HTTPException(status_code=404, detail="Message not found or cannot be edited")
            
        # Delete all messages that come after this message
        db.query(Message).filter(
            Message.thread_id == thread_id,
            Message.id > message_id
        ).delete()
        
        # Update the user message content
        message.content = request.get("message")
        db.commit()
        db.refresh(message)
        
        # Get all messages up to this point for the AI context
        chat_history = db.query(Message).filter(
            Message.thread_id == thread_id,
            Message.id <= message_id
        ).order_by(Message.id).all()
        
        # Format messages for OpenAI API
        formatted_history = [
            {"role": "user" if msg.sender == "user" else "assistant", "content": msg.content}
            for msg in chat_history
        ]
        
        # Generate new assistant response based on selected model with better error handling
        model = request.get("model", "openai")  # Get model preference, default to OpenAI
        logger.info(f"Updating message with model: {model}")
        
        try:
            if model == "gemini":
                logger.info("Using Gemini service for response generation")
                bot_reply = gemini_service.generate_response(formatted_history)
            elif model == "claude":
                logger.info("Using Claude service for response generation")
                bot_reply = claude_service.generate_response(formatted_history)
            else:
                logger.info("Using OpenAI service for response generation")
                bot_reply = openai_service.generate_response(formatted_history)
        except Exception as e:
            logger.error(f"Error generating response with {model} model: {str(e)}")
            # Fall back to alternative model if first choice fails
            try:
                if model == "gemini":
                    logger.info("Falling back to OpenAI service")
                    bot_reply = openai_service.generate_response(formatted_history)
                    model = "openai (fallback)"
                else:
                    logger.info("Falling back to Claude service")
                    bot_reply = claude_service.generate_response(formatted_history)
                    model = "claude (fallback)"
            except Exception as fallback_error:
                logger.error(f"Fallback model also failed: {str(fallback_error)}")
                from alternatives import get_rule_based_response
                # Get the last user message
                last_user_message = message.content
                bot_reply = get_rule_based_response(last_user_message)
                model = "rule-based (fallback)"
        
        # Add the new bot response with model information
        new_bot_message = Message(
            thread_id=thread_id,
            role="assistant",
            sender="assistant",
            content=bot_reply,
            model=model  # Store which model generated this response
        )
        db.add(new_bot_message)
        db.commit()
        db.refresh(new_bot_message)
        
        # Get all updated messages in order
        all_messages = db.query(Message).filter(
            Message.thread_id == thread_id
        ).order_by(Message.id).all()
        
        return [format_message_for_frontend(msg) for msg in all_messages]
        
    except Exception as e:
        logger.error(f"Error updating message: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/chat/{thread_id}/delete/")
async def delete_thread(thread_id: int, user_id: int, db: Session = Depends(get_db)):
    try:
        chat_thread = db.query(ChatThread).filter(
            ChatThread.id == thread_id,
            ChatThread.user_id == user_id
        ).first()
        
        if not chat_thread:
            raise HTTPException(status_code=404, detail="Chat thread not found")
            
        # Instead of deleting, set the is_deleted flag
        chat_thread.is_deleted = True
        db.commit()
        
        return {"message": "Thread marked as deleted"}
    except Exception as e:
        logger.error(f"Error deleting thread: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/{thread_id}/restore/")
async def restore_thread(thread_id: int, user_id: int, db: Session = Depends(get_db)):
    try:
        chat_thread = db.query(ChatThread).filter(
            ChatThread.id == thread_id,
            ChatThread.user_id == user_id,
            ChatThread.is_deleted.is_(True)
        ).first()
        
        if not chat_thread:
            raise HTTPException(status_code=404, detail="Deleted thread not found")
            
        # Explicitly set is_deleted to False
        chat_thread.is_deleted = False
        db.commit()
        db.refresh(chat_thread)
        
        return chat_thread
    except Exception as e:
        logger.error(f"Error restoring thread: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    return {"message": "FastAPI Chatbot is running!"}

@app.post("/analyze_image/")
async def analyze_image(image: UploadFile = File(...), model: str = Form("gemini")):
    """Analyze an image using Gemini or OpenAI with improved error handling"""
    try:
        # Read image file
        contents = await image.read()
        
        # Log basic info about the image
        file_size = len(contents) / 1024
        file_type = image.content_type or "unknown"
        logger.info(f"Image upload received: {image.filename}, {file_size:.1f} KB, type: {file_type}")
        
        # Import utilities
        import base64
        import traceback
        from PIL import Image
        from io import BytesIO
        from main import image_analyzer
        
        # Validate and optimize the image
        try:
            # Check if it's a valid image
            img = Image.open(BytesIO(contents))
            width, height = img.size
            format_name = img.format
            logger.info(f"Valid image: {width}x{height} {format_name}")
            
            # Convert to RGB if needed
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
                
                # Convert back to bytes
                output = BytesIO()
                img.save(output, format="JPEG", quality=90)
                contents = output.getvalue()
                logger.info("Converted image to RGB format")
        except Exception as img_err:
            logger.error(f"Invalid image format: {str(img_err)}")
        
        # Try first with specified model
        preferred_model = model.lower()
        logger.info(f"Attempting analysis with {preferred_model}")
        
        try:
            # Process image with appropriate timeout
            image_base64, analysis = await image_analyzer.analyze_image(
                contents,
                preferred_model=preferred_model
            )
            
            # Check if we got a proper analysis
            if "error" not in analysis and analysis.get("description") and "couldn't analyze" not in analysis.get("description", ""):
                logger.info(f"Image analyzed successfully with {preferred_model}")
            else:
                logger.warning(f"{preferred_model} analysis failed, trying fallback with OpenAI")
                image_base64, analysis = await image_analyzer.analyze_image(
                    contents,
                    preferred_model="openai"
                )
            
            # Ensure all expected fields exist in the analysis
            if "description" not in analysis or not analysis["description"]:
                analysis["description"] = "This appears to be an image, but I couldn't analyze it in detail."
                
            if "labels" not in analysis or not analysis["labels"]:
                analysis["labels"] = ["image"]

            if "objects" not in analysis:
                analysis["objects"] = []
                
            if "text" not in analysis:
                analysis["text"] = ""
                
            logger.info(f"Returning analysis: {analysis['description'][:100]}...")
            
            # Explicitly structure the response in the expected format
            return {
                "image_base64": image_base64,
                "analysis": {
                    "description": analysis["description"],
                    "labels": analysis["labels"],
                    "objects": analysis["objects"],
                    "text": analysis["text"],
                    "faces": analysis.get("faces", 0)
                }
            }
            
        except Exception as analysis_error:
            logger.error(f"Image analysis error: {str(analysis_error)}")
            logger.error(traceback.format_exc())
            
            # Try direct Gemini analysis as a last resort
            try:
                from gemini_service import GeminiService
                
                gemini = GeminiService()
                image_base64 = base64.b64encode(contents).decode('utf-8')
                description = gemini.analyze_image(image_base64)
                
                return {
                    "image_base64": image_base64,
                    "analysis": {
                        "description": description,
                        "labels": ["image"],
                        "faces": 0,
                        "text": "",
                        "objects": []
                    }
                }
            except Exception as gemini_err:
                logger.error(f"Direct Gemini analysis failed: {str(gemini_err)}")
        
        # Return a fallback response if all methods fail
        image_base64 = base64.b64encode(contents).decode('utf-8')
        return {
            "image_base64": image_base64,
            "analysis": {
                "description": "I can see your image, but I'm currently experiencing technical issues with the image analysis service. Please try again later.",
                "labels": ["image"],
                "text": "",
                "objects": [],
                "faces": 0
            }
        }
            
    except Exception as e:
        logger.error(f"Image upload error: {str(e)}")
        logger.error(traceback.format_exc())
        
        raise HTTPException(status_code=500, detail=f"Image processing failed: {str(e)}")

@app.post("/upload-image/")
async def upload_image(file: UploadFile = File(...), model: str = Form(...), db: Session = Depends(get_db)):
    try:
        # Read image data
        image_data = await file.read()
        encoded_image = base64.b64encode(image_data).decode('utf-8')
        
        # Process with the appropriate model
        analysis = None
        model = model.lower()
        
        logger.info(f"Processing image with model: {model}")
        
        if model == "gemini":
            logger.info("Using Gemini for image analysis")
            analysis = gemini_service.analyze_image(encoded_image)
        elif model == "claude":
            logger.info("Using Claude for image analysis")
            analysis = claude_service.analyze_image(encoded_image)
        else:
            logger.warning(f"Unsupported model for image analysis: {model}")
            raise HTTPException(status_code=400, detail="Selected model doesn't support image analysis")
        
        # Check if analysis was successful
        if not analysis or "error" in analysis.lower():
            logger.warning(f"Analysis failed: {analysis}")
            raise HTTPException(status_code=500, detail=f"Failed to analyze image: {analysis}")
        
        return {
            "success": True,
            "analysis": analysis,
            "filename": file.filename
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze_document/")
async def analyze_document(
    document: UploadFile = File(...),
    model: str = Form("gemini"),
    filename: str = Form(None)
):
    """Analyze a document (PDF, DOC, TXT) with AI model capabilities"""
    try:
        # Read document file
        contents = await document.read()
        
        # Log basic info about the document
        file_size = len(contents) / 1024
        file_type = document.content_type or "unknown"
        logger.info(f"Document upload received: {filename or document.filename}, {file_size:.1f} KB, type: {file_type}")
        
        # Process different document types
        text_content = ""
        
        if file_type == "application/pdf":
            # For PDF files
            try:
                from PyPDF2 import PdfReader
                from io import BytesIO
                
                pdf = PdfReader(BytesIO(contents))
                for page in pdf.pages:
                    text_content += page.extract_text() + "\n\n"
            except Exception as e:
                logger.error(f"PDF extraction error: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Cannot process PDF: {str(e)}")
                
        elif file_type.startswith("text/"):
            # For text files
            try:
                text_content = contents.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text_content = contents.decode('latin-1')
                except:
                    raise HTTPException(status_code=400, detail="Unable to decode text file")
        
        elif "word" in file_type:
            # For Word documents
            try:
                import docx
                from io import BytesIO
                
                doc = docx.Document(BytesIO(contents))
                text_content = "\n".join([para.text for para in doc.paragraphs])
            except Exception as e:
                logger.error(f"Word document extraction error: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Cannot process Word document: {str(e)}")
        
        else:
            # Unsupported document type
            raise HTTPException(status_code=400, detail=f"Unsupported document type: {file_type}")
        
        # Summarize text content if too long
        if len(text_content) > 8000:
            summary_text = text_content[:8000] + "... [content truncated]"
        else:
            summary_text = text_content
            
        # Use selected AI model to analyze the document
        try:
            # Choose the appropriate AI service based on model parameter
            analysis = None
            
            if model == "gemini":
                analysis = gemini_service.generate_response([
                    {"role": "user", "content": f"Please analyze this document: {summary_text}"}
                ])
            elif model == "claude":
                analysis = claude_service.generate_response([
                    {"role": "user", "content": f"Please analyze this document: {summary_text}"}
                ])
            else:
                analysis = openai_service.generate_response([
                    {"role": "user", "content": f"Please analyze this document: {summary_text}"}
                ])
            
            # Extract key points
            key_points = extract_key_points(analysis)
            
            # Return in same format as image analysis for consistency
            doc_base64 = base64.b64encode(contents).decode('utf-8')
            
            return {
                "image_base64": doc_base64,  # Using same field name for consistency
                "analysis": {
                    "description": analysis,
                    "labels": key_points[:3],  # Top 3 points as labels
                    "text": summary_text[:500] + "..." if len(summary_text) > 500 else summary_text,
                    "objects": [],  # No objects in documents
                    "document_type": file_type
                },
                "success": True  # Additional field for backward compatibility
            }
            
        except Exception as e:
            logger.error(f"AI analysis error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error analyzing document: {str(e)}")
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Document processing error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

def extract_key_points(analysis_text):
    """Extract key points from AI analysis output"""
    # Simple extraction - look for bullet points or numbered lists
    key_points = []
    
    # Look for lines starting with bullet markers or numbers
    for line in analysis_text.split('\n'):
        line = line.strip()
        if line.startswith('•') or line.startswith('-') or line.startswith('*'):
            key_points.append(line.lstrip('•-* '))
        elif re.match(r'^\d+\.', line):
            key_points.append(re.sub(r'^\d+\.\s*', '', line))
    
    # If no bullet points found, try to extract sentences with important keywords
    if not key_points:
        important_keywords = ['important', 'key', 'significant', 'main', 'primary', 'critical']
        sentences = re.split(r'[.!?]+', analysis_text)
        for sentence in sentences:
            sentence = sentence.strip()
            if any(keyword in sentence.lower() for keyword in important_keywords) and len(sentence) > 20:
                key_points.append(sentence)
    
    # If still no key points, just split by sentences and take first few
    if not key_points and analysis_text:
        sentences = re.split(r'[.!?]+', analysis_text)
        key_points = [s.strip() for s in sentences if len(s.strip()) > 20][:5]
    
    # Limit to top 5 key points
    return key_points[:5] if key_points else ["Document analysis available"]
