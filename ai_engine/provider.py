"""
AI ENGINE PROVIDER - ENTERPRISE GATEWAY
========================================
Hỗ trợ:
- OpenRouter
- Gemini Direct
- OpenAI Direct
- Anthropic / Claude
- Ollama Local

Mục tiêu:
- API thống nhất cho toàn hệ thống.
- Phân loại lỗi rõ ràng.
- Retry chỉ dành cho lỗi mạng / timeout.
- Không retry lỗi API Key / quota / model.
- Fallback chỉ khi phù hợp.
- Không để Markdown URL lọt vào cấu hình.
"""

import time
from dataclasses import dataclass
from typing import List, Dict, Union, Generator

import requests
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from cachetools import TTLCache

from openai import OpenAI
import anthropic

from google import genai
from google.genai import types


# ============================================================
# 1. CẤU HÌNH CHUNG
# ============================================================

DEFAULT_TIMEOUT = 120
DEFAULT_TEMP = 0.2
DEFAULT_MAX_TOKENS = 8192
DEFAULT_TOP_P = 0.95

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_REFERER = "https://github.com/giangvien/edu-ai"
OPENROUTER_TITLE = "AI Exam Generator"

OLLAMA_BASE_URL = "http://localhost:11434"


# ============================================================
# 2. CUSTOM EXCEPTIONS
# ============================================================

class AIEngineError(Exception):
    """Lỗi tổng quát của AI Engine."""


class AuthenticationError(AIEngineError):
    """API Key sai hoặc không có quyền."""


class ModelNotFoundError(AIEngineError):
    """Model không tồn tại / không khả dụng."""


class QuotaExceededError(AIEngineError):
    """Hết quota / credits / rate limit."""


class NetworkError(AIEngineError):
    """Lỗi mạng / server."""


class TimeoutError(AIEngineError):
    """Quá thời gian chờ."""


# ============================================================
# 3. RESPONSE OBJECT
# ============================================================

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


# ============================================================
# 4. CACHE
# ============================================================

prompt_cache = TTLCache(
    maxsize=200,
    ttl=3600,
)


# ============================================================
# 5. AI ENGINE
# ============================================================

