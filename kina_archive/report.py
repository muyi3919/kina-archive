import sqlite3
import os
import shutil
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("kina_archive.report")


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>kina-archive | 网页时光机</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#0f0f1a;color:#e0e0e0;line-height:1.6}}
.container{{max-width:1400px;margin:0 auto;padding:20px}}
header{{text-align:center;padding:40px 0;border-bottom:1px solid #1a1a2e}}
header h1{{font-size:2.5em;background:linear-gradient(135deg,#e94560,#ff6b6b);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:10px}}
header p{{color:#888}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:20px;margin:30px 0}}
.stat-card{{background:#16213e;padding:25px;border-radius:12px;text-align:center;border:1px solid #1a1a2e}}
.stat-card .number{{font-size:2.5em;font-weight:bold;color:#e94560}}
.stat-card .label{{color:#888;font-size:.9em;margin-top:5px}}
.url-section{{background:#16213e;border-radius:12px;margin:25px 0;overflow:hidden;border:1px solid #1a1a2e}}
.url-header{{padding:20px 25px;background:#1a1a2e;display:flex;justify-content:space-between;align-items:center}}
.url-header h2{{color:#e94560;font-size:1.1em;word-break:break-all}}
.url-header .badge{{background:#0f3460;color:#4fbdba;padding:4px 12px;border-radius:20px;font-size:.8em}}
.timeline{{display:flex;gap:15px;padding:20px;overflow-x:auto;scroll-snap-type:x mandatory}}
.snapshot{{flex-shrink:0;width:280px;scroll-snap-align:start}}
.snapshot img{{width:100%;border-radius:8px;border:2px solid #1a1a2e;transition:border-color .2s}}
.snapshot img:hover{{border-color:#e94560}}
.snapshot .meta{{margin-top:10px;font-size:.85em;color:#888}}
.snapshot .hash{{font-family:monospace;font-size:.75em;color:#555}}
.changes{{padding:0 20px 20px}}
.change-item{{display:flex;align-items:center;gap:15px;padding:12px;margin:8px 0;background:#1a1a2e;border-radius:8px}}
.change-item .sim{{font-weight:bold;padding:4px 12px;border-radius:6px;font-size:.9em}}
.sim-high{{background:#1a472a;color:#4ade80}}
.sim-mid{{background:#78350f;color:#fbbf24}}
.sim-low{{background:#7f1d1d;color:#f87171}}
.change-item .diff-thumb{{width:120px;height:80px;object-fit:cover;border-radius:4px}}
footer{{text-align:center;padding:40px;color:#555;font-size:.9em}}
footer a{{color:#e94560;text-decoration:none}}
@media(max-width:768px){{.snapshot{{width:220px}}header h1{{font-size:1.8em}}}}
</style>
</head>
<body>
<div class="container">
<header><h1>🕐 kina-archive</h1><p>网页时光机 · 视觉变更追踪</p></header>
{stats_html}
{content_html}
<footer><p>生成时间: {generated_at} | <a href="https://github.com/muyi3919">kina漫记</a></p></footer>
</div>
</body>
</html>"""


class ReportGenerator:
    def __init__(self, db_path: str = "archive.db"):
        self.db_path = db_path

    def generate(self, output_path: str = "archive_report.html"):
        output_path = Path(output_path)
        output_dir = output_path.parent or Path(".")
        output_dir.mkdir(parents=True, exist_ok=True)

        # 创建报告资源目录
        assets_dir = output_dir / "report_assets"
        assets_dir.mkdir(exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        stats = self._get_stats(conn)
        stats_html = self._render_stats(stats)

        urls = conn.execute("SELECT DISTINCT url FROM snapshots ORDER BY url").fetchall()
        content_html = ""
        for (url,) in urls:
            content_html += self._render_url_section(conn, url, assets_dir)

        conn.close()

        html = HTML_TEMPLATE.format(
            stats_html=stats_html,
            content_html=content_html,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"报告已生成: {output_path}")
        return str(output_path)

    def _get_stats(self, conn) -> dict:
        snap = conn.execute("SELECT COUNT(*) as total, COUNT(DISTINCT url) as urls FROM snapshots").fetchone()
        ch = conn.execute("SELECT COUNT(*) as total FROM changes").fetchone()
        return {"snapshots": snap["total"], "urls": snap["urls"], "changes": ch["total"]}

    def _render_stats(self, stats: dict) -> str:
        return """<div class="stats">
<div class="stat-card"><div class="number">{snapshots}</div><div class="label">总截图数</div></div>
<div class="stat-card"><div class="number">{urls}</div><div class="label">监控站点</div></div>
<div class="stat-card"><div class="number">{changes}</div><div class="label">检测到变更</div></div>
</div>""".format(**stats)

    def _render_url_section(self, conn, url: str, assets_dir: Path) -> str:
        snapshots = conn.execute(
            "SELECT * FROM snapshots WHERE url = ? ORDER BY timestamp DESC LIMIT 15", (url,)
        ).fetchall()
        snap_count = conn.execute("SELECT COUNT(*) FROM snapshots WHERE url = ?", (url,)).fetchone()[0]

        timeline = '<div class="timeline">'
        for snap in snapshots:
            ip = snap["image_path"]
            # 复制图片到报告资源目录，使用相对路径
            img_name = f"snap_{snap['id']}_{Path(ip).name}"
            dest = assets_dir / img_name
            try:
                if os.path.exists(ip):
                    shutil.copy2(ip, dest)
                rel_path = f"report_assets/{img_name}"
            except Exception as e:
                logger.warning(f"复制图片失败 {ip}: {e}")
                rel_path = ip  # fallback 到原始路径

            ts = snap["timestamp"][:16]
            ih = snap["image_hash"][:8]
            timeline += '<div class="snapshot"><img src="{}" loading="lazy"><div class="meta">{}</div><div class="hash">{}...</div></div>'.format(rel_path, ts, ih)
        timeline += '</div>'

        changes = conn.execute("""SELECT c.*,s1.image_path as old_path,s2.image_path as new_path
            FROM changes c LEFT JOIN snapshots s1 ON c.old_snapshot_id=s1.id
            LEFT JOIN snapshots s2 ON c.new_snapshot_id=s2.id WHERE c.url=? ORDER BY c.detected_at DESC LIMIT 5""", (url,)).fetchall()

        ch_html = '<div class="changes">'
        if changes:
            for ch in changes:
                cls = "sim-high" if ch["similarity"] > 0.95 else "sim-mid" if ch["similarity"] > 0.9 else "sim-low"
                sim = ch["similarity"]
                dp = ch["diff_path"]
                # 复制 diff 图
                diff_name = f"diff_{ch['id']}_{Path(dp).name}" if dp else ""
                if dp and os.path.exists(dp):
                    try:
                        shutil.copy2(dp, assets_dir / diff_name)
                        dp_rel = f"report_assets/{diff_name}"
                    except Exception as e:
                        logger.warning(f"复制 diff 图失败 {dp}: {e}")
                        dp_rel = dp
                else:
                    dp_rel = dp
                da = ch["detected_at"][:16]
                ch_html += '<div class="change-item"><span class="sim {}">{:.1%}</span><img class="diff-thumb" src="{}" loading="lazy"><span>{}</span></div>'.format(cls, sim, dp_rel, da)
        else:
            ch_html += '<p style="color:#555;padding:10px">暂无变更记录</p>'
        ch_html += '</div>'

        return '<div class="url-section"><div class="url-header"><h2>{}</h2><span class="badge">{} 张截图</span></div>{}</div>'.format(url, snap_count, timeline + ch_html)
