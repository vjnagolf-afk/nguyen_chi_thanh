"""Xử lý hiển thị phần Footer của ứng dụng."""
import streamlit as st

def render_footer() -> None:
    """Hiển thị chân trang ứng dụng."""
    st.markdown("---")
    st.caption("© 2026 Edu-AI Ecosystem - Được thiết kế tối ưu hóa cho CT GDPT 2018.")
