import os
import json
import time
from typing import Dict, Any, Tuple
from models.base_client import BaseLLMClient

class GeminiLLMClient(BaseLLMClient):
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        super().__init__(model_name)

    def _get_api_key(self) -> str:
        return os.environ.get("GEMINI_API_KEY", "")

    def _call_api(self, image_path: str, prompt: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        # Import inside method to avoid dependency errors if package is not installed and mock mode is active
        import google.generativeai as genai
        from PIL import Image

        genai.configure(api_key=self.api_key)
        
        # Configure model parameters for structured JSON output matching ExpenseSchema
        from models.base_client import ExpenseSchema
        generation_config = {
            "response_mime_type": "application/json",
            "response_schema": ExpenseSchema
        }
        
        model = genai.GenerativeModel(self.model_name, generation_config=generation_config)
        
        # Open and prepare the image
        img = Image.open(image_path)
        
        start_time = time.time()
        response = model.generate_content([img, prompt])
        latency = time.time() - start_time
        
        # Extract metadata
        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count
        
        # Cost mapping based on official Gemini pricing
        # Flash: $0.075 / 1M input, $0.30 / 1M output
        # Pro: $3.50 / 1M input, $10.50 / 1M output
        if "pro" in self.model_name:
            cost = (input_tokens * 3.50 / 1e6) + (output_tokens * 10.50 / 1e6)
        else:
            cost = (input_tokens * 0.075 / 1e6) + (output_tokens * 0.30 / 1e6)
            
        fields = json.loads(response.text)
        
        metadata = {
            "tokens_input": input_tokens,
            "tokens_output": output_tokens,
            "cost": cost,
            "latency": latency,
            "is_mock": False
        }
        
        return fields, metadata
