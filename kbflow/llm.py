import json
import os
import urllib.request

try:
    import httpx
except ImportError:
    httpx = None

from kbflow.config import get_llm_config


class LLMNotConfiguredError(Exception):
    pass


class LLMError(Exception):
    pass


def _http_post_json(url, headers, body):
    if httpx is not None:
        response = httpx.post(url, headers=headers, content=body, timeout=60.0)
        if response.status_code == 401:
            raise LLMError(
                "API Key 无效（HTTP 401）。\n"
                "  最常见原因：只配了 api_key，但 base_url/model 没配——默认指向 OpenAI 官方，而你的 key 可能是别的服务（如 DeepSeek）。\n"
                "  请运行 python kbflow.py config 一次性配齐三样（api_key + base_url + model），三者必须指向同一个服务。\n"
                "  或手动检查 ~/.kbflow/config.ini 的 [llm] 段 / 环境变量 KBFLOW_LLM_API_KEY、KBFLOW_LLM_BASE_URL、KBFLOW_LLM_MODEL"
            )
        response.raise_for_status()
        return response.json()
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60.0) as response:
            raw = response.read()
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise LLMError(
                "API Key 无效（HTTP 401）。请运行 python kbflow.py config 一次性配齐 "
                "api_key + base_url + model（三者必须指向同一个服务），"
                "或检查 ~/.kbflow/config.ini / 环境变量。"
            ) from e
        raise LLMError("LLM HTTP 错误 %s: %s" % (e.code, e.reason)) from e
    return json.loads(raw.decode("utf-8"))


class LLMClient:
    def __init__(self, base_url, api_key, model):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def complete(self, prompt, system=""):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": self.model, "messages": messages}
        url = self.base_url + "/chat/completions"
        headers = {
            "Authorization": "Bearer " + self.api_key,
            "Content-Type": "application/json",
        }
        body = json.dumps(payload).encode("utf-8")
        try:
            data = _http_post_json(url, headers, body)
        except LLMError:
            raise
        except Exception as e:
            raise LLMError("LLM 调用失败: %s" % e) from e
        return data["choices"][0]["message"]["content"]


def require_llm():
    config = get_llm_config()
    if not config["api_key"] or not config["api_key"].strip():
        raise LLMNotConfiguredError(
            "未检测到 LLM API Key。请任选一种方式配置：\n"
            "  1. 快速配置: 运行 python kbflow.py config（交互式生成 ~/.kbflow/config.ini）\n"
            "  2. 手动配置: 参考项目根目录 config.example.ini，复制为 ~/.kbflow/config.ini 填入 key\n"
            "  3. 环境变量: export KBFLOW_LLM_API_KEY=\"sk-...\""
        )
    return LLMClient(config["base_url"], config["api_key"], config["model"])
