# app/llm/adapter.py
from __future__ import annotations
from typing import Tuple
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings

_openai_client = None
def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client

_genai = None
def _get_gemini_model(model_name: str):
    global _genai
    if _genai is None:
        import google.generativeai as genai
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        _genai = genai
    return _genai.GenerativeModel(model_name)

class LLMError(RuntimeError):
    pass

class LLMAdapter:
    """
    Provider-agnostic interface:
      generate(prompt, model=?, temperature=?, max_tokens=?)
    Returns: (text, provider_message_id)
    """

    def __init__(self, provider: str | None = None):
        self.provider = (provider or settings.LLM_PROVIDER).lower()

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(LLMError),
    )
    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> Tuple[str, str]:
        model = model or settings.LLM_MODEL
        temperature = settings.LLM_TEMPERATURE if temperature is None else float(temperature)
        max_tokens = settings.LLM_MAX_TOKENS if max_tokens is None else int(max_tokens)
        timeout = settings.LLM_TIMEOUT if timeout is None else float(timeout)

        if self.provider == "google":
            return self._generate_gemini(prompt, model, temperature, max_tokens, timeout)
        elif self.provider == "openai":
            return self._generate_openai(prompt, model, temperature, max_tokens, timeout)
        else:
            raise LLMError(f"Unsupported LLM_PROVIDER: {self.provider}")

    # ------------------ Google (Gemini) ------------------
    def _generate_gemini(self, prompt: str, model: str, temperature: float, max_tokens: int, timeout: float) -> Tuple[str, str]:
        try:
            model_obj = _get_gemini_model(model)
            # generation_config differs from OpenAI; maps to Gemini’s knobs
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
            # Gemini Python SDK doesn’t expose a direct timeout per call; rely on HTTP default.
            resp = model_obj.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=None,  # keep defaults; you can add custom tuning here
            )
            # Extract text and a best-effort message id
            text = getattr(resp, "text", "") or ""
            # Try to extract a candidate/message id (SDKs vary; this is best-effort safe)
            message_id = ""
            try:
                if getattr(resp, "candidates", None):
                    c0 = resp.candidates[0]
                    message_id = getattr(c0, "candidate_id", "") or getattr(c0, "id", "") or ""
            except Exception:
                pass

            if not text:
                raise LLMError("Gemini returned empty text.")
            return text, (message_id or "gemini-no-id")
        except Exception as e:
            raise LLMError(f"Gemini error: {e}")

    # ------------------ OpenAI ------------------
    def _generate_openai(self, prompt: str, model: str, temperature: float, max_tokens: int, timeout: float) -> Tuple[str, str]:
        try:
            client = _get_openai_client()
            # You can also use client.with_options(timeout=timeout)
            resp = client.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": "You are a skilled fiction writer."},
                    {"role": "user", "content": prompt},
                ],
                timeout=timeout,
            )
            text = resp.choices[0].message.content or ""
            message_id = resp.id or "openai-no-id"
            if not text:
                raise LLMError("OpenAI returned empty text.")
            return text, message_id
        except Exception as e:
            raise LLMError(f"OpenAI error: {e}")
