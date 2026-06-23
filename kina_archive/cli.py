#!/usr/bin/env python3
import os
import sys
import time
import hashlib
import argparse
from datetime import datetime, timedelta

from .db import ArchiveDB
from .screenshot import Screenshotter
from .compare import ImageComparator
from .report import ReportGenerator


def print_logo():
    print("""
    ╔══════════════════════════════════════╗
    ║     🕐 kina-archive 网页时光机        ║
    ║                                      ║
    ║     截图 · 对比 · 追踪 · 回溯         ║
    ╚══════════════════════════════════════╝
    """)


def parse_ignore_regions(regions_str: str) -> list:
    """解析忽略区域字符串 'x,y,w,h;x,y,w,h'"""
    if not regions_str:
        return None
    regions = []
    for part in regions_str.split(";"):
        coords = [int(c.strip()) for c in part.split(",")]
        if len(coords) == 4:
            regions.append(tuple(coords))
    return regions if regions else None


def snapshot_cmd(args):
    db = ArchiveDB(args.db)
    screenshotter = Screenshotter(args.output, browser=args.browser)

    print(f"📸 截图: {args.url}")

    image_path, width, height = screenshotter.capture(
        args.url, args.width, args.height, not args.viewport
    )

    with open(image_path, "rb") as f:
        img_hash = hashlib.md5(f.read()).hexdigest()
    size = os.path.getsize(image_path)

    last = db.get_last_snapshot(args.url)
    if last and last["image_hash"] == img_hash:
        print("  ✅ 无变化，删除重复截图")
        os.remove(image_path)
        db.close()
        return

    snap_id = db.add_snapshot(args.url, image_path, img_hash, size, width, height)
    print(f"  ✅ 已保存 #{snap_id}: {image_path}")

    if last:
        print(f"  🔍 对比中... [模式: {args.mode}]")
        comparator = ImageComparator(args.output)
        ignore = parse_ignore_regions(args.ignore)
        similarity, diff_path, pixel_diff = comparator.compare(
            last["image_path"], image_path, mode=args.mode, ignore_regions=ignore
        )
        db.add_change(args.url, last["id"], snap_id, diff_path, similarity, pixel_diff)
        print(f"  📊 相似度: {similarity:.2%}")
        if similarity < 0.2:
            print(f"  ⚠️  相似度极低，可能是验证码/故障页面")
        elif similarity < 0.95:
            print(f"  ⚠️  检测到明显变化!")
        print(f"  🖼️  差异图: {diff_path}")

    db.close()


def watch_cmd(args):
    db = ArchiveDB(args.db)
    screenshotter = Screenshotter(args.output, browser=args.browser)
    comparator = ImageComparator(args.output)
    ignore = parse_ignore_regions(args.ignore)

    print(f"👁️  监控: {args.url}")
    print(f"   间隔: {args.interval}秒 | 模式: {args.mode} | 按 Ctrl+C 停止\n")

    count = 0
    try:
        while True:
            print(f"\n--- [{datetime.now().strftime('%H:%M:%S')}] 第 {count + 1} 次截图 ---")

            image_path, width, height = screenshotter.capture(args.url)

            with open(image_path, "rb") as f:
                img_hash = hashlib.md5(f.read()).hexdigest()
            size = os.path.getsize(image_path)

            last = db.get_last_snapshot(args.url)
            if last and last["image_hash"] == img_hash:
                print("  ✅ 无变化")
                os.remove(image_path)
            else:
                snap_id = db.add_snapshot(args.url, image_path, img_hash, size, width, height)
                print(f"  ✅ 已保存 #{snap_id}")

                if last:
                    similarity, diff_path, pixel_diff = comparator.compare(
                        last["image_path"], image_path, mode=args.mode, ignore_regions=ignore
                    )
                    db.add_change(args.url, last["id"], snap_id, diff_path, similarity, pixel_diff)
                    print(f"  📊 相似度: {similarity:.2%}")
                    if similarity < 0.2:
                        print(f"  ⚠️  相似度极低，可能是验证码/故障页面")
                    elif similarity < 0.95:
                        print(f"  ⚠️  检测到变化! 差异图: {diff_path}")

            count += 1
            if args.count and count >= args.count:
                print(f"\n✅ 已完成 {count} 次截图")
                break

            next_time = datetime.now() + timedelta(seconds=args.interval)
            print(f"  ⏳ 下次: {next_time.strftime('%H:%M:%S')}")
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print(f"\n\n👋 共截图 {count} 次，再见")

    db.close()


