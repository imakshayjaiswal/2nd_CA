import os
import json
import time
import re
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="The Viral-Loop Architect API")

# Setup Nvidia OpenAI Wrapper Configuration
API_KEY = os.getenv("API_KEY", "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")
client = OpenAI(
  base_url="https://integrate.api.nvidia.com/v1",
  api_key=API_KEY
)
MODEL_NAME = "meta/llama-3.1-70b-instruct"

# ==========================================
# Data Models Structure (FastAPI)
# ==========================================
class AnalyzeRequest(BaseModel):
    source: str         # "text" or "url"
    transcript: str = ""
    yt_url: str = ""
    platform: str
    vibe: str

# ==========================================
# Helper Modules
# ==========================================
def extract_youtube_id(url: str) -> str:
    if "youtu.be" in url:
        return url.split("/")[-1].split("?")[0]
    elif "youtube.com" in url:
        if "v=" in url:
            return url.split("v=")[1].split("&")[0]
        elif "embed/" in url:
            return url.split("embed/")[1].split("?")[0]
    return ""

def fetch_youtube_transcript(url: str) -> str:
    video_id = extract_youtube_id(url)
    if not video_id:
        raise ValueError("Invalid YouTube URL.")
    try:
        ts = YouTubeTranscriptApi().fetch(video_id)
        formatter = TextFormatter()
        return formatter.format_transcript(ts)
    except Exception as e:
        raise ValueError(f"Failed to fetch transcript: {e}")

# ==========================================
# AI Pipeline Functions
# ==========================================
def robust_generate(prompt, temperature=0.7, retries=3):
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=2048,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                time.sleep(10)
                continue
            raise Exception(f"AI Pipeline Failed: {str(e)}")

def extract_features(transcript: str) -> dict:
    prompt = f"""
    Act as a master retention analyst for social media.
    Analyze the following video hook transcript and extract key features.
    You MUST return ONLY a strictly valid JSON object with the exact following schema (No markdown ticks):
    {{
        "Pacing": "Fast, Slow, or Medium",
        "Question Count": 0,
        "Core Emotion": "Emotion String",
        "Target Persona": "Description of the target listener profile",
        "Trigger Strategy": "The psychological hook type",
        "Power Words": ["word1", "word2"]
    }}
    Transcript: "{transcript}"
    """
    try:
        resp = robust_generate(prompt, temperature=0.1)
        resp = resp.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(resp)
    except Exception:
        return {
            "Pacing": "N/A", "Question Count": 0, "Core Emotion": "Unknown",
            "Target Persona": "N/A", "Trigger Strategy": "N/A", "Power Words": []
        }

def score_hook(transcript: str, platform: str) -> int:
    prompt = f"""
    Score the following video hook transcript specifically for {platform} from 0 to 100.
    Return ONLY the integer score as your final response.
    Transcript: "{transcript}"
    """
    try:
        resp = robust_generate(prompt, temperature=0.2)
        score = int(''.join(filter(str.isdigit, resp)))
        return max(0, min(100, score))
    except Exception:
        return 50 

def rewrite_hook(transcript: str, platform: str, vibe: str) -> str:
    prompt = f"""
    Act as an expert scriptwriter optimizing for {platform} using a {vibe} tone.
    Rewrite the following hook into three distinct, high-retention variations:
    1. Curiosity-Driven
    2. Action-Packed
    3. Story-Based
    Format response in raw text matching these three formats.
    Transcript: "{transcript}"
    """
    try:
        return robust_generate(prompt, temperature=0.7)
    except Exception as e:
        return "Failed to generate variations due to AI bounds."

# ==========================================
# REST API Endpoints
# ==========================================
@app.get("/")
def read_root():
    # Serves our beautiful Tailwind Frontend
    return FileResponse("index.html")

@app.post("/api/analyze")
def analyze_endpoint(req: AnalyzeRequest):
    # Step 1: Resolve Text source
    analyze_text = ""
    if req.source == "url":
        try:
            full_txt = fetch_youtube_transcript(req.yt_url)
            analyze_text = " ".join(full_txt.split()[:400]) # Grabbing the hook payload strictly
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        if not req.transcript.strip():
            raise HTTPException(status_code=400, detail="Transcript text is empty.")
        analyze_text = req.transcript

    # Step 2: Push through Nvidia Pipeline
    try:
        features = extract_features(analyze_text)
        score = score_hook(analyze_text, req.platform)
        variations = rewrite_hook(analyze_text, req.platform, req.vibe)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation Pipeline Error: {str(e)}")

    # Step 3: Bundle and Return Payload
    return {
        "success": True,
        "score": score,
        "features": features,
        "variations": variations,
        "analyzed_snippet": analyze_text
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)