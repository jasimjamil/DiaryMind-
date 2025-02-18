from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime
import requests
from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from pathlib import Path


app = FastAPI()

# Hugging Face API details
HF_API_URL = "https://api-inference.huggingface.co/models/facebook/blenderbot-400M-distill"
HF_HEADERS = {"Authorization": "Bearer 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"}

# Database setup (SQLite)
DATABASE_URL = "sqlite:///./memory_chatbot.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class DiaryEntryDB(Base):
    __tablename__ = "diary_entries"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    content = Column(Text)
    date = Column(DateTime, default=datetime.utcnow)

class MemoryExerciseDB(Base):
    __tablename__ = "memory_exercises"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    image_url = Column(String)
    correct_name = Column(String)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic Models for API
class DiaryEntry(BaseModel):
    user_id: str
    content: str
    date: datetime = datetime.utcnow()

class MemoryExercise(BaseModel):
    user_id: str
    image_url: str
    correct_name: str

class ChatbotRequest(BaseModel):
    user_input: str

# Dependency: Database Session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API Endpoints
@app.post("/write-diary/")
def write_diary(entry: DiaryEntry, db=Depends(get_db)):
    db_entry = DiaryEntryDB(**entry.dict())
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return {"message": "Diary entry saved!", "id": db_entry.id}

@app.get("/read-diary/{user_id}")
def read_diary(user_id: str, db=Depends(get_db)):
    entries = db.query(DiaryEntryDB).filter(DiaryEntryDB.user_id == user_id).all()
    return [{"id": entry.id, "content": entry.content, "date": entry.date} for entry in entries]

@app.post("/memory-exercise/")
def memory_exercise(exercise: MemoryExercise, db=Depends(get_db)):
    db_exercise = MemoryExerciseDB(**exercise.dict())
    db.add(db_exercise)
    db.commit()
    return {"message": "Memory exercise saved!"}

@app.post("/chatbot/")
def chatbot_response(chatbot_request: ChatbotRequest):
    user_input = chatbot_request.user_input
    try:
        # Sending request to Hugging Face API
        response = requests.post(HF_API_URL, headers=HF_HEADERS, json={"inputs": user_input})
        response.raise_for_status()  # Will raise an exception for 4xx/5xx responses
        
        # Return the chatbot response
        return response.json()
    
    except requests.exceptions.RequestException as e:
        # Log the error and return a more specific message
        print(f"Error contacting Hugging Face API: {e}")
        raise HTTPException(status_code=500, detail=f"Error contacting Hugging Face API: {e}")

# Serve static files (Frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve the HTML file directly
@app.get("/")
async def serve_frontend():
    return FileResponse(Path("static") / "main.html")

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

