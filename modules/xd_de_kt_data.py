import streamlit as st
import json
from utils.document_reader import extract_text_from_file

def build_system_prompt(config: dict, mode: str, text_context: str) -> str:
    """Xây dựng Prompt chi tiết dựa vào Mode và Cấu hình"""
    
    # Base Context - Các chỉ thị Tối cao
    prompt = f"""
[CHỈ THỊ TỐI CAO]
Bạn là Cỗ máy Sinh Đề Thi tự động. Bạn PHẢI tuân thủ 100% các yêu cầu dưới đây, không được sai lệch dù chỉ 1 câu hay 0.25 điểm.

1. THÔNG TIN CHUNG:
- Môn học: {config['mon_hoc']} | Khối: Lớp {config['lop']}
- Loại đề: {config['loai_de']}
- Thời lượng: BẮT BUỘC thiết kế nội dung đủ làm trong {config['thoi_gian']}.
- Chủ đề: {config.get('chu_de', 'Tổng hợp')}

2. QUY ĐỊNH KỸ THUẬT NGHIÊM NGẶT:
- BẮT BUỘC sử dụng LaTeX (bọc trong $$ hoặc $) cho TẤT CẢ công thức Toán, Lý, Hóa (VD: $x^2 + y^2 = z^2$).
- Không dùng HTML, không lồng bảng.
"""
    
    # Siết chặt Dữ liệu đầu vào
    if text_context:
        prompt += f"""
3. TÀI LIỆU NỀN TẢNG (QUAN TRỌNG NHẤT):
- BẠN BỊ CẤM sử dụng kiến thức bên ngoài. CHỈ ĐƯỢC PHÉP sử dụng thông tin từ tài liệu đính kèm dưới đây để đặt câu hỏi.
- NGUỒN TÀI LIỆU:\n{text_context[:10000]}...\n
"""
    else:
        prompt += "\n3. TÀI LIỆU NỀN TẢNG: Bám sát chuẩn kiến thức kỹ năng CT GDPT 2018.\n"

    # Xử lý riêng cho Tab Chỉ Sinh Ma Trận
    if mode == "chi_ma_tran":
        prompt += """
[NHIỆM VỤ ĐẶC BIỆT]
Dựa vào nội dung Đề kiểm tra trong "TÀI LIỆU NỀN TẢNG", hãy XÂY DỰNG NGƯỢC LẠI:
# I. MA TRẬN ĐỀ KIỂM TRA (Trình bày dưới dạng Bảng Markdown)
# II. BẢN ĐẶC TẢ ĐỀ KIỂM TRA (Trình bày dưới dạng Bảng Markdown)
Tuyệt đối KHÔNG sinh lại đề, KHÔNG sinh đáp án. CHỈ trả về 2 bảng trên.
"""
        return prompt

    # Chi tiết điểm số cho Tab 1, 2, 3
    tn = config['tn']
    tl = config['tl']
    md = config['muc_do']
    
    prompt += f"""
4. CẤU TRÚC ĐIỂM SỐ (BẮT BUỘC KHỚP 100%):
- TỶ LỆ MỨC ĐỘ: Nhận biết ({md['nb']}%) - Thông hiểu ({md['th']}%) - Vận dụng ({md['vd']}%) - Vận dụng cao ({md['vdc']}%).
- TRẮC NGHIỆM ({tn['total']} điểm - Yêu cầu sinh chính xác số lượng câu):
   + Nhiều lựa chọn (4 đáp án A,B,C,D): PHẢI CÓ ĐÚNG {tn['n_nlc']} câu (Mỗi câu {tn['p_nlc']} điểm)
   + Đúng/Sai (Mỗi câu có 4 ý a,b,c,d): PHẢI CÓ ĐÚNG {tn['n_ds']} câu (Mỗi câu {tn['p_ds']} điểm)
   + Điền khuyết: PHẢI CÓ ĐÚNG {tn['n_dk']} câu (Mỗi câu {tn['p_dk']} điểm)
   + Trả lời ngắn: PHẢI CÓ ĐÚNG {tn['n_ngan']} câu (Mỗi câu {tn['p_ngan']} điểm)
- TỰ LUẬN ({tl['total']} điểm): PHẢI CÓ ĐÚNG {tl['so_cau']} câu, bao gồm:
"""
    for i, p in enumerate(tl['diem_chi_tiet']):
        prompt += f"   + Câu {i+1}: Trị giá đúng {p} điểm\n"

    # Định dạng Đầu ra
    if mode in ["cv7991", "tuy_chon_co_ma_tran"]:
        prompt += """
5. CẤU TRÚC TRẢ VỀ (MARKDOWN):
HÃY TRẢ VỀ ĐÚNG TRÌNH TỰ SAU, ĐÁNH DẤU CHÍNH XÁC CÁC TIÊU ĐỀ:
# I. MA TRẬN ĐỀ KIỂM TRA (Bảng Markdown chuẩn CV7991)
# II. BẢN ĐẶC TẢ (Bảng Markdown chuẩn CV7991)
# III. ĐỀ KIỂM TRA (Đánh số câu liên tục hoặc chia phần rõ ràng)
# IV. ĐÁP ÁN (Liệt kê rõ ràng)
# V. HƯỚNG DẪN CHẤM (Chi tiết barem điểm đến 0.25 cho từng ý tự luận)
"""
    elif mode == "tuy_chon_khong_ma_tran":
        prompt += """
5. CẤU TRÚC TRẢ VỀ (MARKDOWN):
BỎ QUA MA TRẬN VÀ BẢN ĐẶC TẢ. HÃY TRẢ VỀ ĐÚNG TRÌNH TỰ SAU:
# I. ĐỀ KIỂM TRA (Đánh số câu liên tục hoặc chia phần rõ ràng)
# II. ĐÁP ÁN (Liệt kê rõ ràng)
# III. HƯỚNG DẪN CHẤM (Chi tiết barem điểm đến 0.25 cho từng ý tự luận)
"""
    return prompt