class AIEngine:

    def __init__(
        self,
        provider_type: str,
        api_key: str,
        model_name: str,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.provider_type = provider_type.strip().split()[0]
        self.api_key = (api_key or "").strip()
        self.model_name = (model_name or "").strip()
        self.timeout = timeout

        self.session = requests.Session()

        # Ollama không cần API key.
        self._is_ready = bool(
            self.api_key
            or self.provider_type == "Ollama"
        )

        self._validate_provider()

    # ========================================================
    # BASIC
    # ========================================================

    def is_ready(self) -> bool:
        return self._is_ready

    # ========================================================
    # VALIDATE PROVIDER
    # ========================================================

    def _validate_provider(self):

        model_lower = self.model_name.lower()

        if not self.model_name:
            raise ModelNotFoundError(
                "Chưa nhập tên model."
            )

        if self.provider_type == "Gemini":

            if "gemini" not in model_lower:
                raise ModelNotFoundError(
                    "Model không đúng định dạng Gemini."
                )

        elif self.provider_type == "OpenAI":

            if (
                "gpt" not in model_lower
                and "o1" not in model_lower
                and "o3" not in model_lower
                and "o4" not in model_lower
            ):
                raise ModelNotFoundError(
                    "Model không đúng định dạng OpenAI."
                )

        elif self.provider_type == "Anthropic":

            if "claude" not in model_lower:
                raise ModelNotFoundError(
                    "Model không đúng định dạng Claude."
                )

        elif self.provider_type == "OpenRouter":

            # OpenRouter dùng dạng:
            # provider/model
            if "/" not in self.model_name:
                raise ModelNotFoundError(
                    "Model OpenRouter phải có dạng provider/model."
                )

        elif self.provider_type == "Ollama":

            # Ollama không cần kiểm tra API key.
            pass

        else:

            raise AIEngineError(
                f"Provider không được hỗ trợ: {self.provider_type}"
            )

    # ========================================================
    # BUILD MESSAGES
    # ========================================================

    def _build_messages(
        self,
        system_instruction: str,
        prompt: str,
    ) -> List[Dict[str, str]]:

        messages = []

        if system_instruction:
            messages.append(
                {
                    "role": "system",
                    "content": system_instruction,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        return messages

    # ========================================================
    # TEST CONNECTION
    # ========================================================

    def test_connection(self) -> bool:
        """
        Kiểm tra kết nối AI.

        Không che giấu lỗi:
        - AuthenticationError
        - ModelNotFoundError
        - QuotaExceededError
        - NetworkError
        - TimeoutError
        """

        try:

            response = self.generate_text(
                prompt="Ping.",
                system_instruction=(
                    "Chỉ trả lời đúng một từ: Pong."
                ),
            )

            return bool(
                response
                and response.text
                and response.text.strip()
            )

        except (
            AuthenticationError,
            ModelNotFoundError,
            QuotaExceededError,
            NetworkError,
            TimeoutError,
        ):
            raise

        except Exception as exc:

            raise NetworkError(
                f"Lỗi hệ thống hoặc đường truyền: {exc}"
            )

    # ========================================================
    # FALLBACK
    # ========================================================

    def generate_with_fallback(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> AIResponse:

        # ----------------------------------------------------
        # 1. Luôn thử model chính trước.
        # ----------------------------------------------------

        try:

            return self.generate_text(
                prompt,
                system_instruction,
            )

        except AuthenticationError:
            # Sai API key -> KHÔNG fallback.
            raise

        except QuotaExceededError:
            # Hết tiền/quota -> KHÔNG fallback.
            raise

        except ModelNotFoundError as main_error:

            logger.warning(
                f"Model chính không khả dụng: "
                f"{self.model_name}"
            )

            original_error = main_error

        except (
            NetworkError,
            TimeoutError,
        ) as main_error:

            logger.warning(
                f"Model chính gặp lỗi mạng/timeout: "
                f"{main_error}"
            )

            original_error = main_error

        except Exception as main_error:

            logger.error(
                f"Lỗi ngoài dự kiến: {main_error}"
            )

            raise

        # ----------------------------------------------------
        # 2. Danh sách fallback.
        # ----------------------------------------------------

        fallbacks = []

        if self.provider_type == "OpenRouter":

            fallbacks = [
                "google/gemini-2.5-flash",
                "openai/gpt-4o-mini",
                "anthropic/claude-sonnet-4",
            ]

        elif self.provider_type == "Gemini":

            fallbacks = [
                "gemini-2.5-flash",
                "gemini-2.0-flash",
            ]

        elif self.provider_type == "OpenAI":

            fallbacks = [
                "gpt-4o-mini",
            ]

        # Anthropic và Ollama:
        # Không tự ý fallback sang provider khác.

        # ----------------------------------------------------
        # 3. Thử fallback.
        # ----------------------------------------------------

        for fallback_model in fallbacks:

            if fallback_model == self.model_name:
                continue

            try:

                logger.warning(
                    f"Đang thử fallback: "
                    f"{self.provider_type} → "
                    f"{fallback_model}"
                )

                fallback_engine = AIEngine(
                    provider_type=self.provider_type,
                    api_key=self.api_key,
                    model_name=fallback_model,
                    timeout=self.timeout,
                )

                return fallback_engine.generate_text(
                    prompt,
                    system_instruction,
                )

            except AuthenticationError:
                # API key sai -> dừng.
                raise

            except QuotaExceededError:
                # Hết quota -> dừng.
                raise

            except (
                ModelNotFoundError,
                NetworkError,
                TimeoutError,
            ) as exc:

                logger.warning(
                    f"Fallback {fallback_model} thất bại: "
                    f"{exc}"
                )

        # ----------------------------------------------------
        # 4. Tất cả fallback thất bại.
        # ----------------------------------------------------

        raise original_error

    # ========================================================
    # GENERATE JSON
    # ========================================================

    def generate_json(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> AIResponse:

        sys_json = (
            system_instruction
            + "\n\n"
            "BẮT BUỘC TRẢ VỀ JSON HỢP LỆ."
            "\n"
            "KHÔNG dùng ```json."
            "\n"
            "KHÔNG thêm lời giải thích."
            "\n"
            "CHỈ TRẢ VỀ JSON."
        )

        return self.generate_text(
            prompt,
            sys_json,
        )

    # ========================================================
    # GENERATE MARKDOWN
    # ========================================================

    def generate_markdown(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> AIResponse:

        sys_md = (
            system_instruction
            + "\n\n"
            "BẮT BUỘC TRẢ VỀ MARKDOWN CHUẨN."
        )

        return self.generate_text(
            prompt,
            sys_md,
        )

    # ========================================================
    # GENERATE TEXT
    # ========================================================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(
            multiplier=1,
            min=2,
            max=10,
        ),
        retry=retry_if_exception_type(
            (
                NetworkError,
                TimeoutError,
            )
        ),
        reraise=True,
    )
    def generate_text(
        self,
        prompt: str,
        system_instruction: str = "",
        stream: bool = False,
    ) -> Union[AIResponse, Generator]:

        if not self.is_ready():

            raise AuthenticationError(
                "AI chưa sẵn sàng hoặc chưa có API Key."
            )

        # ----------------------------------------------------
        # CACHE
        # ----------------------------------------------------

        cache_key = hash(
            (
                self.provider_type,
                self.model_name,
                system_instruction,
                prompt,
            )
        )

        if (
            not stream
            and cache_key in prompt_cache
        ):
            return prompt_cache[cache_key]

        start_time = time.time()

        try:

            # ------------------------------------------------
            # PROVIDER DISPATCH
            # ------------------------------------------------

            if self.provider_type == "Gemini":

                response = self._call_gemini(
                    prompt,
                    system_instruction,
                )

            elif self.provider_type == "OpenAI":

                response = self._call_openai(
                    prompt,
                    system_instruction,
                )

            elif self.provider_type == "Anthropic":

                response = self._call_anthropic(
                    prompt,
                    system_instruction,
                )

            elif self.provider_type == "OpenRouter":

                response = self._call_openrouter(
                    prompt,
                    system_instruction,
                )

            elif self.provider_type == "Ollama":

                response = self._call_ollama(
                    prompt,
                    system_instruction,
                )

            else:

                raise AIEngineError(
                    f"Provider không hỗ trợ: "
                    f"{self.provider_type}"
                )

            response.latency = (
                time.time() - start_time
            )

            if not stream:
                prompt_cache[cache_key] = response

            return response

        except requests.exceptions.Timeout:

            raise TimeoutError(
                "Timeout kết nối máy chủ AI."
            )

        except (
            AuthenticationError,
            ModelNotFoundError,
            QuotaExceededError,
            NetworkError,
            TimeoutError,
        ):

            raise

        except Exception as exc:

            raise NetworkError(
                f"Lỗi AI Provider: {exc}"
            )

    # ========================================================
    # GEMINI
    # ========================================================

    def _call_gemini(
        self,
        prompt: str,
        system_instruction: str,
    ) -> AIResponse:

        try:

            client = genai.Client(
                api_key=self.api_key
            )

            config = types.GenerateContentConfig(
                temperature=DEFAULT_TEMP,
                top_p=DEFAULT_TOP_P,
                max_output_tokens=DEFAULT_MAX_TOKENS,
                system_instruction=(
                    system_instruction
                    if system_instruction
                    else None
                ),
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )

            usage = getattr(
                response,
                "usage_metadata",
                None,
            )

            prompt_tokens = (
                getattr(
                    usage,
                    "prompt_token_count",
                    0,
                )
                if usage
                else 0
            )

            completion_tokens = (
                getattr(
                    usage,
                    "candidates_token_count",
                    0,
                )
                if usage
                else 0
            )

            return AIResponse(
                text=response.text or "",
                provider="Gemini",
                model=self.model_name,
                latency=0.0,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=(
                    prompt_tokens
                    + completion_tokens
                ),
            )

        except Exception as exc:

            self._raise_provider_error(
                "Gemini",
                exc,
            )

            raise

    # ========================================================
    # OPENAI
    # ========================================================

    def _call_openai(
        self,
        prompt: str,
        system_instruction: str,
    ) -> AIResponse:

        try:

            client = OpenAI(
                api_key=self.api_key,
                timeout=self.timeout,
            )

            response = client.chat.completions.create(
                model=self.model_name,
                messages=self._build_messages(
                    system_instruction,
                    prompt,
                ),
                temperature=DEFAULT_TEMP,
                max_tokens=DEFAULT_MAX_TOKENS,
                top_p=DEFAULT_TOP_P,
            )

            usage = response.usage

            return AIResponse(
                text=(
                    response.choices[0]
                    .message.content
                    or ""
                ),
                provider="OpenAI",
                model=self.model_name,
                latency=0.0,
                prompt_tokens=(
                    usage.prompt_tokens
                    if usage
                    else 0
                ),
                completion_tokens=(
                    usage.completion_tokens
                    if usage
                    else 0
                ),
                total_tokens=(
                    usage.total_tokens
                    if usage
                    else 0
                ),
                finish_reason=(
                    response.choices[0].finish_reason
                    or "stop"
                ),
            )

        except Exception as exc:

            self._raise_provider_error(
                "OpenAI",
                exc,
            )

            raise

    # ========================================================
    # ANTHROPIC
    # ========================================================

    def _call_anthropic(
        self,
        prompt: str,
        system_instruction: str,
    ) -> AIResponse:

        try:

            client = anthropic.Anthropic(
                api_key=self.api_key,
                timeout=self.timeout,
            )

            response = client.messages.create(
                model=self.model_name,
                max_tokens=DEFAULT_MAX_TOKENS,
                temperature=DEFAULT_TEMP,
                system=(
                    system_instruction
                    if system_instruction
                    else anthropic.NOT_GIVEN
                ),
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            input_tokens = getattr(
                response.usage,
                "input_tokens",
                0,
            )

            output_tokens = getattr(
                response.usage,
                "output_tokens",
                0,
            )

            return AIResponse(
                text=(
                    response.content[0].text
                    if response.content
                    else ""
                ),
                provider="Anthropic",
                model=self.model_name,
                latency=0.0,
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
                total_tokens=(
                    input_tokens
                    + output_tokens
                ),
                finish_reason=(
                    getattr(
                        response,
                        "stop_reason",
                        None,
                    )
                    or "stop"
                ),
            )

        except Exception as exc:

            self._raise_provider_error(
                "Anthropic",
                exc,
            )

            raise

    # ========================================================
    # OPENROUTER
    # ========================================================

    def _call_openrouter(
        self,
        prompt: str,
        system_instruction: str,
    ) -> AIResponse:

        try:

            # QUAN TRỌNG:
            # Đây là URL THUẦN.
            # Tuyệt đối không thêm []() Markdown.

            client = OpenAI(
                base_url=OPENROUTER_BASE_URL,
                api_key=self.api_key,
                timeout=self.timeout,
            )

            response = client.chat.completions.create(
                model=self.model_name,
                messages=self._build_messages(
                    system_instruction,
                    prompt,
                ),
                temperature=DEFAULT_TEMP,
                max_tokens=DEFAULT_MAX_TOKENS,
                extra_headers={
                    "HTTP-Referer": OPENROUTER_REFERER,
                    "X-Title": OPENROUTER_TITLE,
                },
            )

            usage = response.usage

            return AIResponse(
                text=(
                    response.choices[0]
                    .message.content
                    or ""
                ),
                provider="OpenRouter",
                model=self.model_name,
                latency=0.0,
                prompt_tokens=(
                    usage.prompt_tokens
                    if usage
                    else 0
                ),
                completion_tokens=(
                    usage.completion_tokens
                    if usage
                    else 0
                ),
                total_tokens=(
                    usage.total_tokens
                    if usage
                    else 0
                ),
                finish_reason=(
                    response.choices[0].finish_reason
                    or "stop"
                ),
            )

        except Exception as exc:

            self._raise_provider_error(
                "OpenRouter",
                exc,
            )

            raise

    # ========================================================
    # OLLAMA
    # ========================================================

    def _call_ollama(
        self,
        prompt: str,
        system_instruction: str,
    ) -> AIResponse:

        url = (
            f"{OLLAMA_BASE_URL}/api/generate"
        )

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": system_instruction,
            "stream": False,
        }

        try:

            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout,
            )

            response.raise_for_status()

            data = response.json()

            return AIResponse(
                text=data.get(
                    "response",
                    "",
                ),
                provider="Ollama",
                model=self.model_name,
                latency=0.0,
                prompt_tokens=data.get(
                    "prompt_eval_count",
                    0,
                ),
                completion_tokens=data.get(
                    "eval_count",
                    0,
                ),
                total_tokens=(
                    data.get(
                        "prompt_eval_count",
                        0,
                    )
                    + data.get(
                        "eval_count",
                        0,
                    )
                ),
            )

        except requests.exceptions.ConnectionError:

            raise NetworkError(
                "Không thể kết nối Ollama. "
                "Nếu đang chạy Streamlit Cloud, "
                "localhost là máy chủ Cloud chứ "
                "không phải máy tính cá nhân."
            )

        except requests.exceptions.Timeout:

            raise TimeoutError(
                "Timeout khi kết nối Ollama."
            )

        except requests.exceptions.HTTPError as exc:

            status = (
                response.status_code
                if response
                else 0
            )

            if status == 404:

                raise ModelNotFoundError(
                    f"Model Ollama '{self.model_name}' "
                    "không tồn tại."
                )

            raise NetworkError(
                f"Ollama HTTP {status}: {exc}"
            )

        except Exception as exc:

            raise NetworkError(
                f"Lỗi Ollama: {exc}"
            )

    # ========================================================
    # ERROR MAPPING
    # ========================================================

    @staticmethod
    def _raise_provider_error(
        provider: str,
        exc: Exception,
    ):

        error_text = str(exc)
        error_lower = error_text.lower()

        # ----------------------------------------------------
        # Authentication
        # ----------------------------------------------------

        if any(
            x in error_lower
            for x in [
                "401",
                "unauthorized",
                "authentication",
                "invalid api key",
                "invalid_api_key",
                "api key is invalid",
                "forbidden",
                "403",
            ]
        ):

            raise AuthenticationError(
                f"{provider}: API Key không hợp lệ "
                "hoặc không có quyền truy cập."
            )

        # ----------------------------------------------------
        # Model
        # ----------------------------------------------------

        if any(
            x in error_lower
            for x in [
                "404",
                "model not found",
                "model_not_found",
                "does not exist",
                "unknown model",
            ]
        ):

            raise ModelNotFoundError(
                f"{provider}: Model không tồn tại "
                "hoặc không khả dụng."
            )

        # ----------------------------------------------------
        # Quota / Rate limit
        # ----------------------------------------------------

        if any(
            x in error_lower
            for x in [
                "402",
                "429",
                "quota",
                "rate limit",
                "rate_limit",
                "too many requests",
                "credits",
                "insufficient balance",
            ]
        ):

            raise QuotaExceededError(
                f"{provider}: Hết quota/credits "
                "hoặc vượt giới hạn request."
            )

        # ----------------------------------------------------
        # Timeout
        # ----------------------------------------------------

        if any(
            x in error_lower
            for x in [
                "timeout",
                "timed out",
                "time out",
            ]
        ):

            raise TimeoutError(
                f"{provider}: Timeout kết nối."
            )

        # ----------------------------------------------------
        # Network
        # ----------------------------------------------------

        if any(
            x in error_lower
            for x in [
                "connection",
                "connect",
                "network",
                "dns",
                "ssl",
                "socket",
                "temporarily unavailable",
                "server error",
                "502",
                "503",
                "504",
            ]
        ):

            raise NetworkError(
                f"{provider}: Lỗi mạng/server: "
                f"{error_text}"
            )

        # ----------------------------------------------------
        # Unknown
        # ----------------------------------------------------

        raise NetworkError(
            f"{provider}: {error_text}"
        )
