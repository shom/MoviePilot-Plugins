from typing import Any, List, Dict, Tuple
from app.core.config import settings
from app.core.event import eventmanager, Event
from app.log import logger
from app.plugins import _PluginBase
import requests
import json
from app.schemas.types import EventType, ChainEventType


class SiliconFlow(_PluginBase):
    # 插件名称
    plugin_name = "SiliconFlow"
    # 插件描述
    plugin_desc = "消息交互支持与硅基流动对话。"
    # 插件图标
    plugin_icon = "SiliconFlow_A.png"
    # 插件版本
    plugin_version = "0.0.1"
    # 插件作者
    plugin_author = "shom"
    # 作者主页
    author_url = "https://github.com/shom"
    # 插件配置项ID前缀
    plugin_config_prefix = "siliconflow_"
    # 加载顺序
    plugin_order = 15
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _enabled = False
    _proxy = False
    _recognize = False
    _siliconflow_url = "https://api.siliconflow.cn/v1/chat/completions"
    _siliconflow_token = None
    _model = "deepseek-ai/DeepSeek-R1"

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self._proxy = config.get("proxy")
            self._recognize = config.get("recognize")
            self._siliconflow_token = config.get("siliconflow_token")
            self._model = config.get("model", self._model)

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'proxy',
                                            'label': '使用代理服务器',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'recognize',
                                            'label': '辅助识别',
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'siliconflow_token',
                                            'label': '硅基流动 API Token',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'model',
                                            'label': '默认模型',
                                            'placeholder': 'deepseek-ai/DeepSeek-R1',
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "proxy": False,
            "recognize": False,
            "siliconflow_token": "",
            "model": "deepseek-ai/DeepSeek-R1"
        }

    def get_page(self) -> List[dict]:
        pass

    @eventmanager.register(EventType.UserMessage)
    def talk(self, event: Event):
        """
        监听用户消息，获取硅基流动回复
        """
        if not self._enabled or not self._siliconflow_token:
            return
        text = event.event_data.get("text")
        userid = event.event_data.get("userid")
        channel = event.event_data.get("channel")
        if not text:
            return
        response = self.get_siliconflow_response(text, userid)
        if response:
            self.post_message(channel=channel, title=response, userid=userid)

    @eventmanager.register(ChainEventType.NameRecognize)
    def recognize(self, event: Event):
        """
        监听识别事件，使用硅基流动辅助识别名称
        """
        if not self._recognize:
            return
        if not event.event_data:
            return
        title = event.event_data.get("title")
        if not title:
            return
        # 调用硅基流动API进行识别
        response = self.get_siliconflow_media_name(title)
        logger.info(f"硅基流动返回结果：{response}")
        if response:
            event.event_data = {
                'title': title,
                'name': response.get("title"),
                'year': response.get("year"),
                'season': response.get("season"),
                'episode': response.get("episode")
            }
        else:
            event.event_data = {}

    def get_siliconflow_response(self, text: str, userid: str) -> str:
        """
        使用硅基流动API获取聊天回复
        """
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": text}],
            "stream": False,
            "max_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.7,
            "top_k": 50,
            "frequency_penalty": 0.5,
            "n": 1,
            "response_format": {"type": "text"},
            "tools": []
        }
        headers = {
            "Authorization": f"Bearer {self._siliconflow_token}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(self._siliconflow_url, json=payload, headers=headers)
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                return f"请求错误: {response.text}"
        except Exception as e:
            return f"发生错误: {str(e)}"

    def get_siliconflow_media_name(self, filename: str) -> dict:
        """
        使用硅基流动辅助识别文件名中的媒体信息
        """
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": f"请从文件名 '{filename}' 中提取媒体信息。"}],
            "stream": False,
            "max_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.7,
            "top_k": 50,
            "frequency_penalty": 0.5,
            "n": 1,
            "response_format": {"type": "json"},
            "tools": []
        }
        headers = {
            "Authorization": f"Bearer {self._siliconflow_token}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(self._siliconflow_url, json=payload, headers=headers)
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", {})
            else:
                return {}
        except Exception as e:
            logger.error(f"硅基流动辅助识别失败: {str(e)}")
            return {}
    
    def stop_service(self):
        """
        退出插件
        """
        pass

