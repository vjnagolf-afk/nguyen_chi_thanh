import streamlit as st
import os
from dotenv import load_dotenv
from ai_engine.provider import AIEngine

# Tải các biến môi trường từ file .env
load_dotenv()

st.set_page_config(page_title="Hệ Thống Trợ Lý Giáo Viên AI", layout="wide")
st.title("🎓 Trợ Lý AI: Sinh Đề Kiểm Tra & Soạn Giáo Án")

# --- SIDEBAR: CẤU HÌNH AI ---
st.sidebar.header("⚙️ Cấu hình AI Engine")
provider = st.sidebar.selectbox(
    "Chọn nguồn AI:",
    ["Gemini (Free - Khuyên dùng)", "OpenRouter (Free Models)", "Ollama (Offline)"]
)

# Tự động lấy Key từ hệ thống nếu có
default_gemini_key = os.getenv("GEMINI_API_KEY", "")
default_openrouter_key = os.getenv("OPENROUTER_API_KEY", "")

api_key = ""
model_name = "gemini-1.5-flash"

if "Gemini" in provider:
    api_key = st.sidebar.text_input("Nhập Google AI Studio Key:", value=default_gemini_key, type="password")
    model_name = st.sidebar.selectbox("Chọn Model:", ["gemini-1.5-flash", "gemini-1.5-pro"])
elif "OpenRouter" in provider:
    api_key = st.sidebar.text_input("Nhập OpenRouter API Key:", value=default_openrouter_key, type="password")
    model_name = st.sidebar.text_input("Tên Model OpenRouter:", value="google/gemini-flash-1.5")
elif "Ollama" in provider:
    model_name = st.sidebar.text_input("Tên Model Local:", value="llama3")

# Lưu vào session
st.session_state["ai_engine"] = AIEngine(provider_type=provider, api_key=api_key, model_name=model_name)

# ... (Giữ nguyên phần TRANG CHÍNH: TEST KẾT NỐI như cũ)
