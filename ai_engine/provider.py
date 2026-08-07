import json
import requests
import google.generativeai as genai

class AIEngine:
    def __init__(self, provider_type="OpenRouter (Khuyên dùng)", api_key="", model_name="google/gemini-2.5-flash"):
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

        if "OpenRouter" in self.provider_type:
            return self._call_openrouter(prompt, system_instruction)
        elif "Gemini" in self.provider_type:
            return self._call_gemini_sdk(prompt, system_instruction)
        elif "OpenAI" in self.provider_type:
            return self._call_openai(prompt, system_instruction)
        elif "Anthropic" in self.provider_type:
            return self._call_anthropic(prompt, system_instruction)
        elif "Ollama" in self.provider_type:
            return self._call_ollama(prompt, system_instruction)
        else:
            raise ValueError(f"Provider {self.provider_type} chưa được hỗ trợ.")

    def _call_openrouter(self, prompt: str, system_instruction: str) -> str:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/giangvien/edu-ai",
            "X-Title": "Hệ thống ra đề AI"
        }
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.2
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=90)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise Exception(f"Lỗi OpenRouter: {str(e)}")

    def _call_gemini_sdk(self, prompt: str, system_instruction: str) -> str:
        # Chấp nhận mọi key người dùng nhập vào, không bắt bẻ định dạng
        try:
            genai.configure(api_key=self.api_key)
            generation_config = genai.types.GenerationConfig(
                temperature=0.2, 
                top_p=0.95, 
                max_output_tokens=8192
            )
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction if system_instruction else None,
                generation_config=generation_config
            )
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            raise Exception(f"Lỗi hệ thống Gemini: {str(e)}")

    def _call_openai(self, prompt: str, system_instruction: str) -> str:
        url = "https://api.openai.com/v1/chat/completions"
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
            "temperature": 0.2
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=90)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise Exception(f"Lỗi OpenAI: {str(e)}")

    def _call_anthropic(self, prompt: str, system_instruction: str) -> str:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "max_tokens": 8192,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": prompt}]
        }
        if system_instruction:
            payload["system"] = system_instruction
            
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=90)
            response.raise_for_status()
            return response.json()["content"][0]["text"]
        except Exception as e:
            raise Exception(f"Lỗi Anthropic/Claude: {str(e)}")

    def _call_ollama(self, prompt: str, system_instruction: str) -> str:
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": f"{system_instruction}\n\n{prompt}",
            "stream": False
        }
        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            raise Exception(f"Lỗi Ollama (Local): {str(e)}")
