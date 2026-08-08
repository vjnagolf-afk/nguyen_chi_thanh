"""
AI ENGINE PROVIDER - STABLE GATEWAY
===================================

Hỗ trợ:
- OpenAI Direct
- OpenRouter
- Gemini Direct
- Anthropic / Claude
- Ollama Local

Nguyên tắc:
- Một interface thống nhất cho toàn hệ thống.
- Phân loại lỗi rõ ràng.
- Không retry API Key / quota / model.
- Chỉ retry lỗi mạng / timeout.
- Không fallback khi API Key hoặc quota bị lỗi.
- OpenRouter sử dụng OpenAI-compatible API.
- Không sử dụng Markdown URL trong cấu hình.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Dict, Generator, List, Union

import requests
from cachetools import TTLCache
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from openai import OpenAI
import anthropic

from google import genai
from google.genai import types


# ============================================================
# 1. CONFIGURATION
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
# 2. EXCEPTIONS
# ============================================================

class AIEngineError(Exception):
    """Lỗi tổng quát của AI Engine."""


class AuthenticationError(AIEngineError):
    """API Key sai hoặc không có quyền."""


class ModelNotFoundError(AIEngineError):
    """Model không tồn tại hoặc không khả dụng."""


class QuotaExceededError(AIEngineError):
    """Hết quota / credits / rate limit."""


class NetworkError(AIEngineError):
    """Lỗi mạng hoặc server."""


class TimeoutError(AIEngineError):
    """Quá thời gian chờ."""


# ============================================================
# 3. RESPONSE
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
        api_key: str = "",
        model_name: str = "",
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.provider_type = (
            (provider_type or "")
            .strip()
            .split()[0]
            if provider_type
            else ""
        )

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

    def _validate_provider(self) -> None:

        if not self.provider_type:
            raise AIEngineError(
                "Chưa xác định AI Provider."
            )

        if not self.model_name:
            raise ModelNotFoundError(
                "Chưa nhập tên model."
            )

        model = self.model_name.lower()

        if self.provider_type == "Gemini":

            if "gemini" not in model:
                raise ModelNotFoundError(
                    "Model Gemini không hợp lệ."
                )

        elif self.provider_type == "OpenAI":

            if not any(
                key in model
                for key in (
                    "gpt",
                    "o1",
                    "o3",
                    "o4",
                )
            ):
                raise ModelNotFoundError(
                    "Model OpenAI không hợp lệ."
                )

        elif self.provider_type == "Anthropic":

            if "claude" not in model:
                raise ModelNotFoundError(
                    "Model Anthropic không hợp lệ."
                )

        elif self.provider_type == "OpenRouter":

            if "/" not in self.model_name:
                raise ModelNotFoundError(
                    "Model OpenRouter phải có dạng provider/model."
                )

        elif self.provider_type == "Ollama":

            pass

        else:

            raise AIEngineError(
                f"Provider không được hỗ trợ: "
                f"{self.provider_type}"
            )

    # ========================================================
    # BUILD MESSAGES
    # ========================================================

    def _build_messages(
        self,
        system_instruction: str,
        prompt: str,
    ) -> List[Dict[str, str]]:

        messages: List[Dict[str, str]] = []

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
            ) from exc

    # ========================================================
    # FALLBACK
    # ========================================================

    def generate_with_fallback(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> AIResponse:

        try:

            return self.generate_text(
                prompt,
                system_instruction,
            )

        except AuthenticationError:
            # Sai API Key -> KHÔNG fallback.
            raise

        except QuotaExceededError:
            # Hết quota -> KHÔNG fallback.
            raise

        except (
            ModelNotFoundError,
            NetworkError,
            TimeoutError,
        ) as main_error:

            logger.warning(
                f"{self.provider_type}/{self.model_name} "
                f"không khả dụng: {main_error}"
            )

            original_error = main_error

        # ----------------------------------------------------
        # Fallback cùng provider
        # ----------------------------------------------------

        if self.provider_type == "Gemini":

            fallbacks = [
                "gemini-2.5-flash",
                "gemini-2.0-flash",
            ]

        elif self.provider_type == "OpenRouter":

            fallbacks = [
                "google/gemini-2.5-flash",
                "openai/gpt-4o-mini",
            ]

        elif self.provider_type == "OpenAI":

            fallbacks = [
                "gpt-4o-mini",
            ]

        else:

            fallbacks = []

        # ----------------------------------------------------
        # Try fallback
        # ----------------------------------------------------

        for model in fallbacks:

            if model == self.model_name:
                continue

            try:

                logger.info(
                    f"Fallback "
                    f"{self.provider_type}: "
                    f"{self.model_name} -> {model}"
                )

                engine = AIEngine(
                    provider_type=self.provider_type,
                    api_key=self.api_key,
                    model_name=model,
                    timeout=self.timeout,
                )

                return engine.generate_text(
                    prompt,
                    system_instruction,
                )

            except AuthenticationError:
                raise

            except QuotaExceededError:
                raise

            except (
                ModelNotFoundError,
                NetworkError,
                TimeoutError,
            ) as exc:

                logger.warning(
                    f"Fallback {model} thất bại: {exc}"
                )

        raise original_error

    # ========================================================
    # JSON
    # ========================================================

    def generate_json(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> AIResponse:

        instruction = (
            system_instruction
            + "\n\n"
            "BẮT BUỘC TRẢ VỀ JSON HỢP LỆ.\n"
            "KHÔNG dùng ```json.\n"
            "KHÔNG thêm giải thích.\n"
            "CHỈ TRẢ VỀ JSON."
        )

        return self.generate_text(
            prompt,
            instruction,
        )

    # ========================================================
    # MARKDOWN
    # ========================================================

    def generate_markdown(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> AIResponse:

        instruction = (
            system_instruction
            + "\n\n"
            "BẮT BUỘC TRẢ VỀ MARKDOWN CHUẨN."
        )

        return self.generate_text(
            prompt,
            instruction,
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
                f"{self.provider_type}: "
                "Chưa có API Key hợp lệ."
            )

        cache_key = hashlib.sha256(
            (
                f"{self.provider_type}|"
                f"{self.model_name}|"
                f"{system_instruction}|"
                f"{prompt}"
            ).encode("utf-8")
        ).hexdigest()

        if (
            not stream
            and cache_key in prompt_cache
        ):
            return prompt_cache[cache_key]

        start_time = time.time()

        try:

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

        except requests.exceptions.Timeout as exc:

            raise TimeoutError(
                "Timeout kết nối máy chủ AI."
            ) from exc

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
                f"{self.provider_type}: {exc}"
            ) from exc

    # ========================================================
    # GEMINI DIRECT
    # ========================================================

    def _call_gemini(
        self,
        prompt: str,
        system_instruction: str,
    ) -> AIResponse:

        try:

            if not self.api_key:
                raise AuthenticationError(
                    "Gemini: Chưa nhập API Key."
                )

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

            prompt_tokens = int(
                getattr(
                    usage,
                    "prompt_token_count",
                    0,
                )
                or 0
            )

            completion_tokens = int(
                getattr(
                    usage,
                    "candidates_token_count",
                    0,
                )
                or 0
            )

            text = getattr(
                response,
                "text",
                None,
            )

            if not text:
                raise NetworkError(
                    "Gemini trả về phản hồi rỗng."
                )

            return AIResponse(
                text=text,
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

        except AuthenticationError:
            raise

        except Exception as exc:

            self._raise_provider_error(
                "Gemini",
                exc,
            )

            raise

    # ========================================================
    # OPENAI DIRECT
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

            choice = response.choices[0]

            return AIResponse(
                text=choice.message.content or "",
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
                    choice.finish_reason
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

            input_tokens = int(
                getattr(
                    response.usage,
                    "input_tokens",
                    0,
                )
                or 0
            )

            output_tokens = int(
                getattr(
                    response.usage,
                    "output_tokens",
                    0,
                )
                or 0
            )

            text = ""

            if response.content:

                first = response.content[0]

                text = getattr(
                    first,
                    "text",
                    "",
                ) or ""

            return AIResponse(
                text=text,
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

            if not self.api_key:
                raise AuthenticationError(
                    "OpenRouter: Chưa nhập API Key."
                )

            # QUAN TRỌNG:
            # URL phải là chuỗi thuần.
            # KHÔNG dùng Markdown [URL](URL).

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
            choice = response.choices[0]

            return AIResponse(
                text=choice.message.content or "",
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
                    choice.finish_reason
                    or "stop"
                ),
            )

        except AuthenticationError:
            raise

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

            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout,
            )

            if response.status_code == 404:

                raise ModelNotFoundError(
                    f"Ollama: Model "
                    f"'{self.model_name}' "
                    "không tồn tại."
                )

            response.raise_for_status()

            data = response.json()

            text = data.get(
                "response",
                "",
            )

            if not text:

                raise NetworkError(
                    "Ollama trả về phản hồi rỗng."
                )

            prompt_tokens = int(
                data.get(
                    "prompt_eval_count",
                    0,
                )
                or 0
            )

            completion_tokens = int(
                data.get(
                    "eval_count",
                    0,
                )
                or 0
            )

            return AIResponse(
                text=text,
                provider="Ollama",
                model=self.model_name,
                latency=0.0,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=(
                    prompt_tokens
                    + completion_tokens
                ),
            )

        except ModelNotFoundError:
            raise

        except requests.exceptions.ConnectionError as exc:

            raise NetworkError(
                "Ollama không thể kết nối. "
                "Nếu đang chạy Streamlit Cloud, "
                "localhost là máy chủ Cloud, "
                "không phải máy tính cá nhân."
            ) from exc

        except requests.exceptions.Timeout as exc:

            raise TimeoutError(
                "Ollama kết nối quá thời gian."
            ) from exc

        except requests.exceptions.HTTPError as exc:

            raise NetworkError(
                f"Ollama HTTP "
                f"{response.status_code}: {exc}"
            ) from exc

        except Exception as exc:

            raise NetworkError(
                f"Ollama: {exc}"
            ) from exc

    # ========================================================
    # ERROR MAPPING
    # ========================================================

    @staticmethod
    def _raise_provider_error(
        provider: str,
        exc: Exception,
    ) -> None:

        text = str(exc or "")
        lower = text.lower()

        # ----------------------------------------------------
        # Authentication
        # ----------------------------------------------------

        authentication_patterns = (
            "invalid api key",
            "invalid_api_key",
            "api key is invalid",
            "incorrect api key",
            "unauthorized",
            "authentication",
            "authenticationerror",
            "401",
        )

        if any(
            pattern in lower
            for pattern in authentication_patterns
        ):

            raise AuthenticationError(
                f"{provider}: API Key không hợp lệ "
                "hoặc không có quyền truy cập."
            ) from exc

        # ----------------------------------------------------
        # Quota
        # ----------------------------------------------------

        quota_patterns = (
            "insufficient_quota",
            "insufficient balance",
            "quota",
            "rate limit",
            "rate_limit",
            "too many requests",
            "credits",
            "402",
            "429",
        )

        if any(
            pattern in lower
            for pattern in quota_patterns
        ):

            raise QuotaExceededError(
                f"{provider}: Hết quota/credits "
                "hoặc vượt giới hạn request."
            ) from exc

        # ----------------------------------------------------
        # Model
        # ----------------------------------------------------

        model_patterns = (
            "model not found",
            "model_not_found",
            "unknown model",
            "does not exist",
            "no such model",
        )

        if any(
            pattern in lower
            for pattern in model_patterns
        ):

            raise ModelNotFoundError(
                f"{provider}: Model không tồn tại "
                "hoặc không khả dụng."
            ) from exc

        # 404 chỉ được xem là model lỗi nếu thực sự
        # có dấu hiệu model trong thông báo.
        if (
            "404" in lower
            and "model" in lower
        ):

            raise ModelNotFoundError(
                f"{provider}: Model không tồn tại "
                "hoặc không khả dụng."
            ) from exc

        # ----------------------------------------------------
        # Timeout
        # ----------------------------------------------------

        timeout_patterns = (
            "timeout",
            "timed out",
            "time out",
            "deadline exceeded",
        )

        if any(
            pattern in lower
            for pattern in timeout_patterns
        ):

            raise TimeoutError(
                f"{provider}: Timeout kết nối."
            ) from exc

        # ----------------------------------------------------
        # Network / Server
        # ----------------------------------------------------

        network_patterns = (
            "connection",
            "connect",
            "network",
            "dns",
            "socket",
            "ssl",
            "502",
            "503",
            "504",
            "server error",
            "temporarily unavailable",
        )

        if any(
            pattern in lower
            for pattern in network_patterns
        ):

            raise NetworkError(
                f"{provider}: Lỗi mạng/server: "
                f"{text}"
            ) from exc

        # ----------------------------------------------------
        # Unknown
        # ----------------------------------------------------

        raise NetworkError(
            f"{provider}: {text}"
        ) from exc
