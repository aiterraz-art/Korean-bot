
import os
import time
import asyncio
import json
import logging
import functools
import google.generativeai as genai
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-3-flash-preview"  # User requested model (Experimental)

# System Prompt mandated by SENSEI LOGIC (Beginner Pivot)
SYSTEM_PROMPT = """
You are a friendly, patient, and highly intelligent native Korean tutor (Sensei).
Role: Advanced Adaptive Guide.

**CONTEXT AWARENESS**:
You will receive a history of previous interactions. USE IT.
- Remember the user's name.
- Remember which lesson they struggled with.
- Do not repeat "Hello" if you just said it.
- If they failed a phrase previously, ask them to retry it now.

**MASTER CURRICULUM (Follow sequentially unless user tracks off):**

**LEVEL 1: SURVIVAL & MANNERS**
1.  **Greetings**: "Annyeonghaseyo" (Hello)
2.  **Yes/No**: "Ne" (Yes) / "Aniyo" (No)
3.  **Thanks**: "Gamsahamnida" (Thank you - formal)
4.  **Apology**: "Joesonghamnida" (I am sorry)
5.  **Excuse Me**: "Jeogiyo" (Excuse me - to call attention)
6.  **Farewell (Stay)**: "Annyeonghi gyeseyo" (Goodbye - to person staying)
7.  **Farewell (Go)**: "Annyeonghi gaseyo" (Goodbye - to person leaving)

**LEVEL 2: BASIC INTRO & IDENTITY**
8.  **Identity**: "Jeoneun [Name] imnida" (I am [Name]). Ask user's name first if unknown.
9.  **Nice to meet**: "Bangapseumnida" (Nice to meet you)
10. **Topic Particle**: Explanation of 'eun/neun' (simple concept).
11. **Object ID**: "Igeo mwoyeyo?" (What is this?)
12. **It is X**: "Igeoseun [Object] yeyo" (This is [Object])

**LEVEL 3: SURVIVAL SKILLS**
13. **Give me**: "[Item] juseyo" (Please give me [Item])
14. **Numbers 1-5 (Native)**: Hana, Dul, Set, Net, Daseot (Counting things)
15. **Numbers 1-10 (Sino)**: Il, I, Sam, Sa, O... (Money/Dates)
16. **How much?**: "Eolmayeyo?" (How much is it?)
17. **Where is?**: "Hwajangsil eodi-yeyo?" (Where is the bathroom?)

**LEVEL 4: DAILY ROUTINE (Verbs)**
18. **To Go**: "Gada" -> "Gayo" (I go)
19. **To Eat**: "Meokda" -> "Meogeoyo" (I eat)
20. **To Do**: "Hada" -> "Haeyo" (I do)
21. **Past Tense**: "Gasseoyo" (I went) / "Meogeosseoyo" (I ate)

**LEVEL 5: FEELINGS & OPINIONS**
22. **Good/Like**: "Joayo" (It's good / I like it)
23. **Delicious**: "Masisseoyo" (It's delicious)
24. **Busy**: "Bappayo" (I'm busy)
25. **Want to**: "Hago sipeoyo" (I want to do X)

**LEVEL 6: FLUENCY CONNECTORS**
26. **And/With**: "Hago" / "Rang"
27. **But**: "Hajiman" / "Geunde"
28. **So/Therefore**: "Geuraeseo"
29. **Because**: "Wae-nyahamyon"

**CONVERSATIONAL GOAL**:
Once user passes Level 6, engage in **Free Conversation**.
Ask open-ended questions like "Mwo haeyo?" (What are you doing?) or "Oneul eottaeyo?" (How is today?).

**INSTRUCTIONS**:
1.  **Analyze**: Listen to user audio OR read user text.
2.  **Evaluate**: Score pronunciation (1-10) only if they attempt Korean.
3.  **Flow Logic**:
    - **"Necesito decir X" / "How do I say X"**: IGNORE CURRICULUM. Provide the Translation, Romanization, and Phonetics for "X".
    - **Score >= 7**: Praise briefly, then INTRODUCE the NEXT lesson phrase.
    - **Score < 7**: Encourage warmly, explain the mistake (e.g. "Tongue higher"), and ASK TO REPEAT.
    - **User Converses**: If user asks a question or chats, ANSWER IT intelligently, then gently guide back to curriculum.
    - **"I don't know"**: Teach the current phrase immediately.

4.  **Output Style**:
    - **reply_text**: The Korean phrase (Lesson or Requested Translation).
    - **feedback**: Specific, helpful, short.
    - **reply_translation**: Spanish.
    - **reply_phonetic_es**: Spanish-reader friendly (e.g., "An-ñong", not "An-nyeong").

Output Format (JSON ONLY):
{
  "transcription": "...",
  "transcription_romanized": "...",
  "pronunciation_score": 8,
  "feedback": "...",
  "reply_text": "...", 
  "reply_romanized": "...",
  "reply_translation": "...",
  "reply_phonetic_es": "..."
}
"""

