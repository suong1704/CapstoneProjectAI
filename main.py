import os
import re
import difflib
from openai import OpenAI
from fastapi import FastAPI, File, UploadFile, Form
from pydantic import BaseModel
from typing import Annotated
import time
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

app = FastAPI(
    title="AI Services",
    description="AI services are applications or software that use artificial intelligence to perform tasks, such as image recognition or natural language processing.",
    version="2.0",
    openapi_url="/api/v2/openapi.json",
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


load_dotenv()
KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=KEY)

@app.post("/transcribe", tags=["Convert audio to text"], description="Transcribes audio into the input language.")
async def transcribe(file: UploadFile = File(...)):
        
    transcript = ""
    directory = "./audio_files/"

    # Create a directory for files
    if not os.path.exists(directory):
        os.makedirs(directory)

    timestamp = int(time.time()) 
    audio_name = f"speech_{timestamp}"
    # Combine the directory, filename to create the full path
    full_path = os.path.join(directory, audio_name + file.filename)

    # Save audio file to disk temporarily
    try:
        contents = file.file.read()
        with open(full_path, 'wb') as f:
            f.write(contents)
    except Exception:
        return "There was an error uploading the file"
    finally:
        file.file.close()
    
    # Transcribe audio using OpenAI API
    with open(full_path, 'rb') as f:
        transcript = client.audio.transcriptions.create(model="whisper-1", file=f, language="en", temperature=0.7)
        
    return str(transcript.text).lower()

@app.post("/pronunciation_score", tags=["Pronunciation Score"], description="Pronunciation Score")
async def pronunciation_score(original_script: Annotated[str, Form()], audio_file: UploadFile = File(...)):

    user_script = await transcribe(audio_file)
    
    if not original_script or not user_script:
        return None
    
    html_output, percent_diff = highlight_script_differrences(original_script, user_script)
    
    return original_script, user_script, percent_diff, html_output

def get_score(original_split, user_script_split):
    matcher = difflib.SequenceMatcher(None, original_split, user_script_split)
    ops = matcher.get_opcodes()
    percent_diff = 100 - round(((sum(original_end - original_start for op, original_start, original_end, user_start, user_end in ops if op != 'equal') / max(len(original_split), len(user_script_split))) * 100), 2)
    return round(percent_diff, 2)

def get_html(original_split, user_script_split, raw_user_script_split):
    matcher = difflib.SequenceMatcher(None, original_split, user_script_split)
    ops = matcher.get_opcodes()
    # Create a list to hold the HTML-formatted words
    highlighted_words = []
    for op, original_start, original_end, user_start, user_end in ops:
        if op == 'equal':
            # If the words are equal, add a green span tag around the word
            for i in range(original_start, original_end):
                if i < len(user_script_split):
                    highlighted_words.append(f'<span className="green">{raw_user_script_split[i]}</span>')

        elif op == 'replace':
            # If the words are different, add a red span tag around the word
            for i in range(original_start, original_end):
                if i < len(user_script_split):
                    if original_split[i] == user_script_split[i]:
                        # If the capitalization is different, keep the original capitalization
                        highlighted_words.append(f'<span className="red">{raw_user_script_split[i]}</span>')
        elif op == 'delete':
                # If the word is missing from the user's script, add a red span tag around the original word
                for i in range(original_start, original_end):
                    if i < len(user_script_split):
                        highlighted_words.append(f'<span className="red">{raw_user_script_split[i]}</span>')
        elif op == 'insert':
            # If there is an extra word in the user's script, add a red span tag around the user's word
            for i in range(user_start, user_end):
                if i < len(user_script_split):
                    highlighted_words.append(f'<span className="red">{raw_user_script_split[i]}</span>')
    
    # highlight the remaining word with red if the user script is longer than the original script             
    if len(raw_user_script_split) > len(highlighted_words):
        for i in range(len(highlighted_words), len(raw_user_script_split)):
            highlighted_words.append(f'<span className="red">{raw_user_script_split[i]}</span>')
        
    # Join the list of highlighted words into a single string
    highlighted_script = ' '.join(highlighted_words)


    # Wrap the highlighted script in a div tag with a class for styling
    return f'<div className="highlighted-script">{highlighted_script}</div>'
    

def highlight_script_differrences(original_script, user_script):
    user_script_cleaned = re.sub(r"[^a-zA-Z\s]", "", user_script).lower()
    original_script_cleaned = re.sub(r"[^a-zA-Z\s]", "", original_script).lower()

    raw_user_script_split = user_script.split()
    user_script_split = user_script_cleaned.split()
    original_split = original_script_cleaned.split()
    
    percent_diff = get_score(original_split, user_script_split)
    html_output = get_html(original_split, user_script_split, raw_user_script_split)

    return html_output, percent_diff