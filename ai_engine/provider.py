import json
import requests

class AIEngine:
    def __init__(self, provider_type="Gemini (Free)", api_key="", model_name="gemini-1.5-flash"):
        self.provider_type = provider_type
        self.api_key = api_key.strip()
        self.model_name = model_name
        self._is_ready = False

        if self.api_key or self.provider_type == "Ollama (Offline)":
            self._is_ready = True

    def is_ready(self) -> bool:
        return self._is_ready

    def generate(self, prompt: str, system_instruction: str = "") -> str:
        if not self._is_ready:
            raise ValueError("Hệ thống AI chưa sẵn sàng. Vui lòng kiểm tra API Key.")

        if "Gemini" in self.provider_type:
            return self._call_gemini_raw(prompt, system_instruction)
        elif "OpenRouter" in self.provider_type:
            return self._call_openrouter(prompt, system_instruction)
        elif "Ollama" in self.provider_type:
            return self._call_ollama(prompt, system_instruction)
        else:
            raise ValueError(f"Provider {self.provider_type} chưa được hỗ trợ.")

    def _call_gemini_raw(self, prompt: str, system_instruction: str) -> str:
        # Chuyển sang dùng REST API thô để kiểm soát Header
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
        headers = {"Content-Type": "application/json"}

        # Cơ chế xác thực thông minh (Smart Auth Routing)
        if self.api_key.startswith("AIza"):
            url += f"?key={self.api_key}"
        else:
            # Xử lý các token dạng OAuth (như AQ.Ab...)
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2, # Hạ nhiệt độ xuống 0.2 để AI bám sát dữ liệu thực tế, bớt "sáng tạo" đi
                "top_p": 0.95,
                "maxOutputTokens": 8192
            }
        }
        
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=90)
            
            if response.status_code != 200:
                err_msg = response.json().get("error", {}).get("message", response.text)
                raise Exception(f"Lỗi Gemini ({response.status_code}): {err_msg}")
                
            res_data = response.json()
            return res_data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            raise Exception(f"Lỗi kết nối Gemini: {str(e)}")

    def _call_openrouter(self, prompt: str, system_instruction: str) -> str:
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
            "messages": messages,
            "temperature": 0.2 # Tối ưu hóa tính chính xác
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=90)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise Exception(f"Lỗi kết nối OpenRouter: {str(e)}")

    def _call_ollama(self, prompt: str, system_instruction: str) -> str:
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": self.model_name or "llama3",
            "prompt": f"{system_instruction}\n\n{prompt}",
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            raise Exception(f"Lỗi kết nối Ollama (Local): {str(e)}")
