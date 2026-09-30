import json
import os
import subprocess


class McpClient:
    def __init__(self, command, args=None, env=None, cwd=None):
        merged_env = dict(os.environ)
        if env:
            merged_env.update(env)
        self.proc = subprocess.Popen(
            [command] + (args or []),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=merged_env,
            cwd=cwd,
        )
        self._id = 0
        self._initialize()

    def _request(self, method, params=None):
        self._id += 1
        req = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}}
        payload = (json.dumps(req) + "\n").encode("utf-8")
        self.proc.stdin.write(payload)
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("MCP 进程无响应（请检查 toolbox 命令和数据库连接配置）")
        return json.loads(line.decode("utf-8"))

    def _initialize(self):
        self._request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "kbflow", "version": "1.0.0"},
        })
        self.proc.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        self.proc.stdin.flush()

    def call_tool(self, name, arguments=None):
        resp = self._request("tools/call", {"name": name, "arguments": arguments or {}})
        if "error" in resp:
            raise RuntimeError("MCP tools/call 失败: %s" % resp["error"])
        return resp.get("result", {})

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.terminate()
        except Exception:
            pass


def _extract_text(result):
    for item in result.get("content", []):
        if item.get("type") == "text":
            return item.get("text", "")
    return ""


def _parse_table_names(text):
    names = []
    for line in text.splitlines():
        line = line.strip().strip(",").strip("'").strip('"')
        if line and not line.startswith(("{", "[", "#", "--")):
            names.append(line)
    return names
