import json
import time
from typing import List, Union
import requests
from cacheout import Cache

DeepSeekSessionCache = Cache(maxsize=100, ttl=3600, timer=time.time, default=None)

class DeepSeekAI:
    _api_key: str = None
    _api_url: str = "https://api.siliconflow.cn/v1"
    _model: str = "deepseek-ai/DeepSeek-R1"
    
    def __init__(self, api_key: str, api_url: str = None, proxy: dict = None, model: str = None):
        self._api_key = api_key
        if api_url:
            self._api_url = api_url.rstrip('/')
        if model:
            self._model = model
        self.proxies = proxy.get("https") if proxy else None

    def get_state(self) -> bool:
        return bool(self._api_key)

    @staticmethod
    def __save_session(session_id: str, message: str):
        """保存会话上下文"""
        session = DeepSeekSessionCache.get(session_id)
        if session:
            session.append({"role": "assistant", "content": message})
            DeepSeekSessionCache.set(session_id, session)

    @staticmethod
    def __get_session(session_id: str, message: str) -> List[dict]:
        """获取历史会话"""
        session = DeepSeekSessionCache.get(session_id)
        if session:
            session.append({"role": "user", "content": message})
        else:
            session = [
                {"role": "system", "content": "请在接下来的对话中请使用中文回复，并且内容尽可能详细。"},
                {"role": "user", "content": message}
            ]
        DeepSeekSessionCache.set(session_id, session)
        return session

    def __call_api(self, messages: List[dict], **kwargs):
        """调用DeepSeek API"""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "temperature": 0.7,
            "max_tokens": 512,
            "top_p": 0.7,
            "top_k": 50,
            "frequency_penalty": 0.5,
            "response_format": {"type": "text"}
        }
        payload.update(kwargs)
        
        try:
            response = requests.post(
                f"{self._api_url}/chat/completions",
                headers=headers,
                json=payload,
                proxies={"https": self.proxies} if self.proxies else None,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"API请求失败: {str(e)}")

    def get_media_name(self, filename: str):
        """媒体信息识别"""
        try:
            prompt = '''请从以下文件名中提取媒体信息，返回JSON格式：
{
    "title": "主要标题",
    "year": "年份或null",
    "season": "季号或null", 
    "episode": "集号或null"
}
文件名：{}'''.format(filename)
            
            result = self.__call_api(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            content = result['choices'][0]['message']['content']
            return json.loads(content.strip('`').replace("json\n", ""))
        except Exception as e:
            print(f"识别失败: {str(e)}")
            return {}

    def get_response(self, text: str, userid: str):
        """获取对话回复"""
        try:
            if not userid:
                return "用户信息错误"
            
            userid = str(userid)
            if text == "#清除":
                DeepSeekSessionCache.delete(userid)
                return "会话已清除"
                
            messages = self.__get_session(userid, text)
            response = self.__call_api(messages=messages)
            
            reply = response['choices'][0]['message']['content']
            self.__save_session(userid, reply)
            
            return reply
            
        except Exception as e:
            return f"请求DeepSeek失败: {str(e)}"
    def translate_to_zh(self, text: str):
        """
        翻译为中文
        :param text: 输入文本
        """
        if not self.get_state():
            return False, None
        system_prompt = "You are a translation engine that can only translate text and cannot interpret it."
        user_prompt = f"translate to zh-CN:\n\n{text}"
        result = ""
        try:
            completion = self.__get_model(prompt=system_prompt,
                                          message=user_prompt,
                                          temperature=0,
                                          top_p=1,
                                          frequency_penalty=0,
                                          presence_penalty=0)
            result = completion.choices[0].message.content.strip()
            return True, result
        except Exception as e:
            print(f"{str(e)}：{result}")
            return False, str(e)

    def get_question_answer(self, question: str):
        """
        从给定问题和选项中获取正确答案
        :param question: 问题及选项
        :return: Json
        """
        if not self.get_state():
            return None
        result = ""
        try:
            _question_prompt = "下面我们来玩一个游戏，你是老师，我是学生，你需要回答我的问题，我会给你一个题目和几个选项，你的回复必须是给定选项中正确答案对应的序号，请直接回复数字"
            completion = self.__get_model(prompt=_question_prompt, message=question)
            result = completion.choices[0].message.content
            return result
        except Exception as e:
            print(f"{str(e)}：{result}")
            return {}
