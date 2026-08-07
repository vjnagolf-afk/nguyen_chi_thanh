"""Quản lý trạng thái phiên làm việc (Session State) tập trung."""

import json
import streamlit as st
from loguru import logger

def initialize_session_state() -> None:
    """Khởi tạo toàn bộ các biến trạng thái cần thiết cho hệ thống."""
    # Khởi tạo thông tin mặc định từ file cấu hình
    if "teacher_name" not in st.session_state or "school_name" not in st.session_state:
        try:
            with open("config/app_config.json", "r", encoding="utf-8") as f:
                config_data = json.load(f)
                st.session_state["teacher_name"] = config_data.get("teacher_name", "Giáo viên")
                st.session_state["school_name"] = config_data.get("school_name", "Trường học")
        except Exception as e:
            logger.warning(f"Không thể đọc app_config.json: {e}")
            st.session_state["teacher_name"] = "Giáo viên"
            st.session_state["school_name"] = "Trường học"

    # Khởi tạo các biến hệ thống AI
    if "ai_engine" not in st.session_state:
        st.session_state["ai_engine"] = None
    if "ai_status" not in st.session_state:
        st.session_state["ai_status"] = {"connected": False, "latency": 0.0}
    
    # Khởi tạo lịch sử và điều hướng
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    if "current_module" not in st.session_state:
        st.session_state["current_module"] = "Trang chủ (Kiểm tra AI)"
