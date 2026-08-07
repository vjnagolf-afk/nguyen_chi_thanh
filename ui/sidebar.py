"""Xử lý toàn bộ logic và hiển thị của thanh điều hướng (Sidebar)."""

import os
import streamlit as st
from loguru import logger

from config.menu import MENU_ITEMS
from config.providers import SUPPORTED_PROVIDERS
from config.models import PROVIDER_MODELS
from ai_engine.provider import (
    AIEngine, AuthenticationError, NetworkError, TimeoutError, 
    QuotaExceededError, ModelNotFoundError
)

def get_api_key(key_name: str) -> str:
    """Lấy API Key từ Secrets hoặc Environment."""
    if key_name in st.secrets:
        return st.secrets[key_name]
    return os.getenv(key_name, "")

@st.cache_resource(show_spinner=False)
def initialize_and_test_engine(provider: str, api_key: str, model: str) -> AIEngine:
    """
    Khởi tạo và chạy test_connection. 
    Được Cache để tránh khởi tạo lại nếu các tham số không đổi.
    """
    engine = AIEngine(provider_type=provider, api_key=api_key, model_name=model)
    engine.test_connection()
    return engine

def render_sidebar() -> str:
    """
    Hiển thị Sidebar cấu hình AI và menu điều hướng.
    
    Returns:
        str: Tên module được người dùng chọn từ Menu.
    """
    st.sidebar.header("⚙️ Cấu hình AI Đa Mô Hình")
    
    # 1. Khu vực Cấu hình
    provider = st.sidebar.selectbox("Nguồn cung cấp AI:", SUPPORTED_PROVIDERS)
    
    api_key = ""
    default_model = PROVIDER_MODELS.get(provider, "llama3")

    if "OpenRouter" in provider:
        api_key = st.sidebar.text_input("OpenRouter API Key:", value=get_api_key("OPENROUTER_API_KEY"), type="password")
    elif "Gemini" in provider:
        api_key = st.sidebar.text_input("Google / Gemini Key:", value=get_api_key("GEMINI_API_KEY"), type="password")
    elif "OpenAI" in provider:
        api_key = st.sidebar.text_input("OpenAI API Key:", value=get_api_key("OPENAI_API_KEY"), type="password")
    elif "Anthropic" in provider:
        api_key = st.sidebar.text_input("Claude API Key:", value=get_api_key("ANTHROPIC_API_KEY"), type="password")

    model_name = st.sidebar.text_input("Mã Model:", value=default_model)

    # 2. Xử lý nút Kết nối
    if st.sidebar.button("💾 Lưu Cấu Hình AI", use_container_width=True):
        if not api_key and "Ollama" not in provider:
            st.sidebar.error("⚠️ Vui lòng nhập API Key!")
        else:
            with st.spinner("Đang kiểm tra kết nối AI..."):
                try:
                    # Kiểm tra kết nối trước khi lưu (Yêu cầu 10)
                    engine = initialize_and_test_engine(provider, api_key, model_name)
                    st.session_state["ai_engine"] = engine
                    st.session_state["ai_status"] = {"connected": True, "provider": provider, "model": model_name}
                    st.sidebar.success("✅ Đã kết nối thành công!")
                    logger.info(f"Kết nối AI thành công: {provider} - {model_name}")
                except AuthenticationError as e:
                    st.sidebar.error(f"❌ Sai khóa bảo mật: {e}")
                except NetworkError as e:
                    st.sidebar.error(f"❌ Lỗi mạng: {e}")
                except TimeoutError as e:
                    st.sidebar.error(f"⏳ Hết thời gian chờ: {e}")
                except QuotaExceededError as e:
                    st.sidebar.error(f"💳 Hết dung lượng (Quota): {e}")
                except ModelNotFoundError as e:
                    st.sidebar.error(f"🔍 Sai tên Model: {e}")
                except Exception as e:
                    st.sidebar.error(f"❌ Lỗi hệ thống: {e}")

    st.sidebar.divider()
    
    # 3. Hiển thị Trạng thái AI (Yêu cầu 13)
    st.sidebar.subheader("📡 Trạng thái AI")
    status = st.session_state.get("ai_status", {})
    if status.get("connected"):
        st.sidebar.success("✅ Đang hoạt động")
        st.sidebar.caption(f"**Provider:** {status.get('provider')}")
        st.sidebar.caption(f"**Model:** {status.get('model')}")
    else:
        st.sidebar.error("🔴 Chưa kết nối AI")

    st.sidebar.divider()
    
    # 4. Khu vực Điều hướng
    st.sidebar.header("📁 Chức năng chính")
    menu = st.sidebar.radio("Lựa chọn module làm việc:", MENU_ITEMS)
    
    return menu