def retry_on_error(max_retries=3, delay=1):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if "503" in str(e) or "429" in str(e):
                        logger.warning(f"Gemini API error {e}. Retrying {attempt+1}/{max_retries}...")
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
                    else:
                        raise e
            raise Exception("Max retries exceeded for Gemini API")
        return wrapper
    return decorator

class GeminiService:
    def __init__(self):
        self.model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=SYSTEM_PROMPT,
            generation_config={"response_mime_type": "application/json"}
        )

    async def upload_audio(self, mp3_path: str):
        """Uploads file to Gemini File API (Non-blocking)."""
        logger.info(f"Uploading {mp3_path} to Gemini...")
        # Run blocking upload in a separate thread
        file_ref = await asyncio.to_thread(genai.upload_file, mp3_path, mime_type="audio/mp3")
        logger.info(f"File uploaded: {file_ref.name}")
        return file_ref

    @retry_on_error()
    async def analyze_audio(self, audio_file_ref, history=None):
        """
        Sends audio to Gemini and gets JSON response.
        history: List of strings/messages from previous turns.
        """
        # 1. Construct the rich prompt with history
        prompt_content = "Analyze this audio clip based on the system instructions.\n"
        
        if history and len(history) > 0:
            prompt_content += "\n\n**CONVERSATION HISTORY (Most recent last):**\n"
            for item in history:
                prompt_content += f"- {item}\n"
            prompt_content += "\n**END OF HISTORY**\n"
            
        prompt_parts = [
            prompt_content,
            audio_file_ref
        ]
        
        # Note: In a real chat loop, we would append history here.
        # For this statless MVP audio-analysis, we just send the file + prompt.
        
        logger.info("Sending request to Gemini...")
        # Run blocking generation in a separate thread
        response = await asyncio.to_thread(self.model.generate_content, prompt_parts)
        
        try:
            # Check for valid text part or safety rejection
            try:
                text_response = response.text
            except ValueError:
                # This happens if the model returns no text (e.g. safety block or empty completion)
                logger.warning(f"Gemini returned empty response. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'Unknown'}")
                return {
                    "transcription": "(Unclear audio)",
                    "pronunciation_score": 0,
                    "feedback": "I couldn't hear that clearly. Please try again!",
                    "reply_text": "다시 말씀해 주세요.",
                    "reply_romanized": "Dasi malsseumhae juseyo.",
                    "reply_translation": "Por favor, dilo de nuevo.",
                    "reply_phonetic_es": "Da-shi mal-seum-hae ju-se-yo"
                }

            if text_response.startswith("```json"):
                text_response = text_response.replace("```json", "").replace("```", "")
            
            parsed_json = json.loads(text_response)
            logger.info("Successfully parsed Gemini JSON response")
            return parsed_json
        except Exception as e:
            logger.error(f"Failed to parse JSON: {e}")
            # Fallback structure
            return {
                "transcription": "Error parsing response",
                "pronunciation_score": 0,
                "feedback": "System error: Could not parse AI response.",
                "reply_text": "죄송합니다. 다시 말씀해 주세요.",
                "reply_romanized": "Joesonghamnida. Dasi malsseumhae juseyo."
            }

    @retry_on_error()
    async def analyze_text(self, user_text, history=None):
        """
        Analyzes TEXT input (for typed messages or 'Necesito decir' commands).
        """
        # 1. Construct the rich prompt with history
        prompt_content = f"Analyze this user TEXT input: '{user_text}'\nBased on system instructions."
        
        if history and len(history) > 0:
            prompt_content += "\n\n**CONVERSATION HISTORY (Most recent last):**\n"
            for item in history:
                prompt_content += f"- {item}\n"
            prompt_content += "\n**END OF HISTORY**\n"
            
        prompt_parts = [prompt_content]
        
        logger.info("Sending TEXT request to Gemini...")
        # Run blocking generation in a separate thread
        response = await asyncio.to_thread(self.model.generate_content, prompt_parts)
        
        try:
            text_response = response.text
            if text_response.startswith("```json"):
                text_response = text_response.replace("```json", "").replace("```", "")
            
            parsed_json = json.loads(text_response)
            logger.info("Successfully parsed Gemini JSON response (Text)")
            return parsed_json
        except Exception as e:
            logger.error(f"Failed to parse JSON (Text): {e}")
            return {
                "transcription": user_text,
                "pronunciation_score": 0,
                "feedback": "Error conceptualizing response.",
                "reply_text": "죄송합니다. 다시 말씀해 주세요.",
                "reply_romanized": "Joesonghamnida.",
                "reply_phonetic_es": "Chue-song-jam-ni-da"
            }

    @staticmethod
    def cleanup_gemini_file(file_ref):
        """Deletes the file from Gemini cloud storage to avoid clutter."""
        try:
            genai.delete_file(file_ref.name)
            logger.debug(f"Deleted Gemini file: {file_ref.name}")
        except Exception as e:
            logger.warning(f"Failed to delete Gemini file: {e}")
