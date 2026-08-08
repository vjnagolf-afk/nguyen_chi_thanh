"""
============================================================
AI ENGINE PROVIDER - ENTERPRISE GATEWAY
Quản lý đa mô hình AI, Fallback an toàn và Exception chuẩn.
============================================================
"""

import time
import json
from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Union, Generator
import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from cachetools import TTLCache

from openai import OpenAI
import anthropic
from google import genai
from google.genai import types
from google.genai.errors import APIError

DEFAULT_TIMEOUT = 120
DEFAULT_TEMP = 0.2
DEFAULT_MAX_TOKENS = 8192
DEFAULT_TOP_P = 0.95

class AIEngineError(Exception): pass
class AuthenticationError(AIEngineError): pass
class ModelNotFoundError(AIEngineError): pass
class QuotaExceededError(AIEngineError): pass
class NetworkError(AIEngineError): pass
class TimeoutError(AIEngineError): pass

@dataclass
class AIResponse:
    text: str
    provider: str
    model: str
    latency: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = "stop"

prompt_cache = TTLCache(maxsize=200, ttl=3600)

class AIEngine:
    def __init__(self, provider_type: str, api_key: str, model_name: str, timeout: int = DEFAULT_TIMEOUT):
        self.provider_type = provider_type.split()[0]
        self.api_key = api_key.strip()
        self.model_name = model_name.strip()
        self.timeout = timeout
        self.session = requests.Session()
        
        self._is_ready = bool(self.api_key or self.provider_type == "Ollama")
        self._validate_provider()

    def is_ready(self) -> bool:
        return self._is_ready

    def _validate_provider(self):
        model_lower = self.model_name.lower()
        if self.provider_type == "Gemini" and "gemini" not in model_lower: raise ModelNotFoundError("Model sai cho Gemini.")
        if self.provider_type == "OpenAI" and "gpt" not in model_lower and "o1" not in model_lower: raise ModelNotFoundError("Model sai cho OpenAI.")
        if self.provider_type == "Anthropic" and "claude" not in model_lower: raise ModelNotFoundError("Model sai cho Claude.")

    def _build_messages(self, system_instruction: str, prompt: str) -> List[Dict[str, str]]:
        messages = []
        if system_instruction: messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        return messages

    def test_connection(self) -> bool:
        """Kiểm tra kết nối và trả về đúng loại Exception để Sidebar hiển thị."""
        try:
            res = self.generate_text(prompt="Ping.", system_instruction="Chỉ trả lời 'Pong'.")
            return bool(res and res.text)
        except (AuthenticationError, QuotaExceededError, NetworkError, TimeoutError, ModelNotFoundError) as e:
            raise e
        except Exception as e:
            raise NetworkError(f"Lỗi hệ thống hoặc đường truyền: {str(e)}")

    def generate_with_fallback(self, prompt: str, system_instruction: str = "") -> AIResponse:
        fallbacks = []
        if self.provider_type == "OpenRouter": fallbacks = ["google/gemini-2.5-flash", "google/gemini-1.5-pro", "meta-llama/llama-3-8b-instruct"]
        elif self.provider_type == "Gemini": fallbacks = ["gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash"]
        elif self.provider_type == "OpenAI": fallbacks = ["gpt-4o-mini", "gpt-3.5-turbo"]
            
        for fallback_model in fallbacks:
            if fallback_model == self.model_name: continue
            try:
                temp_engine = AIEngine(provider_type=self.provider_type, api_key=self.api_key, model_name=fallback_model, timeout=self.timeout)
                logger.warning(f"Đang thử Fallback sang model {fallback_model}...")
                return temp_engine.generate_text(prompt, system_instruction)
            except Exception as e:
                logger.error(f"Fallback model {fallback_model} thất bại: {e}")
                
        return self.generate_text(prompt, system_instruction)

    def generate_json(self, prompt: str, system_instruction: str = "") -> AIResponse:
        sys_json = system_instruction + "\nBẮT BUỘC TRẢ VỀ ĐỊNH DẠNG JSON. KHÔNG DÙNG ```json HAY KÈM THEO BẤT KỲ VĂN BẢN NÀO KHÁC."
        return self.generate_text(prompt, sys_json)

    def generate_markdown(self, prompt: str, system_instruction: str = "") -> AIResponse:
        sys_md = system_instruction + "\nBẮT BUỘC TRẢ VỀ ĐỊNH DẠNG MARKDOWN CHUẨN."
        return self.generate_text(prompt, sys_md)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type((NetworkError, TimeoutError)))
    def generate_text(self, prompt: str, system_instruction: str = "", stream: bool = False) -> Union[AIResponse, Generator]:
        if not self.is_ready(): raise AuthenticationError("AI chưa sẵn sàng.")

        cache_key = hash(f"{self.provider_type}_{self.model_name}_{system_instruction}_{prompt}")
        if not stream and cache_key in prompt_cache:
            return prompt_cache[cache_key]

        start_time = time.time()
        try:
            if self.provider_type == "Gemini": response = self._call_gemini_sdk(prompt, system_instruction)
            elif self.provider_type == "OpenAI": response = self._call_openai(prompt, system_instruction)
            elif self.provider_type == "Anthropic": response = self._call_anthropic(prompt, system_instruction)
            elif self.provider_type == "OpenRouter": response = self._call_openrouter(prompt, system_instruction)
            elif self.provider_type == "Ollama": response = self._call_ollama(prompt, system_instruction)
            else: raise AIEngineError("Provider không hỗ trợ.")

            response.latency = time.time() - start_time
            if not stream: prompt_cache[cache_key] = response
            return response
            
        except requests.exceptions.Timeout: raise TimeoutError("Timeout kết nối máy chủ.")
        except Exception as e: raise e

    def _call_gemini_sdk(self, prompt: str, system_instruction: str) -> AIResponse:
        try:
            client = genai.Client(api_key=self.api_key)
            config = types.GenerateContentConfig(temperature=DEFAULT_TEMP, top_p=DEFAULT_TOP_P, max_output_tokens=DEFAULT_MAX_TOKENS, system_instruction=system_instruction if system_instruction else None)
            res = client.models.generate_content(model=self.model_name, contents=prompt, config=config)
            usage = res.usage_metadata
            p_tokens = usage.prompt_token_count if usage else 0
            c_tokens = usage.candidates_token_count if usage else 0
            return AIResponse(text=res.text, provider="Gemini", model=self.model_name, latency=0.0, prompt_tokens=p_tokens, completion_tokens=c_tokens, total_tokens=p_tokens + c_tokens)
        except APIError as e:
            err_msg = str(e).lower()
            if "oauth" in err_msg: raise AuthenticationError("Lỗi OAuth. Vui lòng dùng API Key tĩnh hoặc OpenRouter.")
            if "401" in err_msg or "403" in err_msg: raise AuthenticationError("API Key Gemini không hợp lệ.")
            if "429" in err_msg: raise QuotaExceededError("Quá giới hạn request Gemini (429).")
            raise NetworkError(f"API Error: {str(e)}")
        except Exception as e: raise NetworkError(f"Lỗi SDK: {str(e)}")

    def _call_openai(self, prompt: str, system_instruction: str) -> AIResponse:
        try:
            client = OpenAI(api_key=self.api_key, timeout=self.timeout)
            res = client.chat.completions.create(model=self.model_name, messages=self._build_messages(system_instruction, prompt), temperature=DEFAULT_TEMP, max_tokens=DEFAULT_MAX_TOKENS, top_p=DEFAULT_TOP_P)
            return AIResponse(text=res.choices[0].message.content, provider="OpenAI", model=self.model_name, latency=0.0, prompt_tokens=res.usage.prompt_tokens, completion_tokens=res.usage.completion_tokens, total_tokens=res.usage.total_tokens)
        except Exception as e:
            err_msg = str(e)
            if "401" in err_msg: raise AuthenticationError("Sai API Key OpenAI.")
            if "429" in err_msg: raise QuotaExceededError("Hết Quota OpenAI.")
            if "timeout" in err_msg.lower(): raise TimeoutError("Timeout kết nối máy chủ OpenAI.")
            raise NetworkError(err_msg)

    def _call_anthropic(self, prompt: str, system_instruction: str) -> AIResponse:
        try:
            client = anthropic.Anthropic(api_key=self.api_key, timeout=self.timeout)
            res = client.messages.create(model=self.model_name, max_tokens=DEFAULT_MAX_TOKENS, temperature=DEFAULT_TEMP, system=system_instruction if system_instruction else anthropic.NOT_GIVEN, messages=[{"role": "user", "content": prompt}])
            return AIResponse(text=res.content[0].text, provider="Anthropic", model=self.model_name, latency=0.0, prompt_tokens=res.usage.input_tokens, completion_tokens=res.usage.output_tokens, total_tokens=res.usage.input_tokens + res.usage.output_tokens)
        except Exception as e:
            if "authentication" in str(e).lower(): raise AuthenticationError("Sai API Key Claude.")
            raise NetworkError(str(e))

    def _call_openrouter(self, prompt: str, system_instruction: str) -> AIResponse:
        try:
            client = OpenAI(
                base_url="[https://openrouter.ai/api/v1](https://openrouter.ai/api/v1)",
                api_key=self.api_key,
                timeout=self.timeout
            )

            res = client.chat.completions.create(
                model=self.model_name,
                messages=self._build_messages(system_instruction, prompt),
                temperature=DEFAULT_TEMP,
                max_tokens=DEFAULT_MAX_TOKENS,
                extra_headers={
                    "HTTP-Referer": "[https://github.com/giangvien/edu-ai](https://github.com/giangvien/edu-ai)",
                    "X-Title": "AI Exam Generator"
                }
            )

            usage = res.usage

            return AIResponse(
                text=res.choices[0].message.content,
                provider="OpenRouter",
                model=self.model_name,
                latency=0.0,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0
            )

        except Exception as e:
            err_msg = str(e)

            if "401" in err_msg:
                raise AuthenticationError("Sai API Key OpenRouter.")

            if "402" in err_msg or "429" in err_msg or "credits" in err_msg.lower():
                raise QuotaExceededError(
                    "Hết Credits hoặc máy chủ OpenRouter quá tải."
                )

            if "timeout" in err_msg.lower():
                raise TimeoutError(
                    "Hết thời gian chờ (Timeout) khi gọi OpenRouter."
                )

            raise NetworkError(f"OpenRouter Error: {err_msg}")

    def _call_ollama(self, prompt: str, system_instruction: str) -> AIResponse:
        url = "http://localhost:11434/api/generate"
        payload = {"model": self.model_name, "prompt": f"{system_instruction}\n\n{prompt}" if system_instruction else prompt, "stream": False}
        res = requests.post(url, json=payload, timeout=self.timeout)
        res.raise_for_status()
        data = res.json()
        return AIResponse(text=data["response"], provider="Ollama", model=self.model_name, latency=0.0, prompt_tokens=data.get("prompt_eval_count", 0), completion_tokens=data.get("eval_count", 0), total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0))
