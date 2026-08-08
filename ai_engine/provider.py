"""
============================================================
AI ENGINE PROVIDER - ENTERPRISE GATEWAY
============================================================
"""

import time
from dataclasses import dataclass
from typing import List, Dict, Union, Generator
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
DEFAULT_MAX_TOKENS = 8192  # Cần mức này để sinh đủ toàn bộ Đề và Đáp án
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

    def is_ready(self) -> bool: return self._is_ready

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
        try:
            res = self.generate_text(prompt="Ping.", system_instruction="Chỉ trả lời 'Pong'.")
            return bool(res and res.text)
        except Exception as e:
            raise AuthenticationError(f"Kiểm tra kết nối thất bại: {str(e)}")

    def generate_with_fallback(self, prompt: str, system_instruction: str = "") -> AIResponse:
        # CHỈ FALLBACK TRONG CÙNG PROVIDER ĐỂ TRÁNH LỖI SAI API KEY
        fallbacks = []
        if self.provider_type == "OpenRouter":
            fallbacks = ["google/gemini-2.5-flash", "google/gemini-1.5-pro", "meta-llama/llama-3-8b-instruct"]
        elif self.provider_type == "Gemini":
            fallbacks = ["gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash"]
            
        for fallback_model in fallbacks:
            try:
                temp_engine = AIEngine(provider_type=self.provider_type, api_key=self.api_key, model_name=fallback_model, timeout=self.timeout)
                return temp_engine.generate_text(prompt, system_instruction)
            except Exception as e:
                logger.warning(f"Fallback model {fallback_model} thất bại: {e}")
                
        return self.generate_text(prompt, system_instruction) # Gọi thẳng nếu không có fallback

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type((NetworkError, TimeoutError)))
    def generate_text(self, prompt: str, system_instruction: str = "", stream: bool = False) -> Union[AIResponse, Generator]:
        if not self.is_ready(): raise AuthenticationError("AI chưa sẵn sàng.")

        # Cache key phải chứa prompt hash để không bị trùng lặp khi config đổi
        cache_key = hash(f"{self.provider_type}_{self.model_name}_{system_instruction}_{prompt}")
        if not stream and cache_key in prompt_cache: return prompt_cache[cache_key]

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
        except requests.exceptions.Timeout: raise TimeoutError("Timeout kết nối.")
        except Exception as e: raise e # Giữ nguyên loại Exception để tầng trên xử lý

    # --- CÁC HÀM GỌI SDK BÊN DƯỚI GIỮ NGUYÊN NHƯ BẢN TRƯỚC, CHỈ SỬA LẠI CÁCH RAISE LỖI ---
    def _call_openrouter(self, prompt: str, system_instruction: str) -> AIResponse:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": self.model_name, "messages": self._build_messages(system_instruction, prompt), "temperature": DEFAULT_TEMP, "max_tokens": DEFAULT_MAX_TOKENS}
        res = self.session.post(url, headers=headers, json=payload, timeout=self.timeout)
        
        if res.status_code == 401: raise AuthenticationError("Sai API Key OpenRouter.")
        if res.status_code == 402 or res.status_code == 429: raise QuotaExceededError("Hết Credits OpenRouter.")
        if res.status_code >= 500: raise NetworkError(f"Lỗi Server OpenRouter: {res.status_code}")
        
        data = res.json()
        if "error" in data: raise AIEngineError(data["error"].get("message", "Lỗi không xác định"))
        
        return AIResponse(
            text=data["choices"][0]["message"]["content"], provider="OpenRouter", model=self.model_name, latency=0.0,
            prompt_tokens=data.get("usage", {}).get("prompt_tokens", 0), completion_tokens=data.get("usage", {}).get("completion_tokens", 0), total_tokens=data.get("usage", {}).get("total_tokens", 0)
        )
    # (Các hàm _call_gemini_sdk, _call_openai... tương tự)