def process_request(config: dict, mode: str, uploaded_file):
    """Hàm trung tâm xử lý Logic sau khi người dùng bấm nút"""
    
    text_context = ""
    if uploaded_file is not None:
        with st.spinner("Đang đọc và phân tích tài liệu đính kèm..."):
            text_context = extract_text_from_file(uploaded_file)
            if "[LỖI" in text_context:
                st.error(text_context)
                return
            st.success(f"Đã đọc thành công tài liệu: {uploaded_file.name}")
    
    system_prompt = build_system_prompt(config, mode, text_context)
    
    engine = st.session_state.get("ai_engine")
    if not engine or not engine.is_ready():
        st.error("⚠️ Lỗi Xác Thực AI: Vui lòng vào thanh cấu hình bên trái để cập nhật API Key hợp lệ.")
        return

    with st.spinner("Hệ thống AI đang tổng hợp kiến thức và xây dựng đề kiểm tra. Vui lòng đợi trong giây lát..."):
        try:
            # Gửi Prompt với System Instruction đóng vai trò như một lệnh tối cao
            response = engine.generate(
                prompt=system_prompt, 
                system_instruction="Bạn là Trợ lý AI tuân thủ mệnh lệnh tuyệt đối. Các thông số về số lượng, điểm số và tài liệu đính kèm là bắt buộc và không thể thương lượng."
            )
            
            st.success("✅ Nhiệm vụ hoàn tất! Đề kiểm tra đã được xây dựng thành công.")
            st.session_state["latest_exam_md"] = response
            
            with st.expander("👀 XEM TRƯỚC KẾT QUẢ (DẠNG VĂN BẢN MARKDOWN)", expanded=True):
                st.markdown(response)
                
        except Exception as e:
            st.error(f"❌ Tiến trình bị gián đoạn: {str(e)}")
            st.info("💡 MẸO TEST: Nếu mã Google Key (AQ...) của bạn vẫn bị từ chối, hãy thử chuyển sang nguồn 'OpenRouter' và dùng khóa 'sk-or-v1...' của bạn để kiểm tra luồng tạo đề!")
