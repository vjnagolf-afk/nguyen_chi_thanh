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

# Các SDK Chính thức (Yêu cầu cài đặt)
from openai import OpenAI
import anthropic
from google import genai
from google.genai import types

# ==========================================
# 19. HẰNG SỐ CẤU HÌNH (CONSTANTS)
# ==========================================
DEFAULT_TIMEOUT = 120
DEFAULT_TEMP = 0.2
DEFAULT_MAX_TOKENS = 8192
DEFAULT_TOP_P = 0.95

# ==========================================
# 18. CHUẨN HÓA EXCEPTION
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
# 7. CHUẨN HÓA RESPONSE (DATACLASS)
# ==========================================
@dataclass
class AIResponse:
    """Cấu trúc dữ liệu chuẩn trả về từ mọi nhà cung cấp AI."""
    text: str
    provider: str
    model: str
    latency: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = "stop"

# ==========================================
# 13. CACHE TOÀN CỤC (GLOBAL CACHE)
# ==========================================
# Lưu trữ các phản hồi trong 1 giờ để giảm chi phí API
prompt_cache = TTLCache(maxsize=200, ttl=3600)

class AIEngine:
    """
    Trình điều khiển Trung tâm kết nối đa mô hình AI.
    Hỗ trợ: Gemini, OpenAI, Claude, OpenRouter, Ollama.
    """

    # 1. CHUẨN HÓA CONSTRUCTOR
    def __init__(
        self,
        provider_type: str,
        api_key: str,
        model_name: str,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """
        Khởi tạo AI Engine.

        Args:
            provider_type (str): Nhà cung cấp (VD: 'Gemini', 'OpenAI', 'Claude', 'OpenRouter', 'Ollama').
            api_key (str): Khóa API xác thực.
            model_name (str): Tên mô hình (VD: 'gpt-4o', 'gemini-2.5-flash').
            timeout (int, optional): Thời gian chờ tối đa. Mặc định 120s.
        """
        self.provider_type = provider_type.split()[0] # Lấy từ khóa chính, VD "Gemini (Direct)" -> "Gemini"
        self.api_key = api_key.strip()
        self.model_name = model_name.strip()
        self.timeout = timeout
        
        # 22. Tái sử dụng HTTP Connection cho REST API (OpenRouter/Ollama)
        self.session = requests.Session()
        
        # 2. Validate Provider & Model
        self._validate_provider()

    def _validate_provider(self):
        """Kiểm tra tính hợp lệ giữa Provider và Model Name."""
        model_lower = self.model_name.lower()
        if self.provider_type == "Gemini" and "gemini" not in model_lower:
            raise ModelNotFoundError(f"Model '{self.model_name}' không hợp lệ cho Gemini SDK. Cần chứa từ khóa 'gemini'.")
        if self.provider_type == "OpenAI" and "gpt" not in model_lower and "o1" not in model_lower:
            raise ModelNotFoundError(f"Model '{self.model_name}' không hợp lệ cho OpenAI. Cần chứa 'gpt' hoặc 'o1'.")
        if self.provider_type == "Anthropic" and "claude" not in model_lower:
            raise ModelNotFoundError(f"Model '{self.model_name}' không hợp lệ cho Claude. Cần chứa 'claude'.")

    # 3. TÁCH HÀM BUILD MESSAGE
    def _build_messages(self, system_instruction: str, prompt: str) -> List[Dict[str, str]]:
        """Xây dựng cấu trúc tin nhắn chuẩn cho định dạng chat completion."""
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        return messages

    # 8. HÀM KIỂM TRA KẾT NỐI
    def test_connection(self) -> bool:
        """Kiểm tra API Key, Model và Quota bằng một prompt cực nhỏ."""
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

    # 15. CƠ CHẾ FALLBACK TỰ ĐỘNG
    def generate_with_fallback(self, prompt: str, system_instruction: str = "") -> AIResponse:
        """
        Cố gắng gọi AI chính, nếu lỗi sẽ tự động chuyển đổi mô hình/nhà cung cấp.
        Luồng: Gemini -> OpenRouter -> OpenAI -> Anthropic.
        """
        fallbacks = [
            ("Gemini", "gemini-2.5-flash", self.api_key),
            ("OpenRouter", "google/gemini-2.5-flash", self.api_key), 
            ("OpenAI", "gpt-4o-mini", self.api_key),
            ("Anthropic", "claude-3-haiku-20240307", self.api_key)
        ]
        
        for provider, model, key in fallbacks:
            if not key:
                continue
            try:
                temp_engine = AIEngine(provider_type=provider, api_key=key, model_name=model, timeout=self.timeout)
                logger.warning(f"Đang thử Fallback với {provider} ({model})...")
                return temp_engine.generate_text(prompt, system_instruction)
            except Exception as e:
                logger.error(f"Fallback {provider} thất bại: {e}")
                
        raise AIEngineError("Tất cả các tuyến Fallback đều thất bại.")

    # 16. GENERATE ĐA ĐỊNH DẠNG
    def generate_json(self, prompt: str, system_instruction: str = "") -> AIResponse:
        """Ép AI trả về chuẩn JSON."""
        sys_json = system_instruction + "\nBẮT BUỘC TRẢ VỀ ĐỊNH DẠNG JSON. KHÔNG KÈM THEO MARKDOWN HAY VĂN BẢN NÀO KHÁC."
        return self.generate_text(prompt, sys_json)

    def generate_markdown(self, prompt: str, system_instruction: str = "") -> AIResponse:
        """Ép AI trả về Markdown."""
        sys_md = system_instruction + "\nBẮT BUỘC TRẢ VỀ ĐỊNH DẠNG MARKDOWN CHUẨN."
        return self.generate_text(prompt, sys_md)

    # ==========================================
    # HÀM LÕI (CORE GENERATION) VỚI RETRY (4) VÀ LOGGING (5)
    # ==========================================
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((NetworkError, TimeoutError))
    )
    def generate_text(self, prompt: str, system_instruction: str = "", stream: bool = False) -> Union[AIResponse, Generator]:
        """
        Gửi yêu cầu tới AI với các cơ chế bảo vệ.
        
        Args:
            prompt: Câu lệnh chính.
            system_instruction: Hướng dẫn hệ thống.
            stream: Nếu True, trả về Generator (Lưu ý: Không dùng cache khi stream).
        """
        # 13. CACHE THÔNG MINH
        cache_key = hash(f"{self.provider_type}_{self.model_name}_{system_instruction}_{prompt}")
        if not stream and cache_key in prompt_cache:
            logger.info("⚡ Trả về kết quả từ Cache.")
            return prompt_cache[cache_key]

        logger.info(f"🚀 Calling {self.provider_type} | Model: {self.model_name} | Prompt length: {len(prompt)}")
        start_time = time.time()

        try:
            # Điều hướng Provider
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

            # 6. TÍNH TOÁN LATENCY
            elapsed = time.time() - start_time
            response.latency = elapsed
            
            logger.info(f"✅ Success | Latency: {elapsed:.2f}s | Tokens (P/C/T): {response.prompt_tokens}/{response.completion_tokens}/{response.total_tokens}")
            
            if not stream:
                prompt_cache[cache_key] = response
                
            return response

        except requests.exceptions.Timeout:
            logger.error("⏳ Lỗi Timeout từ máy chủ.")
            raise TimeoutError("Kết nối quá thời gian chờ.")
        except Exception as e:
            logger.error(f"❌ Lỗi {self.provider_type}: {str(e)}")
            raise AIEngineError(f"Lỗi hệ thống AI: {str(e)}")

    # ==========================================
    # CÁC TRÌNH ĐIỀU KHIỂN CỤ THỂ (10, 11, 12)
    # ==========================================
    
    # 11. GEMINI BẰNG GOOGLE-GENAI SDK
    def _call_gemini_sdk(self, prompt: str, system_instruction: str) -> AIResponse:
        try:
            client = genai.Client(api_key=self.api_key)
            config = types.GenerateContentConfig(
                temperature=DEFAULT_TEMP,
                top_p=DEFAULT_TOP_P,
                max_output_tokens=DEFAULT_MAX_TOKENS,
                system_instruction=system_instruction if system_instruction else None
            )
            
            res = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            
            # Xử lý token (Google API metadata)
            usage = res.usage_metadata
            p_tokens = usage.prompt_token_count if usage else 0
            c_tokens = usage.candidates_token_count if usage else 0
            
            return AIResponse(
                text=res.text,
                provider="Gemini",
                model=self.model_name,
                latency=0.0,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                total_tokens=p_tokens + c_tokens
            )
        except Exception as e:
            if "API_KEY_INVALID" in str(e):
                raise AuthenticationError("API Key Gemini không hợp lệ.")
            raise NetworkError(str(e))

    # 10. OPENAI BẰNG OPENAI SDK
    def _call_openai(self, prompt: str, system_instruction: str) -> AIResponse:
        try:
            client = OpenAI(api_key=self.api_key, timeout=self.timeout)
            messages = self._build_messages(system_instruction, prompt)
            
            res = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=DEFAULT_TEMP,
                max_tokens=DEFAULT_MAX_TOKENS,
                top_p=DEFAULT_TOP_P
            )
            
            return AIResponse(
                text=res.choices[0].message.content,
                provider="OpenAI",
                model=self.model_name,
                latency=0.0,
                prompt_tokens=res.usage.prompt_tokens,
                completion_tokens=res.usage.completion_tokens,
                total_tokens=res.usage.total_tokens
            )
        except Exception as e:
            if "401" in str(e): raise AuthenticationError("Sai API Key OpenAI.")
            if "429" in str(e): raise QuotaExceededError("Hết Quota OpenAI.")
            raise NetworkError(str(e))

    # 12. CLAUDE BẰNG ANTHROPIC SDK
    def _call_anthropic(self, prompt: str, system_instruction: str) -> AIResponse:
        try:
            client = anthropic.Anthropic(api_key=self.api_key, timeout=self.timeout)
            
            res = client.messages.create(
                model=self.model_name,
                max_tokens=DEFAULT_MAX_TOKENS,
                temperature=DEFAULT_TEMP,
                system=system_instruction if system_instruction else anthropic.NOT_GIVEN,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return AIResponse(
                text=res.content[0].text,
                provider="Anthropic",
                model=self.model_name,
                latency=0.0,
                prompt_tokens=res.usage.input_tokens,
                completion_tokens=res.usage.output_tokens,
                total_tokens=res.usage.input_tokens + res.usage.output_tokens
            )
        except Exception as e:
            if "authentication" in str(e).lower(): raise AuthenticationError("Sai API Key Claude.")
            raise NetworkError(str(e))

    # 9. OPENROUTER VỚI XỬ LÝ LỖI MẠNH MẼ
    def _call_openrouter(self, prompt: str, system_instruction: str) -> AIResponse:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/giangvien/edu-ai",
            "X-Title": "AI Exam Generator"
        }
        
        payload = {
            "model": self.model_name,
            "messages": self._build_messages(system_instruction, prompt),
            "temperature": DEFAULT_TEMP
        }
        
        res = self.session.post(url, headers=headers, json=payload, timeout=self.timeout)
        
        if res.status_code in [429, 500, 502, 503, 504]:
            raise NetworkError(f"HTTP {res.status_code}: Máy chủ OpenRouter quá tải.")
            
        data = res.json()
        
        # 9. Validate lỗi sâu bên trong JSON
        if "error" in data:
            err_msg = data["error"].get("message", "Lỗi không xác định")
            if "auth" in err_msg.lower(): raise AuthenticationError(err_msg)
            raise AIEngineError(f"OpenRouter Error: {err_msg}")
            
        usage = data.get("usage", {})
        
        return AIResponse(
            text=data["choices"][0]["message"]["content"],
            provider="OpenRouter",
            model=self.model_name,
            latency=0.0,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0)
        )

    def _call_ollama(self, prompt: str, system_instruction: str) -> AIResponse:
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": f"{system_instruction}\n\n{prompt}" if system_instruction else prompt,
            "stream": False
        }
        
        res = self.session.post(url, json=payload, timeout=self.timeout)
        res.raise_for_status()
        
        data = res.json()
        return AIResponse(
            text=data["response"],
            provider="Ollama",
            model=self.model_name,
            latency=0.0,
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
        )
