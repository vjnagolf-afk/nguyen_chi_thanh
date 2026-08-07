"""
============================================================
AI ASSISTANT FOR TEACHERS - MAIN APPLICATION ENTRY POINT
Kiến trúc Micro-architecture phân tách module hoàn toàn.
============================================================
"""

# 1. Standard Library
import os

# 2. Third-party Libraries
import streamlit as st
from loguru import logger
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 3. Local Modules
from config.settings import APP_CONFIG
from core.session import initialize_session_state
from core.router import route
from ui.sidebar import render_sidebar
from ui.header import render_header
from ui.footer import render_footer

def main() -> None:
    """Hàm trung tâm (Main): Khởi tạo giao diện, tải phiên và điều hướng ứng dụng."""
    # 1. Cấu hình Streamlit (Phải gọi đầu tiên)
    st.set_page_config(**APP_CONFIG)
    
    # Khởi tạo Logging
    logger.add("logs/app.log", rotation="1 MB", retention="7 days", level="INFO")
    logger.info("=== Ứng dụng khởi động ===")

    # 2. Khởi tạo Session State
    initialize_session_state()

    # 3. Render Thanh bên (Sidebar) & Lấy lựa chọn menu
    menu_choice = render_sidebar()

    # 4. Render Tiêu đề chung
    render_header()

    # 5. Gọi Router để điều hướng tới Module tương ứng
    route(menu_choice)
    
    # 6. Render Chân trang
    render_footer()

if __name__ == "__main__":
    main()
