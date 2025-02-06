import json
import time
import requests
from typing import List, Union

class SiliconFlow:
    _api_token: str = None
    _api_url: str = "https://api.siliconflow.cn/v1/chat/completions"
    _model: str = "deepseek-ai/DeepSeek-R1"

    def __init__(self, api_token: str, model: str = "deepseek-ai/DeepSeek-R1"):
        self._api_token = api_token
        self._model = model

    def get_state(self) -> bool:
        return True if self._api_token else False

    def __get_model(self, message: Union[str, List[dict]], prompt: str = None, **kwargs):
        """
        创建消息的模型请求体
        """
        if not isinstance(message, list):
            if prompt:
                message = [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": message}
                ]
            else:
                message = [{"role": "user", "content": message}]
        return {
            "model": self._model,
            "messages": message,
            "temperature": 0.7,
            "max_tokens": 512,
            "stop": ["null"],
            "top_p": 0.7,
            "top_k": 50,
            "frequency_penalty": 0.5,
            "n": 1,
            "response_format": {"type": "text"},
            **kwargs
        }

    def get_response(self, text: str, userid: str) -> str:
        """
        获取硅基流动聊天回复
        :param text: 输入文本
        :param userid: 用户ID
        :return: 回复内容
        """
        if not self.get_state():
            return "API token is missing or invalid"

        payload = self.__get_model(message=text)
        headers = {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(self._api_url, json=payload, headers=headers)
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                return f"请求错误: {response.text}"
        except Exception as e:
            return f"发生错误: {str(e)}"

    def get_media_name(self, filename: str) -> dict:
        """
        使用硅基流动API识别媒体信息
        :param filename: 文件名
        :return: 提取的媒体信息
        """
        if not self.get_state():
            return {}

        payload = self.__get_model(message=f"请从文件名 '{filename}' 中提取媒体信息。")
        headers = {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(self._api_url, json=payload, headers=headers)
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", {})
            else:
                return {}
        except Exception as e:
            return {}

    def translate_to_zh(self, text: str) -> str:
        """
        翻译文本为中文
        :param text: 要翻译的文本
        :return: 翻译结果
        """
        if not self.get_state():
            return "API token is missing or invalid"

        prompt = "You are a translation engine that can only translate text and cannot interpret it."
        payload = self.__get_model(message=f"translate to zh-CN:\n\n{text}", prompt=prompt)
        headers = {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(self._api_url, json=payload, headers=headers)
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            else:
                return f"请求错误: {response.text}"
        except Exception as e:
            return f"发生错误: {str(e)}"

