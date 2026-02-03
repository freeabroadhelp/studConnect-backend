import os
import json
from typing import Dict, Any, Optional
import openai
from dotenv import load_dotenv

from .prompt_builder import build_system_prompt, build_user_prompt

# Load env vars (if not already loaded)
load_dotenv()

class AIExplainer:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
        
        self.model = "gpt-4o-mini"
        self.max_tokens = 700
        self.temperature = 0.3
        
        # Simple in-memory cache: request_id -> response
        # In production, use Redis or Memcached
        self.cache = {}

    def get_explanation(self, request_id: str, student_profile: Dict[str, Any], engine_output: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generates an explanation for the recommendation results.
        Returns None if API key is missing or error occurs.
        """
        if not self.client:
            print("Warning: OpenAI API key not found. Skipping AI explanation.")
            return None
        
        # Check cache
        if request_id in self.cache:
            return self.cache[request_id]

        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(student_profile, engine_output)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if not content:
                return None
                
            parsed_content = json.loads(content)
            
            # Cache result
            self.cache[request_id] = parsed_content
            
            return parsed_content
            
        except Exception as e:
            print(f"Error generating AI explanation: {e}")
            return None

# Singleton instance
explainer = AIExplainer()
