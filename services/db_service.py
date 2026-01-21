
import logging
import os
from datetime import datetime
from supabase import create_client, Client

from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

class DBService:
    def __init__(self):
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Connected to Supabase Cloud.")

    def update_user(self, user_id, username, first_name):
        """Updates user last_active or inserts new user."""
        try:
            data = {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "last_active": "now()"
            }
            # upsert provided by Supabase client
            self.supabase.table("users").upsert(data).execute()
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")

    def save_interaction(self, user_id, role, content_text=None, audio_path=None, analysis_data=None):
        """
        Saves a chat interaction (User or Model).
        """
        try:
            if analysis_data is None:
                analysis_data = {}
            
            data = {
                "user_id": user_id,
                "role": role,
                "content_text": content_text,
                "content_audio_path": audio_path,
                "transcription": analysis_data.get('transcription'),
                "transcription_romanized": analysis_data.get('transcription_romanized'),
                "pronunciation_score": analysis_data.get('pronunciation_score'),
                "feedback_text": analysis_data.get('feedback')
            }
            
            self.supabase.table("interactions").insert(data).execute()
            logger.info(f"Saved interaction for user {user_id} ({role}) to Supabase")
        except Exception as e:
            logger.error(f"Error saving interaction: {e}")

    def get_context(self, user_id, limit=1000):
        """
        Retrieves last N messages formatted for Gemini context.
        Limit increased to 1000 for "Titan Memory" with Gemini Flash.
        """
        try:
            response = self.supabase.table("interactions")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            
            rows = response.data
            
            # Reconstruct history in chronological order (oldest first)
            history = []
            for row in reversed(rows):
                if row['role'] == 'user':
                    text_part = f"User said: {row['transcription']}"
                else:
                    text_part = f"Tutor said: {row['content_text']}. Feedback given: {row['feedback_text']}"
                
                history.append(text_part)
            
            return history
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return []
