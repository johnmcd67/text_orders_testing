"""
Anthropic API helper with retry logic and error handling
"""
import json
import os
import time
from typing import Dict, Any, Optional
from anthropic import Anthropic
from .logger import logger


class AnthropicHelper:
    """Wrapper for Anthropic API calls with retry logic"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Anthropic client

        Args:
            api_key: Anthropic API key (if None, reads from environment)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        self.client = Anthropic(api_key=self.api_key)

        # Default models from .env or hardcoded
        self.default_model = os.getenv("ANTHROPIC_MODEL_DEFAULT", "claude-sonnet-4-5-20250929")
        self.complex_model = os.getenv("ANTHROPIC_MODEL_COMPLEX", "claude-sonnet-4-5-20250929")

        # Retry configuration
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.timeout = int(os.getenv("TIMEOUT_SECONDS", "30"))

        # Token configuration
        self.max_tokens = int(os.getenv("MAX_TOKENS", "4096"))

    def call_with_retry(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0,
        response_format: str = "json",
        system_message: Optional[str] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Call Anthropic API with retry logic

        Args:
            prompt: User prompt
            model: Model to use (if None, uses default_model)
            temperature: Temperature (0 = deterministic, 1 = creative)
            response_format: "json" or "text"
            system_message: Optional system message
            max_tokens: Maximum tokens in response (if None, uses default from config)

        Returns:
            Parsed response (dict if JSON, str if text)

        Raises:
            Exception: If all retries fail
        """
        model = model or self.default_model
        max_tokens = max_tokens or self.max_tokens

        # Build messages array (Anthropic doesn't include system message here)
        messages = [{"role": "user", "content": prompt}]

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"Anthropic API call (attempt {attempt}/{self.max_retries}): model={model}")

                # Call Anthropic API
                response = self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_message if system_message else "",
                    messages=messages,
                    timeout=timeout or self.timeout,
                )

                # Extract content from response
                content = response.content[0].text

                # Parse JSON response
                if response_format == "json":
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON response: {e}")
                        logger.debug(f"Raw response: {content}")
                        # Try to extract JSON from markdown code blocks
                        if "```json" in content:
                            json_str = content.split("```json")[1].split("```")[0].strip()
                            return json.loads(json_str)
                        elif "```" in content:
                            json_str = content.split("```")[1].split("```")[0].strip()
                            return json.loads(json_str)
                        raise

                # Return text response
                return {"content": content}

            except Exception as e:
                logger.warning(f"Anthropic API error (attempt {attempt}/{self.max_retries}): {e}")

                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff: 2, 4, 8 seconds
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {self.max_retries} attempts failed")
                    raise

    def call_default(self, prompt: str, system_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Call with default model (claude-sonnet-4-5-20250929)

        Args:
            prompt: User prompt
            system_message: Optional system message

        Returns:
            Parsed JSON response
        """
        return self.call_with_retry(
            prompt=prompt,
            model=self.default_model,
            system_message=system_message,
            response_format="json",
        )

    def call_complex(self, prompt: str, system_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Call with complex model (claude-sonnet-4-5-20250929)

        Args:
            prompt: User prompt
            system_message: Optional system message

        Returns:
            Parsed JSON response
        """
        return self.call_with_retry(
            prompt=prompt,
            model=self.complex_model,
            system_message=system_message,
            response_format="json",
        )


# Global instance (lazy initialization)
_anthropic_helper: Optional[AnthropicHelper] = None


def get_anthropic_helper() -> AnthropicHelper:
    """Get or create global Anthropic helper instance"""
    global _anthropic_helper
    if _anthropic_helper is None:
        _anthropic_helper = AnthropicHelper()
    return _anthropic_helper

