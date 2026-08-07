import json
import requests

class AIEngine:
    def __init__(self, provider_type="Gemini (Free)", api_key="", model_name="gemini-1.5-flash"):
        self.provider_type = provider_type
        self.api_key = api_key
        self.model_name = model_name

    def generate(self, prompt: str, system_instruction: str = "") -> str:
        """Hàm gửi yêu cầu tới Provider được chọn và trả về văn bản"""
        if not self.api_key and self.provider_type != "Ollama (Offline)":
            raise ValueError("Chưa cấu hình API Key! Vui lòng nhập Key ở mục Cấu hình AI.")

        if "Gemini" in self.provider_type:
            return self._call_gemini(prompt, system_instruction)
        elif "OpenRouter" in self.provider_type:
            return self._call_openrouter(prompt, system_instruction)
        elif "Ollama" in self.provider_type:
            return self._call_ollama(prompt, system_instruction)
        else:
            raise ValueError(f"Provider {self.provider_type} chưa được hỗ trợ.")

    def _call_gemini(self, prompt, system_instruction):
        # Gọi Gemini REST API trực tiếp để tránh phụ thuộc thư viện nặng
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            res_data = response.json()
            try:
                return res_data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                return "Lỗi: Không phản hồi đúng cấu trúc từ Gemini."
        else:
            raise Exception(f"Lỗi Gemini API ({response.status_code}): {response.text}")

    def _call_openrouter(self, prompt, system_instruction):
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages
        }
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            raise Exception(f"Lỗi OpenRouter API ({response.status_code}): {response.text}")

    def _call_ollama(self, prompt, system_instruction):
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": self.model_name or "llama3",
            "prompt": f"{system_instruction}\n\n{prompt}",
            "stream": False
        }
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json()["response"]
        else:
            raise Exception("Không thể kết nối tới Ollama Local.")
