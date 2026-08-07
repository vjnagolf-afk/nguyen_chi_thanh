"""Xử lý hiển thị phần Header của ứng dụng."""
import streamlit as st

def render_header() -> None:
    """Hiển thị thông tin tiêu đề và trường lớp trên cùng."""
    st.title("🎓 Nền Tảng Trợ Lý Trí Tuệ Nhân Tạo Cho Giáo Viên")
    teacher = st.session_state.get("teacher_name", "")
    school = st.session_state.get("school_name", "")
    st.markdown(f"**Giáo viên:** {teacher} | **Đơn vị:** {school}")
    st.divider()
