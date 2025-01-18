from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # Import CORSMiddleware
from pydantic import BaseModel
from app import ResearchAnalyzer
import json
from datetime import datetime

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (replace "*" with your frontend URL in production)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

class ResearchInput(BaseModel):
    domain: str
    project: str
    description: str

@app.post("/analyse")
async def analyse(research_input: ResearchInput):
    analyzer = ResearchAnalyzer(
        groq_api_key="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",
        google_api_key="AIzaSyCGRyC7aXWvHNsG9n8bf0TGBq2thBsncwU",
        google_cse_id="02ecb0c2bcef14fea"
    )
    
    try:
        results = analyzer.analyze(
            domain=research_input.domain,
            project=research_input.project,
            description=research_input.description
        )
        
        return {
            "status": "success",
            "data": results,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def root():
    return {
        "message": "Welcome to the Research Analysis API!",
        "endpoints": {
            "POST /analyse": "Perform research analysis",
            "GET /health": "Check API health"
        }
    }