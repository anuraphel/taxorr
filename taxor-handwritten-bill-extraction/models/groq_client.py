import os
import json
import time
import base64
from typing import Dict, Any, Tuple
from models.base_client import BaseLLMClient, ExpenseSchema

class GroqLLMClient(BaseLLMClient):
    def __init__(self, model_name: str = "llama-3.2-11b-vision-preview"):
        super().__init__(model_name)

    def _get_api_key(self) -> str:
        return os.environ.get("GROQ_API_KEY", "")

    def _call_api(self, image_path: str, prompt: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        from groq import Groq

        client = Groq(api_key=self.api_key)

        # Read and encode image to base64
        with open(image_path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode("utf-8")

        start_time = time.time()

        response = client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt + "\n\nRespond ONLY with a valid JSON object matching the schema. No extra text."
                        }
                    ]
                }
            ],
            temperature=0,
            max_tokens=512,
        )

        latency = time.time() - start_time

        raw_text = response.choices[0].message.content.strip()

        # Strip markdown code fences if model wraps output
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`").strip()
            if raw_text.startswith("json"):
                raw_text = raw_text[4:].strip()

        fields = json.loads(raw_text)

        # Extract token usage
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens

        # Groq pricing: Llama 3.2 Vision 11B = $0.18 / 1M input tokens, $0.18 / 1M output tokens
        cost = (input_tokens * 0.18 / 1e6) + (output_tokens * 0.18 / 1e6)

        metadata = {
            "tokens_input": input_tokens,
            "tokens_output": output_tokens,
            "cost": cost,
            "latency": latency,
            "is_mock": False
        }

        return fields, metadata
