import logging
import edge_tts
import uuid
import shutil
import os
from pydub import AudioSegment

# Initialize logger first
logger = logging.getLogger(__name__)

# Explicit Pydub Configuration
# dynamically find ffmpeg
def find_ffmpeg():
    """Finds ffmpeg binary in common locations."""
    # 1. Try system path
    path = shutil.which("ffmpeg")
    if path:
        return path
    
    # 2. Common fallback paths (Mac Silicon, Mac Intel, Linux)
    common_paths = [
        "/opt/homebrew/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/usr/bin/ffmpeg"
    ]
    
    for p in common_paths:
        if os.path.exists(p):
            return p
            
    return None

def find_ffprobe():
    """Finds ffprobe binary in common locations."""
    # 1. Try system path
    path = shutil.which("ffprobe")
    if path:
        return path
        
    # 2. Common fallback paths
    common_paths = [
        "/opt/homebrew/bin/ffprobe",
        "/usr/local/bin/ffprobe",
        "/usr/bin/ffprobe"
    ]
    
    for p in common_paths:
        if os.path.exists(p):
            return p
            
    return None

ffmpeg_path = find_ffmpeg()
ffprobe_path = find_ffprobe()

if ffmpeg_path:
    AudioSegment.converter = ffmpeg_path
    logger.info(f"ffmpeg found at: {ffmpeg_path}")
else:
    logger.warning("ffmpeg not found! Audio conversion may fail.")

if ffprobe_path:
    AudioSegment.ffprobe = ffprobe_path
else:
    logger.warning("ffprobe not found!")

class AudioService:
    @staticmethod
    def convert_ogg_to_mp3(ogg_path: str) -> str:
        """
        Converts Telegram's OGG voice note to MP3 for Gemini.
        Returns the path to the MP3 file.
        """
        try:
             # Re-verify path just in case, though global config should hold
            if AudioSegment.converter is None:
                 if os.path.exists("/opt/homebrew/bin/ffmpeg"):
                    AudioSegment.converter = "/opt/homebrew/bin/ffmpeg"
            
            mp3_path = ogg_path.replace(".ogg", ".mp3")
            
            # Load OGG and export as MP3
            # Requires FFmpeg installed on the system
            audio = AudioSegment.from_ogg(ogg_path)
            audio.export(mp3_path, format="mp3")
            
            logger.info(f"Converted {ogg_path} to {mp3_path}")
            return mp3_path
        except Exception as e:
            logger.error(f"Error converting audio: {e}")
            raise

    @staticmethod
    async def generate_tts(text: str, output_file: str = None) -> str:
        """
        Generates Korean TTS audio using edge-tts.
        Returns the path to the generated audio file.
        """
        if not output_file:
            # Generate a random filename if none provided
            output_file = f"response_{uuid.uuid4()}.mp3"
        
        try:
            # VOICE SELECTION:
            # ko-KR-SunHiNeural (Female)
            # ko-KR-InJoonNeural (Male)
            voice = "ko-KR-SunHiNeural" 
            
            # Rate -20% for beginners
            communicate = edge_tts.Communicate(text, voice, rate="-20%")
            await communicate.save(output_file)
            
            logger.info(f"Generated TTS audio at {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"Error generating TTS: {e}")
            raise

    @staticmethod
    def cleanup_files(*files):
        """Deletes temporary audio files."""
        for file_path in files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Deleted temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete {file_path}: {e}")
