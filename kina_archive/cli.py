#!/usr/bin/env python3
import os
import sys
import time
import hashlib
import argparse
import logging
from datetime import datetime, timedelta

from .db import ArchiveDB
from .screenshot import Screenshotter
from .compare import ImageComparator
from .report import ReportGenerator

__version__ = "1.1.1"


def setup_logging(verbose=False, quiet=False):
    level = logging.DEBUG if verbose else logging.WARNING if quiet else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def print_logo():
    print("")
    print("    ========================================")
    print("         kina-archive 网页时光机")
    print("    ========================================")
    print("")


def parse_ignore_regions(regions_str):
    if not regions_str:
        return None
    regions = []
    for part in regions_str.split(";"):
        coords = []
        for c in part.split(","):
            c = c.strip()
            if c.endswith("pct"):
                coords.append(c)
            else:
                coords.append(int(c))
        if len(coords) == 4:
            regions.append(tuple(coords))
    return regions if regions else None


def snapshot_cmd(args):
    setup_logging(args.verbose, args.quiet)
    db = ArchiveDB(args.db)
    screenshotter = Screenshotter(args.output, browser=args.browser, timeout=args.timeout)
    comparator = ImageComparator(args.output)

    print("截图: " + args.url)
    logger = logging.getLogger("kina_archive.cli")
    logger.info("开始截图: " + args.url + ", mode=" + args.mode)

    image_path, width, height = screenshotter.capture(
        args.url, args.width, args.height, not args.viewport
    )

    with open(image_path, "rb") as f:
        img_hash = hashlib.md5(f.read()).hexdigest()
    size = os.path.getsize(image_path)

    last = db.get_last_snapshot(args.url)
    if last and last["image_hash"] == img_hash:
        print("  无变化，删除重复截图")
        os.remove(image_path)
        db.close()
        return

    snap_id = db.add_snapshot(args.url, image_path, img_hash, size, width, height)
    print("  已保存 #" + str(snap_id) + ": " + image_path)
    logger.info("截图已保存: #" + str(snap_id))

    if last:
        print("  对比中... [模式: " + args.mode + "]")
        ignore = parse_ignore_regions(args.ignore)
        similarity, diff_path, pixel_diff = comparator.compare(
            last["image_path"], image_path, mode=args.mode, ignore_regions=ignore
        )
        db.add_change(args.url, last["id"], snap_id, diff_path, similarity, pixel_diff)
        print("  相似度: {:.2%}".format(similarity))
        from .compare import SIMILARITY_LOW, SIMILARITY_CHANGE
        if similarity < SIMILARITY_LOW:
            print("  相似度极低，可能是验证码/故障页面")
        elif similarity < SIMILARITY_CHANGE:
            print("  检测到明显变化!")
        print("  差异图: " + diff_path)
        logger.info("对比完成: similarity=" + str(similarity) + ", diff=" + diff_path)

    db.close()


def watch_cmd(args):
    setup_logging(args.verbose, args.quiet)
    db = ArchiveDB(args.db)
    screenshotter = Screenshotter(args.output, browser=args.browser, timeout=args.timeout)
    comparator = ImageComparator(args.output)
    ignore = parse_ignore_regions(args.ignore)
    logger = logging.getLogger("kina_archive.cli")

    print("监控: " + args.url)
    print("间隔: " + str(args.interval) + "秒 | 模式: " + args.mode + " | 按 Ctrl+C 停止")
    print("")
    logger.info("开始监控: " + args.url + ", interval=" + str(args.interval) + "s, mode=" + args.mode)

    count = 0
    try:
        while True:
            print("")
            print("--- [" + datetime.now().strftime("%H:%M:%S") + "] 第 " + str(count + 1) + " 次截图 ---")

            image_path, width, height = screenshotter.capture(args.url)

            with open(image_path, "rb") as f:
                img_hash = hashlib.md5(f.read()).hexdigest()
            size = os.path.getsize(image_path)

            last = db.get_last_snapshot(args.url)
            if last and last["image_hash"] == img_hash:
                print("  无变化")
                os.remove(image_path)
            else:
                snap_id = db.add_snapshot(args.url, image_path, img_hash, size, width, height)
                print("  已保存 #" + str(snap_id))
                logger.info("监控截图已保存: #" + str(snap_id))

                if last:
                    similarity, diff_path, pixel_diff = comparator.compare(
                        last["image_path"], image_path, mode=args.mode, ignore_regions=ignore
                    )
                    db.add_change(args.url, last["id"], snap_id, diff_path, similarity, pixel_diff)
                    print("  相似度: {:.2%}".format(similarity))
                    from .compare import SIMILARITY_LOW, SIMILARITY_CHANGE
                    if similarity < SIMILARITY_LOW:
                        print("  相似度极低，可能是验证码/故障页面")
                    elif similarity < SIMILARITY_CHANGE:
                        print("  检测到变化! 差异图: " + diff_path)
                    logger.info("监控对比: similarity=" + str(similarity))

            count += 1
            if args.count and count >= args.count:
                print("")
                print("已完成 " + str(count) + " 次截图")
                logger.info("监控完成: " + str(count) + " 次截图")
                break

            next_time = datetime.now() + timedelta(seconds=args.interval)
            print("  下次: " + next_time.strftime("%H:%M:%S"))
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("")
        print("")
        print("共截图 " + str(count) + " 次，再见")
        logger.info("监控中断: 共 " + str(count) + " 次截图")

    db.close()


