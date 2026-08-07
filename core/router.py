"""Điều hướng module linh hoạt bằng Dynamic Import."""

import importlib
import streamlit as st
from loguru import logger
from ui import home

# Bản đồ định tuyến (Routing Map)
ROUTES = {
    "Trang chủ (Kiểm tra AI)": {
        "type": "static", 
        "handler": home.render_home
    },
    "Xây dựng Đề kiểm tra": {
        "type": "dynamic", 
        "module": "modules.xd_de_kt", 
        "func": "render_ui"
    },
    "Soạn Giáo án (KHBD)": {
        "type": "dynamic", 
        "module": "modules.xd_khbd", 
        "func": "render_ui"
    }
}

def route(menu_choice: str) -> None:
    """
    Xử lý điều hướng hiển thị giao diện tùy theo lựa chọn menu.
    
    Args:
        menu_choice (str): Tên chức năng người dùng chọn.
    """
    logger.info(f"Điều hướng tới module: {menu_choice}")
    st.session_state["current_module"] = menu_choice
    
    route_config = ROUTES.get(menu_choice)
    
    if not route_config:
        st.error(f"Đường dẫn '{menu_choice}' không tồn tại.")
        return

    if route_config["type"] == "static":
        route_config["handler"]()
    elif route_config["type"] == "dynamic":
        try:
            # Sử dụng importlib để load module động (Dynamic Import)
            module = importlib.import_module(route_config["module"])
            func = getattr(module, route_config["func"])
            func()
        except ImportError as e:
            logger.error(f"Lỗi nạp module {route_config['module']}: {e}")
            st.warning(f"Tính năng '{menu_choice}' đang được cập nhật.")
        except Exception as e:
            logger.error(f"Lỗi thực thi {route_config['module']}: {e}")
            st.error(f"Xảy ra lỗi khi mở module: {e}")
