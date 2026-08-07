"""Xử lý hiển thị giao diện Trang chủ."""
import streamlit as st
from loguru import logger

def render_home() -> None:
    """Vẽ giao diện Trang chủ và hộp thoại kiểm tra AI cơ bản."""
    st.subheader("🧪 Kiểm tra luồng dữ liệu AI")
    st.markdown("Kiểm tra tốc độ và độ phản hồi của bộ máy AI trước khi xây dựng tài liệu.")
    
    test_prompt = st.text_area("Nhập câu lệnh:", "Hãy viết một đoạn giới thiệu ngắn về giáo dục STEM.")
    
    if st.button("Gửi kiểm tra hệ thống", type="primary"):
        engine = st.session_state.get("ai_engine")
        if not engine or not engine.is_ready():
            st.error("⚠️ Vui lòng cấu hình và kết nối AI ở thanh Sidebar trước khi sử dụng.")
            return
            
        with st.spinner("Đang kết nối tới máy chủ AI..."):
            try:
                # Gọi thẳng hàm AI, các cơ chế bảo vệ đã được lo ở provider.py
                response = engine.generate_text(test_prompt)
                st.success(f"✅ Phản hồi từ hệ thống (Độ trễ: {response.latency:.2f}s | {response.total_tokens} tokens)")
                st.write(response.text)
                logger.info("Test AI tại Trang chủ thành công.")
            except Exception as e:
                logger.error(f"Lỗi kiểm tra AI: {e}")
                st.error(f"❌ Tiến trình bị gián đoạn: {str(e)}")
