# app/services/mcp_service.py
import asyncio
import json
import subprocess
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class MCPService:
    """MCP (Model Context Protocol) 服务客户端"""

    def __init__(self, command: str, args: List[str]):
        self.command = command
        self.args = args
        self.process = None

    async def start(self):
        """启动MCP服务进程"""
        try:
            logger.info(f"Starting MCP service: {self.command} {' '.join(self.args)}")
            # 在MCP项目目录中启动进程，确保能读取到正确的.env文件
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd="/home/jimmy/WebstormProjects/untitled"  # 设置工作目录
            )
            logger.info(f"MCP process started with PID: {self.process.pid}")

            # 等待进程启动
            await asyncio.sleep(0.5)

            # 发送初始化消息
            logger.info("Sending initialize request")
            await self._send_request({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "Longchian Agent",
                        "version": "1.0.0"
                    }
                }
            })

            # 读取初始化响应
            logger.info("Reading initialize response")
            response = await self._read_response()
            logger.info(f"Initialize response: {response}")

            return True
        except Exception as e:
            logger.error(f"Failed to start MCP service: {e}")
            if self.process:
                self.process.terminate()
                self.process = None
            return False

    async def stop(self):
        """停止MCP服务进程"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            self.process = None

    async def _send_request(self, request: Dict[str, Any]):
        """发送请求到MCP服务"""
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP service not started")

        message = json.dumps(request) + "\n"
        self.process.stdin.write(message.encode())
        await self.process.stdin.drain()

    async def _read_response(self) -> Dict[str, Any]:
        """从MCP服务读取响应"""
        if not self.process or not self.process.stdout:
            raise RuntimeError("MCP service not started")

        line = await self.process.stdout.readline()
        if not line:
            raise RuntimeError("MCP service closed")

        return json.loads(line.decode().strip())

    async def list_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        try:
            await self._send_request({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list"
            })

            response = await self._read_response()
            if "result" in response and "tools" in response["result"]:
                return response["result"]["tools"]
            return []
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用MCP工具"""
        try:
            await self._send_request({
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": name,
                    "arguments": arguments
                }
            })

            response = await self._read_response()
            if "result" in response:
                return {
                    "success": True,
                    "data": response["result"]
                }
            elif "error" in response:
                return {
                    "success": False,
                    "error": response["error"]["message"]
                }
            else:
                return {
                    "success": False,
                    "error": "Unknown response format"
                }
        except Exception as e:
            logger.error(f"Failed to call tool {name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# 全局MCP服务实例
mcp_service = MCPService(
    command="node",
    args=["/home/jimmy/WebstormProjects/untitled/dist/index.js"]
)