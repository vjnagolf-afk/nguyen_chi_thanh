"""
============================================================
AI ENGINE PROVIDER - ENTERPRISE GATEWAY
Quản lý đa mô hình AI với cơ chế Retry, Logging, Caching và Fallback.
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

# ==========================================
# CÁC SDK CHÍNH THỨC
# ==========================================
from openai import OpenAI
import anthropic
from google import genai
from google.genai import types
from google.genai.errors import APIError

# ==========================================
# HẰNG SỐ CẤU HÌNH (CONSTANTS)
# ==========================================
DEFAULT_TIMEOUT = 120
DEFAULT_TEMP = 0.2
DEFAULT_MAX_TOKENS = 6000  # ĐÃ HẠ XUỐNG 6000 ĐỂ PHÙ HỢP VỚI TÍN DỤNG OPENROUTER HIỆN TẠI
DEFAULT_TOP_P = 0.95

# ==========================================
# CHUẨN HÓA EXCEPTION
# ==========================================
class AIEngineError(Exception):
    """Lớp Exception cơ sở cho toàn bộ AI Engine."""
    pass

class AuthenticationError(AIEngineError): pass
class ModelNotFoundError(AIEngineError): pass
class QuotaExceededError(AIEngineError): pass
class NetworkError(AIEngineError): pass
class TimeoutError(AIEngineError): pass

# ==========================================
# CHUẨN HÓA RESPONSE (DATACLASS)
# ==========================================
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
        
        self._is_ready = False
        if self.api_key or self.provider_type == "Ollama":
            self._is_ready = True
            
        self._validate_provider()

    def is_ready(self) -> bool:
        return self._is_ready

    def _validate_provider(self):
        model_lower = self.model_name.lower()
        if self.provider_type == "Gemini" and "gemini" not in model_lower:
            raise ModelNotFoundError(f"Model '{self.model_name}' không hợp lệ cho Gemini SDK.")
        if self.provider_type == "OpenAI" and "gpt" not in model_lower and "o1" not in model_lower:
            raise ModelNotFoundError(f"Model '{self.model_name}' không hợp lệ cho OpenAI.")
        if self.provider_type == "Anthropic" and "claude" not in model_lower:
            raise ModelNotFoundError(f"Model '{self.model_name}' không hợp lệ cho Claude.")

    def _build_messages(self, system_instruction: str, prompt: str) -> List[Dict[str, str]]:
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        return messages

    def test_connection(self) -> bool:
        logger.info(f"Đang kiểm tra kết nối tới {self.provider_type} - Model: {self.model_name}")
        try:
            res = self.generate_text(prompt="Ping.", system_instruction="Chỉ trả lời 'Pong'.")
            if res and len(res.text) > 0:
                logger.info(f"✅ Kết nối {self.provider_type} thành công. Latency: {res.latency:.2f}s")
                return True
        except Exception as e:
            logger.error(f"❌ Kết nối thất bại: {str(e)}")
            raise AuthenticationError(f"Kiểm tra kết nối thất bại: {str(e)}")
        return False

    def generate_with_fallback(self, prompt: str, system_instruction: str = "") -> AIResponse:
        fallbacks = [
            ("OpenRouter", "google/gemini-2.5-flash", self.api_key), 
            ("OpenAI", "gpt-4o-mini", self.api_key),
            ("Anthropic", "claude-3-haiku-20240307", self.api_key)
        ]
        
        for provider, model, key in fallbacks:
            if not key:
                continue
            try:
                temp_engine = AIEngine(provider_type=provider, api_key=key, model_name=model, timeout=self.timeout)
                return temp_engine.generate_text(prompt, system_instruction)
            except Exception as e:
                logger.error(f"Fallback {provider} thất bại: {e}")
                
        raise AIEngineError("Tất cả các tuyến Fallback đều thất bại.")

    def generate_json(self, prompt: str, system_instruction: str = "") -> AIResponse:
        sys_json = system_instruction + "\nBẮT BUỘC TRẢ VỀ ĐỊNH DẠNG JSON. KHÔNG KÈM THEO MARKDOWN HAY VĂN BẢN NÀO KHÁC."
        return self.generate_text(prompt, sys_json)

    def generate_markdown(self, prompt: str, system_instruction: str = "") -> AIResponse:
        sys_md = system_instruction + "\nBẮT BUỘC TRẢ VỀ ĐỊNH DẠNG MARKDOWN CHUẨN."
        return self.generate_text(prompt, sys_md)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((NetworkError, TimeoutError))
    )
    def generate_text(self, prompt: str, system_instruction: str = "", stream: bool = False) -> Union[AIResponse, Generator]:
        if not self.is_ready():
            raise AuthenticationError("Hệ thống AI chưa sẵn sàng.")

        cache_key = hash(f"{self.provider_type}_{self.model_name}_{system_instruction}_{prompt}")
        if not stream and cache_key in prompt_cache:
            return prompt_cache[cache_key]

        start_time = time.time()
        try:
            if self.provider_type == "Gemini":
                response = self._call_gemini_sdk(prompt, system_instruction)
            elif self.provider_type == "OpenAI":
                response = self._call_openai(prompt, system_instruction)
            elif self.provider_type == "Anthropic":
                response = self._call_anthropic(prompt, system_instruction)
            elif self.provider_type == "OpenRouter":
                response = self._call_openrouter(prompt, system_instruction)
            elif self.provider_type == "Ollama":
                response = self._call_ollama(prompt, system_instruction)
            else:
                raise AIEngineError(f"Provider {self.provider_type} chưa được hỗ trợ.")

            elapsed = time.time() - start_time
            response.latency = elapsed
            if not stream:
                prompt_cache[cache_key] = response
            return response
        except requests.exceptions.Timeout:
            raise TimeoutError("Kết nối quá thời gian chờ.")
        except Exception as e:
            raise AIEngineError(f"{str(e)}")

    def _call_gemini_sdk(self, prompt: str, system_instruction: str) -> AIResponse:
        try:
            client = genai.Client(api_key=self.api_key)
            config = types.GenerateContentConfig(
                temperature=DEFAULT_TEMP,
                top_p=DEFAULT_TOP_P,
                max_output_tokens=DEFAULT_MAX_TOKENS,
                system_instruction=system_instruction if system_instruction else None
            )
            res = client.models.generate_content(model=self.model_name, contents=prompt, config=config)
            usage = res.usage_metadata
            return AIResponse(
                text=res.text, provider="Gemini", model=self.model_name, latency=0.0,
                prompt_tokens=usage.prompt_token_count if usage else 0,
                completion_tokens=usage.candidates_token_count if usage else 0,
                total_tokens=(usage.prompt_token_count + usage.candidates_token_count) if usage else 0
            )
        except APIError as e:
            if "oauth" in str(e).lower():
                raise AuthenticationError("Khóa bảo mật là mã OAuth tạm thời. Vui lòng chuyển sang 'OpenRouter'.")
            raise NetworkError(f"Lỗi API Gemini: {str(e)}")
        except Exception as e:
            raise NetworkError(f"Lỗi kết nối SDK Gemini: {str(e)}")

    def _call_openai(self, prompt: str, system_instruction: str) -> AIResponse:
        try:
            client = OpenAI(api_key=self.api_key, timeout=self.timeout)
            res = client.chat.completions.create(
                model=self.model_name, messages=self._build_messages(system_instruction, prompt),
                temperature=DEFAULT_TEMP, max_tokens=DEFAULT_MAX_TOKENS, top_p=DEFAULT_TOP_P
            )
            return AIResponse(
                text=res.choices[0].message.content, provider="OpenAI", model=self.model_name, latency=0.0,
                prompt_tokens=res.usage.prompt_tokens, completion_tokens=res.usage.completion_tokens, total_tokens=res.usage.total_tokens
            )
        except Exception as e:
            if "401" in str(e): raise AuthenticationError("Sai API Key OpenAI.")
            if "429" in str(e): raise QuotaExceededError("Hết Quota OpenAI.")
            raise NetworkError(str(e))

    def _call_anthropic(self, prompt: str, system_instruction: str) -> AIResponse:
        try:
            client = anthropic.Anthropic(api_key=self.api_key, timeout=self.timeout)
            res = client.messages.create(
                model=self.model_name, max_tokens=DEFAULT_MAX_TOKENS, temperature=DEFAULT_TEMP,
                system=system_instruction if system_instruction else anthropic.NOT_GIVEN,
                messages=[{"role": "user", "content": prompt}]
            )
            return AIResponse(
                text=res.content[0].text, provider="Anthropic", model=self.model_name, latency=0.0,
                prompt_tokens=res.usage.input_tokens, completion_tokens=res.usage.output_tokens, total_tokens=res.usage.input_tokens + res.usage.output_tokens
            )
        except Exception as e:
            if "authentication" in str(e).lower(): raise AuthenticationError("Sai API Key Claude.")
            raise NetworkError(str(e))

    def _call_openrouter(self, prompt: str, system_instruction: str) -> AIResponse:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model_name,
            "messages": self._build_messages(system_instruction, prompt),
            "temperature": DEFAULT_TEMP,
            "max_tokens": DEFAULT_MAX_TOKENS
        }
        res = self.session.post(url, headers=headers, json=payload, timeout=self.timeout)
        if res.status_code in [429, 500, 502, 503, 504]:
            raise NetworkError(f"HTTP {res.status_code}: Máy chủ OpenRouter quá tải.")
        data = res.json()
        if "error" in data:
            err_msg = data["error"].get("message", "Lỗi không xác định")
            if "auth" in err_msg.lower(): raise AuthenticationError(err_msg)
            if "credits" in err_msg.lower(): raise QuotaExceededError(err_msg)
            raise AIEngineError(f"OpenRouter Error: {err_msg}")
        return AIResponse(
            text=data["choices"][0]["message"]["content"], provider="OpenRouter", model=self.model_name, latency=0.0,
            prompt_tokens=data.get("usage", {}).get("prompt_tokens", 0),
            completion_tokens=data.get("usage", {}).get("completion_tokens", 0),
            total_tokens=data.get("usage", {}).get("total_tokens", 0)
        )

    def _call_ollama(self, prompt: str, system_instruction: str) -> AIResponse:
        url = "http://localhost:11434/api/generate"
        res = self.session.post(url, json={"model": self.model_name, "prompt": f"{system_instruction}\n\n{prompt}" if system_instruction else prompt, "stream": False}, timeout=self.timeout)
        res.raise_for_status()
        data = res.json()
        return AIResponse(
            text=data["response"], provider="Ollama", model=self.model_name, latency=0.0,
            prompt_tokens=data.get("prompt_eval_count", 0), completion_tokens=data.get("eval_count", 0), total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
        )