def history_cmd(args):
    db = ArchiveDB(args.db)
    rows = db.get_snapshots(args.url, args.limit)

    print(f"\n📚 {args.url} 的历史记录")
    print("-" * 70)
    print(f"{'ID':<6} {'时间':<20} {'Hash':<12} {'大小':<10} {'文件'}")
    print("-" * 70)

    for row in rows:
        print(f"{row['id']:<6} {row['timestamp'][:19]:<20} "
              f"{row['image_hash'][:10]:<12} {row['file_size']/1024:.1f}KB   {row['image_path']}")

    changes = db.get_changes(args.url, 10)
    if changes:
        print(f"\n📊 最近变更:")
        for ch in changes:
            status = "🟢" if ch["similarity"] > 0.95 else "🟡" if ch["similarity"] > 0.9 else "🔴"
            print(f"  {status} {ch['detected_at'][:16]} | 相似度: {ch['similarity']:.2%} | {ch['diff_path']}")

    db.close()


def report_cmd(args):
    print("📄 正在生成报告...")
    generator = ReportGenerator(args.db)
    path = generator.generate(args.output)
    print(f"✅ 报告已保存: {path}")
    print(f"   用浏览器打开查看")


def stats_cmd(args):
    db = ArchiveDB(args.db)
    stats = db.get_stats()
    urls = db.get_all_urls()

    print("\n📊 kina-archive 统计")
    print("=" * 50)
    print(f"  总截图数: {stats['total_snapshots']}")
    print(f"  监控站点: {stats['unique_urls']}")
    print(f"  变更检测: {stats['total_changes']}")
    print("\n🌐 监控中的 URL:")
    for url in urls:
        count = db.conn.execute("SELECT COUNT(*) FROM snapshots WHERE url = ?", (url,)).fetchone()[0]
        print(f"  • {url} ({count} 张截图)")

    db.close()


def _add_common_args(parser):
    """添加通用参数到子命令"""
    parser.add_argument("--browser", "-b", choices=["chrome", "edge", "firefox"],
                        help="指定浏览器（默认自动检测）")
    parser.add_argument("--mode", "-m", choices=["pixel", "phash", "content"], default="pixel",
                        help="对比模式（默认: pixel）")
    parser.add_argument("--ignore", "-I", help="忽略区域，格式: x,y,w,h;x,y,w,h")


def main():
    parser = argparse.ArgumentParser(
        description="kina-archive: 网页时光机",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s snapshot https://kina.ink                          # 截图一次
  %(prog)s snapshot https://kina.ink --mode phash             # 感知哈希对比
  %(prog)s snapshot https://kina.ink --mode content           # 内容结构对比
  %(prog)s snapshot https://kina.ink --ignore 0,0,1920,300    # 忽略顶部背景区域
  %(prog)s watch https://kina.ink -i 3600 --mode phash        # 每小时监控
  %(prog)s history https://kina.ink -l 20                     # 查看历史
  %(prog)s report                                             # 生成 HTML 报告
  %(prog)s stats                                              # 查看统计

对比模式:
  pixel   - 像素级对比（默认，最严格）
  phash   - 感知哈希（忽略背景图变化，推荐用于动态背景站点）
  content - 内容结构对比（关注布局，忽略颜色变化）

忽略区域格式: x,y,w,h;x,y,w,h
  例: --ignore 0,0,1920,300 表示忽略顶部 300px 区域
        """
    )
    parser.add_argument("--db", "-d", default="archive.db", help="数据库路径")
    parser.add_argument("--output", "-o", default="snapshots", help="截图输出目录")

    subparsers = parser.add_subparsers(dest="command", help="命令")

    # snapshot
    snap = subparsers.add_parser("snapshot", help="单次截图")
    snap.add_argument("url", help="目标网址")
    snap.add_argument("--width", "-W", type=int, default=1920)
    snap.add_argument("--height", "-H", type=int, default=1080)
    snap.add_argument("--viewport", "-v", action="store_true", help="仅视口，不截全页")
    _add_common_args(snap)

    # watch
    watch = subparsers.add_parser("watch", help="持续监控")
    watch.add_argument("url", help="目标网址")
    watch.add_argument("--interval", "-i", type=int, default=3600, help="截图间隔(秒)")
    watch.add_argument("--count", "-c", type=int, default=0, help="截图次数(0=无限)")
    _add_common_args(watch)

    # history
    hist = subparsers.add_parser("history", help="查看历史")
    hist.add_argument("url", help="目标网址")
    hist.add_argument("--limit", "-l", type=int, default=20)

    # report
    report = subparsers.add_parser("report", help="生成 HTML 报告")
    report.add_argument("--output", "-O", default="archive_report.html", help="报告输出路径")

    # stats
    subparsers.add_parser("stats", help="查看统计")

    args = parser.parse_args()

    if not args.command:
        print_logo()
        parser.print_help()
        sys.exit(0)

    commands = {
        "snapshot": snapshot_cmd,
        "watch": watch_cmd,
        "history": history_cmd,
        "report": report_cmd,
        "stats": stats_cmd,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