def history_cmd(args):
    db = ArchiveDB(args.db)
    rows = db.get_snapshots(args.url, args.limit)

    print("")
    print(args.url + " 的历史记录")
    print("-" * 70)
    print("{:<6} {:<20} {:<12} {:<10} {}".format("ID", "时间", "Hash", "大小", "文件"))
    print("-" * 70)

    for row in rows:
        print("{:<6} {:<20} {:<12} {:.1f}KB   {}".format(
            row["id"], row["timestamp"][:19], row["image_hash"][:10],
            row["file_size"]/1024, row["image_path"]))

    changes = db.get_changes(args.url, 10)
    if changes:
        print("")
        print("最近变更:")
        for ch in changes:
            status = "绿" if ch["similarity"] > 0.95 else "黄" if ch["similarity"] > 0.9 else "红"
            print("  " + status + " " + ch["detected_at"][:16] + " | 相似度: {:.2%} | {}".format(ch["similarity"], ch["diff_path"]))

    db.close()


def report_cmd(args):
    setup_logging(args.verbose, args.quiet)
    print("正在生成报告...")
    generator = ReportGenerator(args.db)
    path = generator.generate(args.output)
    print("报告已保存: " + path)
    print("用浏览器打开查看")
    print("提示: 将报告所在目录打包即可分享")


def stats_cmd(args):
    db = ArchiveDB(args.db)
    stats = db.get_stats()
    urls = db.get_all_urls()

    print("")
    print("kina-archive 统计")
    print("=" * 50)
    print("  总截图数: " + str(stats["total_snapshots"]))
    print("  监控站点: " + str(stats["unique_urls"]))
    print("  变更检测: " + str(stats["total_changes"]))
    print("")
    print("监控中的 URL:")
    for url in urls:
        count = db.conn.execute("SELECT COUNT(*) FROM snapshots WHERE url = ?", (url,)).fetchone()[0]
        print("  - " + url + " (" + str(count) + " 张截图)")

    db.close()


def _add_common_args(parser):
    parser.add_argument("--browser", "-b", choices=["chrome", "edge", "firefox"],
                        help="指定浏览器（默认自动检测）")
    parser.add_argument("--mode", "-m", choices=["pixel", "phash", "content"], default="pixel",
                        help="对比模式（默认: pixel）")
    parser.add_argument("--ignore", "-I", help="忽略区域，格式: x,y,w,h;x,y,w,h，支持百分比如 0,0,100pct,20pct")
    parser.add_argument("--timeout", "-t", type=int, default=60,
                        help="截图超时时间(秒)，默认60")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志输出")
    parser.add_argument("--quiet", "-q", action="store_true", help="静默模式，只输出错误")


def main():
    parser = argparse.ArgumentParser(
        description="kina-archive: 网页时光机 v" + __version__,
        epilog="示例: kina-archive snapshot https://kina.ink"
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    parser.add_argument("--db", "-d", default="archive.db", help="数据库路径")
    parser.add_argument("--output", "-o", default="snapshots", help="截图输出目录")

    subparsers = parser.add_subparsers(dest="command", help="命令")

    snap = subparsers.add_parser("snapshot", help="单次截图")
    snap.add_argument("url", help="目标网址")
    snap.add_argument("--width", "-W", type=int, default=1920)
    snap.add_argument("--height", "-H", type=int, default=1080)
    snap.add_argument("--viewport", "-V", action="store_true", help="仅视口，不截全页")
    _add_common_args(snap)

    watch = subparsers.add_parser("watch", help="持续监控")
    watch.add_argument("url", help="目标网址")
    watch.add_argument("--interval", "-i", type=int, default=3600, help="截图间隔(秒)")
    watch.add_argument("--count", "-c", type=int, default=0, help="截图次数(0=无限)")
    _add_common_args(watch)

    hist = subparsers.add_parser("history", help="查看历史")
    hist.add_argument("url", help="目标网址")
    hist.add_argument("--limit", "-l", type=int, default=20)

    report = subparsers.add_parser("report", help="生成 HTML 报告")
    report.add_argument("--output", "-O", default="archive_report.html", help="报告输出路径")
    report.add_argument("--verbose", "-v", action="store_true", help="详细日志输出")
    report.add_argument("--quiet", "-q", action="store_true", help="静默模式")

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
