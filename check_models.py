
import os
import google.generativeai as genai
from config import GEMINI_API_KEY, validate_env

validate_env()
genai.configure(api_key=GEMINI_API_KEY)

print("Listing available models...")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)
