
-- Users table to store profile and preferences
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_active DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Interactions table to store the conversation history and learning progress
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    role TEXT CHECK(role IN ('user', 'model')), -- strict role check
    content_text TEXT,
    content_audio_path TEXT, -- path to stored audio if any
    
    -- Analysis data (only for user turns or model feedback)
    transcription TEXT,
    transcription_romanized TEXT,
    pronunciation_score INTEGER,
    feedback_text TEXT,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

-- Index for fast context retrieval (getting last N messages)
CREATE INDEX IF NOT EXISTS idx_interactions_user_created ON interactions(user_id, created_at DESC);
