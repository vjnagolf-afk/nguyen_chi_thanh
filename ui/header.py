"""Xử lý hiển thị phần Header và CSS toàn cục của ứng dụng."""
import streamlit as st

def render_styles():
    """Nhúng CSS tùy chỉnh để làm đẹp các nút chức năng (Tông màu Pastel nhã nhặn)."""
    st.markdown("""
    <style>
    /* 1. Nút Primary (Màu Xanh lá Pastel - VD: Tiến Hành Xây Dựng, Tải File) */
    button[kind="primary"] {
        background-color: #e8f5e9 !important; /* Nền xanh lá nhạt */
        border: 1px solid #c8e6c9 !important;
        color: #2e7d32 !important; /* Chữ xanh lục đậm */
        font-weight: 600 !important;
        border-radius: 8px !important;
        transition: all 0.2s ease-in-out;
    }
    button[kind="primary"]:hover {
        background-color: #c8e6c9 !important;
        transform: translateY(-2px);
    }
    
    /* 2. Nút Secondary mặc định (Màu Hồng nhạt Pastel - VD: Xóa kết quả) */
    button[kind="secondary"] {
        background-color: #ffebee !important; /* Nền hồng nhạt */
        border: 1px solid #ffcdd2 !important;
        color: #c62828 !important; /* Chữ đỏ thẫm */
        font-weight: 600 !important;
        border-radius: 8px !important;
        transition: all 0.2s ease-in-out;
    }
    button[kind="secondary"]:hover {
        background-color: #ffcdd2 !important;
        transform: translateY(-2px);
    }
    
    /* 3. Tinh chỉnh riêng nút ở Sidebar (Màu Tím Pastel - VD: Lưu cấu hình) */
    [data-testid="stSidebar"] button {
        background-color: #f3e5f5 !important; /* Nền tím nhạt */
        border: 1px solid #e1bee7 !important;
        color: #6a1b9a !important; /* Chữ tím đậm */
        border-radius: 8px !important;
    }
    [data-testid="stSidebar"] button:hover {
        background-color: #e1bee7 !important;
        transform: translateY(-2px);
    }
    </style>
    """, unsafe_allow_html=True)

def render_header() -> None:
    """Hiển thị thông tin tiêu đề và trường lớp trên cùng."""
    render_styles() # Kích hoạt CSS
    
    st.title("🎓 Nền Tảng Trợ Lý Trí Tuệ Nhân Tạo Cho Giáo Viên")
    teacher = st.session_state.get("teacher_name", "")
    school = st.session_state.get("school_name", "")
    st.markdown(f"**Giáo viên:** {teacher} | **Đơn vị:** {school}")
    st.divider()
