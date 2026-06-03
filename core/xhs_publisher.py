"""小红书发布模块 — 通过HTTP API调用xiaohongshu-mcp服务.

集成方案：
1. 启动 xiaohongshu-mcp-windows-amd64.exe 服务（端口18060）
2. 通过 HTTP POST /api/publish_content 发布图文
3. 支持标题、正文、图片路径、标签等参数

前置条件：
- 已运行 xiaohongshu-login-windows-amd64.exe 完成扫码登录
- Cookie已保存到 data/cookies 目录
"""

import json
import subprocess
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

from utils import get_logger

logger = get_logger(__name__)


class XHSPublisherError(Exception):
    """小红书发布相关错误."""
    pass

# 默认配置
MCP_HOST = "http://localhost:18060"
MCP_API_PREFIX = "/api/v1"  # API 路由前缀
MCP_TIMEOUT = 120  # 发布操作超时时间（秒）
MAX_TITLE_LENGTH = 20  # 小红书标题限制
MAX_CONTENT_LENGTH = 1000  # 小红书正文限制


class XHSPublisher:
    """小红书发布器.

    负责：
    1. 启动/停止 xiaohongshu-mcp 服务
    2. 检查登录状态
    3. 发布图文内容
    """

    def __init__(self, mcp_host: str = MCP_HOST, mcp_binary_path: Optional[str] = None):
        self.mcp_host = mcp_host.rstrip("/")
        self.mcp_binary_path = mcp_binary_path or self._find_mcp_binary()
        self._process: Optional[subprocess.Popen] = None

    def _find_mcp_binary(self) -> str:
        """自动查找MCP可执行文件."""
        project_root = Path(__file__).parent.parent
        candidates = [
            project_root / "tools" / "xiaohongshu-mcp" / "xiaohongshu-mcp-windows-amd64.exe",
            project_root / "tools" / "xiaohongshu-mcp" / "xiaohongshu-mcp",
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        raise FileNotFoundError("未找到 xiaohongshu-mcp 可执行文件，请确保已下载到 tools/xiaohongshu-mcp/ 目录")

    def start_service(self, headless: bool = True) -> bool:
        """启动MCP服务.

        Args:
            headless: True=无头模式(无浏览器界面), False=有界面(方便调试)

        Returns:
            是否启动成功
        """
        if self.is_service_running():
            logger.info("MCP服务已在运行")
            return True

        cmd = [self.mcp_binary_path]
        if not headless:
            cmd.append("-headless=false")

        logger.info("启动MCP服务", binary=self.mcp_binary_path, headless=headless)
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            # 等待服务启动
            for i in range(30):
                time.sleep(1)
                if self.is_service_running():
                    logger.info("MCP服务启动成功")
                    return True
                logger.debug("等待MCP服务启动", attempt=i + 1)

            logger.error("MCP服务启动超时")
            return False
        except Exception as e:
            logger.error("启动MCP服务失败", error=str(e))
            return False

    def stop_service(self):
        """停止MCP服务."""
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
            logger.info("MCP服务已停止")

    def is_service_running(self) -> bool:
        """检查MCP服务是否运行."""
        try:
            req = urllib.request.Request(
                f"{self.mcp_host}{MCP_API_PREFIX}/login/status",
                method="GET",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def check_login_status(self) -> dict:
        """检查小红书登录状态.

        Returns:
            {"is_logged_in": bool, "username": str}
        """
        try:
            req = urllib.request.Request(
                f"{self.mcp_host}{MCP_API_PREFIX}/login/status",
                method="GET",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                # API 返回格式: {"success": true, "data": {"is_logged_in": true, ...}}
                if data.get("success") and "data" in data:
                    login_data = data["data"]
                    return {
                        "is_logged_in": login_data.get("is_logged_in", False),
                        "username": login_data.get("username", ""),
                    }
                return {"is_logged_in": False, "username": ""}
        except Exception as e:
            logger.error("检查登录状态失败", error=str(e))
            return {"is_logged_in": False, "username": ""}

    def publish_note(
        self,
        title: str,
        content: str,
        image_paths: list[str],
        tags: Optional[list[str]] = None,
        is_original: bool = True,
        visibility: str = "public",
    ) -> dict:
        """发布图文笔记到小红书.

        Args:
            title: 标题（≤20字，超出自动截断）
            content: 正文（≤1000字，超出自动截断）
            image_paths: 图片本地绝对路径列表
            tags: 标签列表（如 ["播客笔记", "干货分享"]）
            is_original: 是否标记原创
            visibility: 可见范围（public/followers/private）

        Returns:
            {"success": bool, "feed_id": str, "message": str}
        """
        # 截断标题和正文
        title = title[:MAX_TITLE_LENGTH]
        content = content[:MAX_CONTENT_LENGTH]

        # 确保图片路径是绝对路径
        abs_image_paths = []
        for p in image_paths:
            path = Path(p)
            if not path.is_absolute():
                path = path.resolve()
            abs_image_paths.append(str(path))

        payload = {
            "title": title,
            "content": content,
            "images": abs_image_paths,
            "tags": tags or [],
            "is_original": is_original,
            "visibility": visibility,
        }

        logger.info(
            "发布小红书笔记",
            title=title,
            image_count=len(abs_image_paths),
            tags=tags,
        )

        try:
            req = urllib.request.Request(
                f"{self.mcp_host}{MCP_API_PREFIX}/publish",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=MCP_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("success"):
                    result_data = data.get("data", {})
                    feed_id = result_data.get("feed_id", "") if isinstance(result_data, dict) else ""
                    logger.info("发布成功", feed_id=feed_id)
                    return {
                        "success": True,
                        "feed_id": feed_id,
                        "message": data.get("message", "发布成功"),
                    }
                else:
                    logger.error("发布失败", message=data.get("message", "未知错误"))
                    return {
                        "success": False,
                        "feed_id": "",
                        "message": data.get("message", "发布失败"),
                    }
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            logger.error("发布请求HTTP错误", status=e.code, body=error_body)
            return {"success": False, "feed_id": "", "message": f"HTTP {e.code}: {error_body}"}
        except Exception as e:
            logger.error("发布请求异常", error=str(e))
            return {"success": False, "feed_id": "", "message": str(e)}

    def __enter__(self):
        self.start_service()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_service()
        return False


def adapt_v9_to_xhs(structured_content: dict) -> dict:
    """将v9结构化内容适配为小红书发布格式.

    转换规则：
    1. 标题：hook_title → 截断至20字
    2. 正文：thinking + stages摘要 + reflections → 组合为≤1000字
    3. 图片：传入已生成的图片路径列表
    4. 标签：tags字段直接使用

    Args:
        structured_content: v9生成的结构化JSON

    Returns:
        {"title": str, "content": str, "tags": list[str]}
    """
    # 标题
    title = structured_content.get("hook_title", "播客笔记")[:MAX_TITLE_LENGTH]

    # 正文构建
    parts = []

    # 思考导语
    thinking = structured_content.get("thinking", "")
    if thinking:
        parts.append(thinking)
        parts.append("")

    # 阶段摘要（每个阶段一句话）
    stages = structured_content.get("stages", [])
    for stage in stages:
        stage_title = stage.get("stage_title", "")
        time_range = stage.get("time_range", "")
        if stage_title:
            line = stage_title
            if time_range:
                line += f" [{time_range}]"
            parts.append(line)

            # 每个话题一句话
            for topic in stage.get("topics", [])[:2]:  # 每个阶段最多2个话题
                topic_title = topic.get("topic_title", "")
                if topic_title:
                    parts.append(f"  · {topic_title}")

            parts.append("")

    # 思考金句
    reflections = structured_content.get("reflections", [])
    if reflections:
        parts.append("💭 核心思考")
        for r in reflections:
            parts.append(f"  · {r}")

    content = "\n".join(parts)

    # 截断至1000字
    if len(content) > MAX_CONTENT_LENGTH:
        content = content[:MAX_CONTENT_LENGTH - 3] + "..."

    # 标签
    tags = structured_content.get("tags", ["播客笔记", "干货分享"])

    return {
        "title": title,
        "content": content,
        "tags": tags,
    }


def publish_v9_note(
    structured_content: dict | None,
    image_paths: list[str],
    mcp_binary_path: Optional[str] = None,
) -> dict:
    """一键发布v9生成的播客笔记到小红书.

    完整流程：
    1. 适配v9内容为小红书格式
    2. 启动MCP服务
    3. 检查登录状态
    4. 发布图文
    5. 停止MCP服务

    Args:
        structured_content: v9结构化内容（可为None，此时使用默认标题）
        image_paths: 已生成的图片绝对路径列表
        mcp_binary_path: MCP可执行文件路径（可选）

    Returns:
        {"success": bool, "feed_id": str, "message": str}
    """
    # 适配内容格式
    if structured_content is None:
        structured_content = {}
    xhs_data = adapt_v9_to_xhs(structured_content)

    # 启动服务并发布
    with XHSPublisher(mcp_binary_path=mcp_binary_path) as publisher:
        # 检查登录
        login_status = publisher.check_login_status()
        if not login_status["is_logged_in"]:
            raise XHSPublisherError(
                "未登录小红书，请先运行 xiaohongshu-login-windows-amd64.exe 完成扫码登录"
            )

        logger.info("已登录", username=login_status["username"])

        # 发布
        return publisher.publish_note(
            title=xhs_data["title"],
            content=xhs_data["content"],
            image_paths=image_paths,
            tags=xhs_data["tags"],
            is_original=True,
        )
