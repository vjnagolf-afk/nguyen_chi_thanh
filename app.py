import streamlit as st
import os
from ai_engine.provider import AIEngine

# Thiết lập UI toàn cục
st.set_page_config(
    page_title="Hệ Thống Trợ Lý Giáo Viên AI", 
    page_icon="🎓", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Tải biến môi trường an toàn
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def get_api_key(key_name):
    if key_name in st.secrets:
        return st.secrets[key_name]
    return os.getenv(key_name, "")

def initialize_session_state():
    if "teacher_name" not in st.session_state:
        st.session_state["teacher_name"] = "Lê Hồng Dưỡng"
    if "school_name" not in st.session_state:
        st.session_state["school_name"] = "Trường THCS Nguyễn Chí Thanh"
    if "ai_engine" not in st.session_state:
        st.session_state["ai_engine"] = None

def render_sidebar():
    st.sidebar.header("⚙️ Cấu hình Hệ Thống AI")
    
    provider = st.sidebar.selectbox(
        "Nguồn cung cấp AI:",
        ["Gemini (Free - Khuyên dùng)", "OpenRouter (Free Models)", "Ollama (Offline)"]
    )

    api_key = ""
    model_name = "gemini-1.5-flash"

    if "Gemini" in provider:
        api_key = st.sidebar.text_input("Google AI Studio Key:", value=get_api_key("GEMINI_API_KEY"), type="password")
        model_name = st.sidebar.selectbox("Phiên bản Model:", ["gemini-1.5-flash", "gemini-1.5-pro"])
    elif "OpenRouter" in provider:
        api_key = st.sidebar.text_input("OpenRouter API Key:", value=get_api_key("OPENROUTER_API_KEY"), type="password")
        model_name = st.sidebar.text_input("Mã Model OpenRouter:", value="google/gemini-1.5-flash")
    elif "Ollama" in provider:
        model_name = st.sidebar.text_input("Tên Model Local:", value="llama3")

    if st.sidebar.button("💾 Lưu Cấu Hình AI", use_container_width=True):
        st.session_state["ai_engine"] = AIEngine(provider_type=provider, api_key=api_key, model_name=model_name)
        st.sidebar.success("Đã lưu cấu hình AI!")

    st.sidebar.divider()
    
    st.sidebar.header("📁 Chức năng chính")
    menu = st.sidebar.radio(
        "Lựa chọn module làm việc:", 
        ["Trang chủ (Kiểm tra AI)", "Xây dựng Đề kiểm tra", "Soạn Giáo án (KHBD)"]
    )
    return menu

def render_home():
    st.title("🎓 Nền Tảng Trợ Lý Trí Tuệ Nhân Tạo Cho Giáo Viên")
    st.markdown("Chào mừng thầy/cô đến với hệ thống tự động hóa xây dựng tài liệu giảng dạy chuẩn CT GDPT 2018.")
    
    st.subheader("🧪 Kiểm tra luồng dữ liệu AI")
    test_prompt = st.text_area("Nhập câu lệnh để kiểm tra phản hồi từ AI:", "Hãy viết một đoạn giới thiệu ngắn về ý nghĩa của việc ứng dụng AI trong giảng dạy.")
    
    if st.button("Gửi kiểm tra hệ thống", type="primary"):
        engine = st.session_state.get("ai_engine")
        if not engine or not engine.is_ready():
            st.error("⚠️ Vui lòng cấu hình và lưu API Key ở thanh bên trái trước khi sử dụng.")
            return
            
        with st.spinner("Đang kết nối tới máy chủ AI..."):
            try:
                response = engine.generate(test_prompt)
                st.success("✅ Kết nối ổn định! Phản hồi từ hệ thống:")
                st.write(response)
            except Exception as e:
                st.error(f"❌ Lỗi xử lý: {str(e)}")

def main():
    initialize_session_state()
    menu = render_sidebar()
    
    if menu == "Trang chủ (Kiểm tra AI)":
        render_home()
    elif menu == "Xây dựng Đề kiểm tra":
        try:
            from modules import xd_de_kt
            xd_de_kt.render_ui()
        except ImportError:
            st.warning("Module 'Xây dựng Đề kiểm tra' đang được cập nhật.")
    elif menu == "Soạn Giáo án (KHBD)":
        try:
            from modules import xd_khbd
            xd_khbd.render_ui()
        except ImportError:
            st.warning("Module 'Soạn Giáo án' đang được cập nhật.")

if __name__ == "__main__":
    main()
