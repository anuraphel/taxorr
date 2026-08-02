import os
import json
import time
import base64
from typing import Dict, Any, Tuple
from models.base_client import BaseLLMClient, ExpenseSchema

class ClaudeLLMClient(BaseLLMClient):
    def __init__(self, model_name: str = "claude-3-5-sonnet"):
        super().__init__(model_name)

    def _get_api_key(self) -> str:
        return os.environ.get("ANTHROPIC_API_KEY", "")

    def _call_api(self, image_path: str, prompt: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        # Import inside method to avoid dependency errors if package not installed
        from anthropic import Anthropic
        
        client = Anthropic(api_key=self.api_key)
        
        # Read and encode image to base64
        with open(image_path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode("utf-8")
            
        start_time = time.time()
        
        # Define extraction schema as a tool definition
        schema_json = ExpenseSchema.model_json_schema()
        tool_definition = {
            "name": "extract_expense",
            "description": "Extract structured details from the handwritten receipt image.",
            "input_schema": schema_json
        }
        
        # Call Anthropic API
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620" if self.model_name == "claude-3-5-sonnet" else self.model_name,
            max_tokens=1000,
            tools=[tool_definition],
            tool_choice={"type": "tool", "name": "extract_expense"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )
        
        latency = time.time() - start_time
        
        # Extract metadata
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        
        # Cost mapping based on official Claude pricing (per 1M tokens)
        # Claude 3.5 Sonnet: $3.00 input, $15.00 output
        cost = (input_tokens * 3.00 / 1e6) + (output_tokens * 15.00 / 1e6)
        
        # Parse the tool use output
        fields = {}
        for content_block in response.content:
            if content_block.type == "tool_use" and content_block.name == "extract_expense":
                fields = content_block.input
                break
                
        metadata = {
            "tokens_input": input_tokens,
            "tokens_output": output_tokens,
            "cost": cost,
            "latency": latency,
            "is_mock": False
        }
        
        return fields, metadata
