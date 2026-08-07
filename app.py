import streamlit as st
from ai_engine.provider import AIEngine

st.set_page_config(page_title="Hệ Thống Trợ Lý Giáo Viên AI", layout="wide")

st.title("🎓 Trợ Lý AI: Sinh Đề Kiểm Tra & Soạn Giáo Án")

# --- SIDEBAR: CẤU HÌNH AI ---
st.sidebar.header("⚙️ Cấu hình AI Engine")
provider = st.sidebar.selectbox(
    "Chọn nguồn AI:",
    ["Gemini (Free - Khuyên dùng)", "OpenRouter (Free Models)", "Ollama (Offline)"]
)

api_key = ""
model_name = "gemini-1.5-flash"

if "Gemini" in provider:
    api_key = st.sidebar.text_input("Nhập Google AI Studio Key:", type="password", help="Lấy key miễn phí tại aistudio.google.com")
    model_name = st.sidebar.selectbox("Chọn Model:", ["gemini-1.5-flash", "gemini-1.5-pro"])
elif "OpenRouter" in provider:
    api_key = st.sidebar.text_input("Nhập OpenRouter API Key:", type="password")
    model_name = st.sidebar.text_input("Tên Model OpenRouter:", value="google/gemini-flash-1.5")
elif "Ollama" in provider:
    model_name = st.sidebar.text_input("Tên Model Local:", value="llama3")

# Lưu vào session
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
