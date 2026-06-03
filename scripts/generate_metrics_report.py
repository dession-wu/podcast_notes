#!/usr/bin/env python3
"""生成转录性能指标报告.

用法:
    python scripts/generate_metrics_report.py
    python scripts/generate_metrics_report.py --days 30
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.metrics import metrics_collector


def main() -> int:
    """生成并打印指标报告.

    Returns:
        退出码 (0=成功, 1=失败)
    """
    parser = argparse.ArgumentParser(description="生成转录性能指标报告")
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="统计天数 (默认: 7)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出",
    )
    args = parser.parse_args()

    summary = metrics_collector.get_summary(days=args.days)

    if args.json:
        import json
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    # 打印报告
    print("=" * 60)
    print("转录性能指标报告")
    print(f"生成时间: {datetime.now().isoformat()}")
    print("=" * 60)

    if not summary:
        print("\n暂无指标数据。")
        return 0

    print(f"\n📊 统计周期: 最近 {summary['period_days']} 天")
    print(f"📋 总任务数: {summary['total_jobs']}")
    print(f"✅ 成功: {summary['completed']}")
    print(f"❌ 失败: {summary['failed']}")
    print(f"📈 成功率: {summary['success_rate']:.1%}")
    print(f"⏱️  系统可用性: {summary['uptime_percentage']:.1f}%")

    if summary["avg_duration_seconds"] > 0:
        avg_mins = summary["avg_duration_seconds"] / 60
        print(f"⏰ 平均处理时间: {avg_mins:.1f} 分钟")

    if summary["avg_real_time_factor"] > 0:
        rtf = summary["avg_real_time_factor"]
        print(f"🚀 平均实时因子 (RTF): {rtf:.2f}x")
        if rtf < 1.0:
            speedup = 1.0 / rtf
            print(f"   (处理速度是实时的 {speedup:.1f} 倍)")
        else:
            print(f"   (处理速度是实时的 1/{rtf:.1f})")

    # 按引擎统计
    if summary.get("providers"):
        print("\n🔧 按引擎统计:")
        for provider, stats in summary["providers"].items():
            success_rate = (
                stats["completed"] / stats["total"] * 100
                if stats["total"] > 0
                else 0
            )
            print(
                f"   {provider}: "
                f"{stats['completed']}/{stats['total']} 成功 "
                f"({success_rate:.0f}%)"
            )

    print("\n" + "=" * 60)

    # 目标检查
    print("\n🎯 目标达成情况:")
    targets = {
        "可用性 >= 99.9%": summary["uptime_percentage"] >= 99.9,
        "成功率 >= 95%": summary["success_rate"] >= 0.95,
        "RTF < 1.0 (快于实时)": summary.get("avg_real_time_factor", 999) < 1.0,
    }

    all_passed = True
    for target, met in targets.items():
        status = "✅ 通过" if met else "❌ 未通过"
        if not met:
            all_passed = False
        print(f"   {status}: {target}")

    print()
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
