import io
import PyPDF2
from docx import Document
from PIL import Image

def extract_text_from_file(uploaded_file) -> str:
    """
    Hàm đa năng: Đọc file được upload từ Streamlit và chuyển thành văn bản thuần.
    Hỗ trợ: TXT, MD, DOCX, PDF (text-based).
    """
    if uploaded_file is None:
        return ""

    file_name = uploaded_file.name.lower()
    extracted_text = ""

    try:
        # 1. Xử lý file Text thuần
        if file_name.endswith(('.txt', '.md', '.csv')):
            extracted_text = uploaded_file.getvalue().decode("utf-8", errors="ignore")
            
        # 2. Xử lý file Word
        elif file_name.endswith('.docx'):
            doc = Document(io.BytesIO(uploaded_file.getvalue()))
            extracted_text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            
        # 3. Xử lý file PDF (Dạng text)
        elif file_name.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.getvalue()))
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"
            
            if not extracted_text.strip():
                return "[HỆ THỐNG] File PDF này có vẻ là bản Scan (dạng ảnh). Vui lòng sử dụng tính năng tải Ảnh hoặc chuyển đổi PDF sang Word trước khi tải lên, hoặc sử dụng AI Gemini để nhận diện hình ảnh trực tiếp."

        # 4. Xử lý Hình ảnh
        elif file_name.endswith(('.png', '.jpg', '.jpeg')):
            return "[HỆ THỐNG_IMAGE_DETECTED]"

        else:
            return f"[HỆ THỐNG] Định dạng file {file_name} chưa được hỗ trợ trích xuất văn bản."

        return extracted_text.strip()

    except Exception as e:
        return f"[LỖI TRÍCH XUẤT TÀI LIỆU]: {str(e)}"
