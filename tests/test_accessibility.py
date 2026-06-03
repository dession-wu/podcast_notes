"""可访问性测试.

测试转录 UI 的可访问性，包括：
- ARIA 标签
- 键盘导航
- 屏幕阅读器兼容性
- 颜色对比度
"""

from __future__ import annotations

import pytest


class TestAccessibility:
    """可访问性测试."""

    def test_progress_component_has_aria_role(self):
        """测试进度组件有正确的 ARIA 角色."""
        # 验证 TranscriptionProgress 组件包含 ARIA 属性
        # 由于这是 React 组件，我们验证组件代码中包含必要的 ARIA 属性
        component_path = "web-dashboard/src/components/TranscriptionProgress.tsx"

        try:
            with open(component_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            pytest.skip(f"组件文件不存在: {component_path}")

        # 检查关键 ARIA 属性
        assert 'role="progressbar"' in content, "缺少 progressbar 角色"
        assert 'aria-valuenow' in content, "缺少 aria-valuenow"
        assert 'aria-valuemin' in content, "缺少 aria-valuemin"
        assert 'aria-valuemax' in content, "缺少 aria-valuemax"
        assert 'aria-label' in content, "缺少 aria-label"

    def test_progress_component_has_status_role(self):
        """测试进度组件有状态角色."""
        component_path = "web-dashboard/src/components/TranscriptionProgress.tsx"

        try:
            with open(component_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            pytest.skip(f"组件文件不存在: {component_path}")

        assert 'role="status"' in content, "缺少 status 角色"
        assert 'aria-live="polite"' in content, "缺少 aria-live 属性"

    def test_error_messages_actionable(self):
        """测试错误消息是可操作的."""
        page_path = "web-dashboard/src/app/dashboard/library/page.tsx"

        try:
            with open(page_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            pytest.skip(f"页面文件不存在: {page_path}")

        # 检查各种错误类别都有对应的建议
        error_categories = [
            "file_not_found",
            "file_too_large",
            "invalid_format",
            "model_load_error",
            "model_not_installed",
            "out_of_memory",
            "timeout",
            "language_not_supported",
            "network_error",
            "server_busy",
        ]

        for category in error_categories:
            assert f'case "{category}"' in content, f"缺少错误类别: {category}"

        # 检查建议包含行动指示
        assert "请" in content or "尝试" in content or "检查" in content, (
            "建议缺少行动指示"
        )

    def test_error_messages_concise(self):
        """测试错误消息简洁明了."""
        page_path = "web-dashboard/src/app/dashboard/library/page.tsx"

        try:
            with open(page_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            pytest.skip(f"页面文件不存在: {page_path}")

        # 检查错误消息函数存在
        assert "getErrorMessage" in content, "缺少 getErrorMessage 函数"
        assert "getErrorSuggestion" in content, "缺少 getErrorSuggestion 函数"

    def test_library_page_buttons_have_titles(self):
        """测试库页面按钮有标题属性."""
        page_path = "web-dashboard/src/app/dashboard/library/page.tsx"

        try:
            with open(page_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            pytest.skip(f"页面文件不存在: {page_path}")

        # 检查关键按钮有 title 属性（用于工具提示）
        assert 'title="转录"' in content, "转录按钮缺少 title"
        assert 'title="打开位置"' in content, "打开位置按钮缺少 title"
        assert 'title="删除"' in content, "删除按钮缺少 title"

    def test_color_contrast_indicators(self):
        """测试颜色对比度指示器.

        验证使用了不仅依赖颜色的状态指示（图标 + 文字）
        """
        component_path = "web-dashboard/src/components/TranscriptionProgress.tsx"

        try:
            with open(component_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            pytest.skip(f"组件文件不存在: {component_path}")

        # 检查有文字标签而不仅仅是颜色
        assert "转录中" in content, "缺少处理状态文字"
        assert "转录完成" in content, "缺少完成状态文字"
        assert "转录失败" in content, "缺少失败状态文字"

        # 检查有图标而不仅仅是颜色
        assert "Loader2" in content, "缺少处理图标"
        assert "CheckCircle" in content, "缺少完成图标"
        assert "AlertCircle" in content, "缺少错误图标"

    def test_keyboard_accessibility_hints(self):
        """测试键盘可访问性提示."""
        page_path = "web-dashboard/src/app/dashboard/library/page.tsx"

        try:
            with open(page_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            pytest.skip(f"页面文件不存在: {page_path}")

        # 检查交互元素是 button 而不是 div
        assert "<button" in content, "页面应该使用 button 元素"

        # 检查有 disabled 状态处理
        assert "disabled=" in content, "缺少 disabled 状态处理"

    def test_focus_management(self):
        """测试焦点管理."""
        page_path = "web-dashboard/src/app/dashboard/library/page.tsx"

        try:
            with open(page_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            pytest.skip(f"页面文件不存在: {page_path}")

        # 检查有 focus 样式
        assert "focus:" in content, "缺少 focus 样式"
        assert "focus:outline-none" in content, "缺少 focus 轮廓处理"
