import os
import json
import time
import base64
from typing import Dict, Any, Tuple
from models.base_client import BaseLLMClient, ExpenseSchema

class OpenAILLMClient(BaseLLMClient):
    def __init__(self, model_name: str = "gpt-4o-mini"):
        super().__init__(model_name)

    def _get_api_key(self) -> str:
        return os.environ.get("OPENAI_API_KEY", "")

    def _call_api(self, image_path: str, prompt: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        # Import inside method to avoid dependency errors if package not installed
        from openai import OpenAI
        
        client = OpenAI(api_key=self.api_key)
        
        # Read and encode image to base64
        with open(image_path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode("utf-8")
            
        start_time = time.time()
        
        # Call chat completion with Structured Outputs (Beta.chat.completions.parse)
        response = client.beta.chat.completions.parse(
            model=self.model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            response_format=ExpenseSchema,
        )
        
        latency = time.time() - start_time
        
        # Extract metadata
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        
        # Cost mapping based on official OpenAI pricing (per 1M tokens)
        # GPT-4o-mini: $0.15 input, $0.60 output
        # GPT-4o: $2.50 input, $10.00 output
        if "gpt-4o-mini" in self.model_name:
            cost = (input_tokens * 0.15 / 1e6) + (output_tokens * 0.60 / 1e6)
        else:
            cost = (input_tokens * 2.50 / 1e6) + (output_tokens * 10.00 / 1e6)
            
        parsed_fields = response.choices[0].message.parsed
        fields_dict = parsed_fields.model_dump()
        
        metadata = {
            "tokens_input": input_tokens,
            "tokens_output": output_tokens,
            "cost": cost,
            "latency": latency,
            "is_mock": False
        }
        
        return fields_dict, metadata
