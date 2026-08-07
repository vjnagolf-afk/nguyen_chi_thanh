import streamlit as st
import os
from ai_engine.provider import AIEngine

# Thiết lập trang phải luôn ở dòng gọi st đầu tiên
st.set_page_config(page_title="Hệ Thống Trợ Lý Giáo Viên AI", layout="wide")

# 1. Cố gắng tải file .env nếu đang chạy trên máy cá nhân (Local)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass # Bỏ qua lỗi này nếu đang chạy trên Streamlit Cloud

# 2. Hàm lấy API Key thông minh (Hỗ trợ cả Local và Cloud)
def get_api_key(key_name):
    # Ưu tiên lấy từ Streamlit Secrets (trên Cloud)
    if key_name in st.secrets:
        return st.secrets[key_name]
    # Nếu không có, lấy từ biến môi trường (Local)
    return os.getenv(key_name, "")

st.title("🎓 Trợ Lý AI: Sinh Đề Kiểm Tra & Soạn Giáo Án")

# --- SIDEBAR: CẤU HÌNH AI ---
st.sidebar.header("⚙️ Cấu hình AI Engine")
provider = st.sidebar.selectbox(
    "Chọn nguồn AI:",
    ["Gemini (Free - Khuyên dùng)", "OpenRouter (Free Models)", "Ollama (Offline)"]
)

# Tự động lấy Key từ hệ thống
default_gemini_key = get_api_key("GEMINI_API_KEY")
default_openrouter_key = get_api_key("OPENROUTER_API_KEY")

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

# Lưu cấu hình vào session
st.session_state["ai_engine"] = AIEngine(provider_type=provider, api_key=api_key, model_name=model_name)

# --- TRANG CHÍNH: TEST KẾT NỐI ---
st.subheader("🧪 Kiểm tra kết nối AI")
test_prompt = st.text_area("Thử nhập câu hỏi cho AI:", "Hãy viết 1 câu chào thân thiện gửi đến các thầy cô giáo bằng tiếng Việt.")

if st.button("Gửi thử nghiệm", type="primary"):
    if not api_key and "Ollama" not in provider:
        st.warning("⚠️ Vui lòng nhập API Key ở thanh bên trái trước!")
    else:
        with st.spinner("Đang kết nối tới AI..."):
            try:
                engine = st.session_state["ai_engine"]
                response = engine.generate(test_prompt)
                st.success("Kết nối thành công! Phản hồi từ AI:")
                st.write(response)
            except Exception as e:
                st.error(f"Lỗi kết nối: {str(e)}")
