# Project Specification: "K-Voice Coach" (Robust Audio-First Architecture)

## 1. Project Overview
A robust, asynchronous Telegram bot designed to teach Korean through speaking. The system prioritizes audio interaction and provides strict pronunciation feedback. It uses **Google Gemini 1.5 Flash/Pro** natively for both logic and audio understanding (multimodal capabilities).

**Key Differentiator:** The bot does not just transcribe; it "listens" to the raw audio file to detect accent and pronunciation nuances that standard STT (Speech-to-Text) engines might miss or autocorrect.

## 2. Technical Stack & Requirements
* **Language:** Python 3.10+
* **Framework:** `python-telegram-bot` (v20+ Async context-based architecture).
* **AI Core:** `google-generativeai` (Gemini SDK).
* **Audio Output (TTS):** `gTTS` (Google Text-to-Speech) or `edge-tts` for higher quality Korean voices.
* **Audio Processing:** `pydub` and `ffmpeg` (for converting Telegram OGG voice notes to MP3/WAV for Gemini).
* **State Management:** In-memory dictionary or simple `sqlite3` database to store user conversation history (context window).

## 3. Detailed Feature Specifications

### Feature A: The "Pronunciation Doctor" Pipeline (Strict Requirement)
When the user sends a Voice Note, the system must execute this precise flow:

1.  **Ingestion:** Download the OGG file from Telegram and convert it to a format supported by Gemini (MP3/WAV).
2.  **Multimodal Analysis (The Critical Step):**
    * Upload the audio file to Gemini using the `File API`.
    * **Prompt Payload:** Send the Audio File + Current Conversation Context + System Instruction.
    * **System Instruction for Analysis:**
        > "You are a strict Korean phonetics expert. Listen to the attached user audio.
        > 1. **Transcribe** exactly what was said.
        > 2. **Analyze Pronunciation:** Rate it 1-10. If the rating is below 9, explicitly point out which syllable was mispronounced (e.g., 'You said *eo* but it sounded like *o*').
        > 3. **Conversational Reply:** Generate a natural, short response to continue the dialogue in Korean."
3.  **Response Parsing:** The bot must separate the "Correction/Feedback" from the "Conversational Reply".

### Feature B: "Blind" Training Output
To force listening comprehension, the bot's response to the user must be:
1.  **Audio Message:** The "Conversational Reply" converted to speech (TTS).
2.  **Text Message (Spoiler):** The transcript of the reply hidden behind a spoiler `||Hidden Text||`.
3.  **Feedback Message:** Visible text showing the Pronunciation Score and corrections (in Spanish/English as per user pref).

### Feature C: Robustness & Error Handling
* **Retry Logic:** Implement decorators to retry Gemini API calls if `503 Service Unavailable` occurs.
* **Voice Safety:** If the user's audio is unintelligible or silent, handle the exception gracefully and ask them to repeat.
* **Long-Running Tasks:** Send a "Typing..." or "Record_voice..." action status in Telegram while Gemini is processing to prevent user timeout perception.

## 4. System Prompt Strategy (Persona)
The agent must configure Gemini with this persona:
> "You are a native Korean tutor focused on 'Survival Speaking'.
> - **Input:** You will receive audio files.
> - **Feedback Style:** Be direct. Correct intonation errors immediately.
> - **Romanization Rule:** Always provide Romanization for beginners.
> - **Response Style:** Keep replies short (under 15 words) to encourage rapid back-and-forth."

## 5. File Structure Deliverables
The agent must generate:
1.  `bot.py`: Main execution loop using `ApplicationBuilder`.
2.  `services/gemini_service.py`: Class to handle file uploads, chat history, and API generation.
3.  `services/audio_service.py`: Class to handle OGG conversion and TTS generation.
4.  `config.py`: Environment variable validation (fail fast if keys are missing).
5.  `requirements.txt`: Must include `python-telegram-bot[job-queue]`, `pydub`, `gTTS`, `google-generativeai`, `python-dotenv`.

## 6. Execution Instructions
Include a final comment block explaining how to install `ffmpeg` on the host machine (Mac/Windows/Linux), as it is required for `pydub`.