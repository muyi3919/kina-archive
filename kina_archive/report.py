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
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:#f4f2f7;color:#1c1b26;line-height:1.6;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:1.5rem}}
.container{{max-width:1440px;width:100%;background:rgba(255,255,255,0.72);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);border-radius:2.8rem;padding:2rem 2.4rem 2.5rem;box-shadow:0 20px 48px -12px rgba(0,0,0,0.08),0 0 0 1px rgba(255,255,255,0.6);border:1px solid rgba(255,255,255,0.5);transition:all 0.2s ease}}
header{{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;padding-bottom:1.6rem;border-bottom:1px solid rgba(0,0,0,0.04);margin-bottom:2rem}}
.brand{{display:flex;align-items:center;gap:0.6rem}}
.brand i{{font-size:2.2rem;background:linear-gradient(145deg,#f472b6,#e94560);-webkit-background-clip:text;-webkit-text-fill-color:transparent;filter:drop-shadow(0 0 10px rgba(233,69,96,0.15))}}
.brand h1{{font-weight:600;font-size:1.9rem;letter-spacing:-0.02em;color:#1b1b2a;background:none;-webkit-text-fill-color:#1b1b2a}}
.brand span{{font-weight:300;color:#6b6b82;font-size:0.9rem;margin-left:0.2rem}}
.header-meta{{display:flex;align-items:center;gap:0.6rem;font-size:0.85rem;color:#3e3e56;background:rgba(0,0,0,0.02);padding:0.3rem 1.2rem 0.3rem 1rem;border-radius:40px;border:1px solid rgba(0,0,0,0.03);backdrop-filter:blur(4px)}}
.header-meta i{{color:#e94560}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1rem;margin-bottom:2.2rem}}
.stat-card{{background:rgba(255,255,255,0.6);backdrop-filter:blur(4px);padding:1.25rem 0.8rem;border-radius:2rem;text-align:center;border:1px solid rgba(255,255,255,0.8);box-shadow:0 8px 20px -8px rgba(0,0,0,0.02);transition:transform 0.15s ease,border-color 0.2s,box-shadow 0.2s}}
.stat-card:hover{{transform:translateY(-3px);border-color:rgba(233,69,96,0.15);box-shadow:0 12px 28px -8px rgba(233,69,96,0.05)}}
.stat-card .number{{font-size:2.3rem;font-weight:600;background:linear-gradient(145deg,#e94560,#f472b6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:-0.01em}}
.stat-card .label{{color:#4a4a62;font-size:0.8rem;letter-spacing:0.02em;margin-top:0.2rem;display:flex;align-items:center;justify-content:center;gap:0.3rem}}
.stat-card .label i{{font-size:0.7rem;color:#a0a0b8}}
.url-section{{background:rgba(255,255,255,0.4);backdrop-filter:blur(8px);border-radius:2.2rem;overflow:hidden;margin:1.8rem 0 1.8rem;border:1px solid rgba(255,255,255,0.7);box-shadow:0 10px 30px -12px rgba(0,0,0,0.02)}}
.url-header{{padding:1rem 1.8rem;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.6rem;background:rgba(255,255,255,0.3);border-bottom:1px solid rgba(0,0,0,0.02)}}
.url-header h2{{font-weight:500;font-size:1.1rem;color:#181826;display:flex;align-items:center;gap:0.6rem}}
.url-header h2 i{{color:#e94560;font-size:1rem;opacity:0.8}}
.url-header .badge{{background:rgba(233,69,96,0.06);color:#b13e5a;font-weight:400;padding:0.2rem 1.2rem;border-radius:30px;font-size:0.75rem;border:1px solid rgba(233,69,96,0.05);letter-spacing:0.02em}}
.timeline{{display:flex;gap:1.8rem;padding:1.8rem 1.8rem 2rem;overflow-x:auto;scroll-snap-type:x mandatory;scroll-behavior:smooth}}
.timeline::-webkit-scrollbar{{height:4px;background:transparent}}
.timeline::-webkit-scrollbar-thumb{{background:rgba(233,69,96,0.2);border-radius:20px}}
.snapshot{{flex-shrink:0;width:250px;scroll-snap-align:start;background:rgba(255,255,255,0.7);border-radius:1.8rem;padding:0.8rem 0.8rem 1rem;backdrop-filter:blur(4px);border:1px solid rgba(255,255,255,0.9);box-shadow:0 6px 18px -6px rgba(0,0,0,0.02);transition:all 0.2s}}
.snapshot:hover{{border-color:rgba(233,69,96,0.15);background:rgba(255,255,255,0.85);transform:scale(1.01);box-shadow:0 12px 28px -8px rgba(0,0,0,0.04)}}
.snapshot img{{width:100%;border-radius:1.2rem;border:1px solid rgba(255,255,255,0.3);transition:border 0.2s;display:block;aspect-ratio:16/10;object-fit:cover;background:#f0edf5}}
.snapshot .meta{{margin-top:0.7rem;display:flex;justify-content:space-between;align-items:center;font-size:0.75rem;color:#4a4a62}}
.snapshot .meta .date{{display:flex;align-items:center;gap:0.3rem}}
.snapshot .meta .date i{{font-size:0.65rem;color:#8f8fa8}}
.snapshot .hash{{font-family:'SF Mono','Fira Code',monospace;font-size:0.65rem;color:#7a7a92;background:rgba(0,0,0,0.02);padding:0.1rem 0.6rem;border-radius:30px;letter-spacing:0.02em;border:1px solid rgba(0,0,0,0.02)}}
.changes{{padding:0.2rem 1.8rem 2rem}}
.change-item{{display:flex;align-items:center;gap:1.2rem;padding:0.7rem 1.2rem;margin:0.6rem 0;background:rgba(255,255,255,0.5);border-radius:2rem;backdrop-filter:blur(2px);border:1px solid rgba(255,255,255,0.6);transition:background 0.15s,box-shadow 0.15s;box-shadow:0 2px 8px -4px rgba(0,0,0,0.01)}}
.change-item:hover{{background:rgba(255,255,255,0.75);box-shadow:0 6px 16px -6px rgba(0,0,0,0.02)}}
.change-item .sim{{font-weight:500;padding:0.2rem 0.9rem;border-radius:40px;font-size:0.8rem;letter-spacing:0.01em;flex-shrink:0}}
.sim-high{{background:rgba(34,197,94,0.08);color:#1f8b4c;border:1px solid rgba(34,197,94,0.06)}}
.sim-mid{{background:rgba(234,179,8,0.08);color:#a57c0e;border:1px solid rgba(234,179,8,0.06)}}
.sim-low{{background:rgba(239,68,68,0.06);color:#b91c1c;border:1px solid rgba(239,68,68,0.04)}}
.change-item .diff-thumb{{width:100px;height:68px;object-fit:cover;border-radius:1rem;border:1px solid rgba(255,255,255,0.4);background:#f0edf5;flex-shrink:0}}
.change-item .change-text{{font-size:0.9rem;color:#1c1b2a;display:flex;align-items:center;gap:0.4rem;flex-wrap:wrap}}
.change-item .change-text i{{color:#e94560;font-size:0.8rem;opacity:0.6}}
.change-item .change-text .muted{{color:#6b6b82;font-size:0.8rem}}
footer{{margin-top:2.5rem;text-align:center;color:#5a5a78;font-size:0.8rem;border-top:1px solid rgba(0,0,0,0.03);padding-top:1.8rem;display:flex;justify-content:space-between;flex-wrap:wrap;gap:0.5rem}}
footer a{{color:#1c1b26;text-decoration:none;border-bottom:1px dotted rgba(233,69,96,0.15);transition:color 0.15s;font-weight:500}}
footer a:hover{{color:#e94560;border-bottom-color:#e94560}}
@media(max-width:640px){{.container{{padding:1.2rem;border-radius:2rem}}.brand h1{{font-size:1.5rem}}.header-meta{{font-size:0.7rem;padding:0.2rem 0.8rem}}.stats{{grid-template-columns:repeat(2,1fr);gap:0.6rem}}.stat-card .number{{font-size:1.8rem}}.snapshot{{width:200px}}.change-item{{flex-wrap:wrap;gap:0.6rem}}.change-item .diff-thumb{{width:100%;height:auto;max-height:80px}}.url-header h2{{font-size:0.95rem}}
@media(max-width:400px){{.stats{{grid-template-columns:1fr}}
</style>
<style>
/* 图片点击放大 */
.lightbox-overlay{{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);display:none;align-items:center;justify-content:center;z-index:9999;cursor:zoom-out;backdrop-filter:blur(8px)}}
.lightbox-overlay.active{{display:flex}}
.lightbox-overlay img{{max-width:90%;max-height:90%;border-radius:12px;box-shadow:0 20px 60px rgba(0,0,0,0.4);object-fit:contain}}
.lightbox-close{{position:absolute;top:20px;right:30px;color:#fff;font-size:2rem;cursor:pointer;opacity:0.7;transition:opacity 0.2s}}
.lightbox-close:hover{{opacity:1}}
.snapshot img,.change-item .diff-thumb{{cursor:zoom-in;transition:transform 0.2s}}
.snapshot img:hover,.change-item .diff-thumb:hover{{transform:scale(1.02)}}
</style>
<script>
document.addEventListener('DOMContentLoaded',function(){{
  var overlay=document.createElement('div');
  overlay.className='lightbox-overlay';
  overlay.innerHTML='<span class="lightbox-close">&times;</span><img src="" alt="">';
  document.body.appendChild(overlay);
  var lbImg=overlay.querySelector('img');
  var lbClose=overlay.querySelector('.lightbox-close');
  function open(src){{lbImg.src=src;overlay.classList.add('active');}}
  function close(){{overlay.classList.remove('active');lbImg.src='';}}
  overlay.addEventListener('click',close);
  lbClose.addEventListener('click',function(e){{e.stopPropagation();close();}});
  document.addEventListener('keydown',function(e){{if(e.key==='Escape')close();}});
  document.querySelectorAll('.snapshot img,.change-item .diff-thumb').forEach(function(img){{
    img.addEventListener('click',function(e){{e.stopPropagation();open(this.src);}});
  }});
}});
</script>
</head>
<body>
<div class="container">
<header>
<div class="brand">
<i class="fas fa-clock"></i>
<h1>kina-archive</h1>
<span>· 时光机</span>
</div>
<div class="header-meta">
<i class="fas fa-sync-alt fa-fw"></i>
<span>实时追踪</span>
<span style="opacity:0.2;">|</span>
<i class="fas fa-code-branch"></i>
<span>v1.1.3</span>
</div>
</header>
{stats_html}
{content_html}
<footer>
<span><i class="far fa-copyright"></i> 2026 kina-archive</span>
<span><i class="fas fa-code"></i> 由 <a href="https://github.com/muyi3919" target="_blank">kina漫记</a> 驱动</span>
<span><i class="far fa-calendar-alt"></i> 生成: {generated_at}</span>
</footer>
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
<div class="stat-card"><div class="number">{snapshots}</div><div class="label"><i class="far fa-file-image"></i> 快照总数</div></div>
<div class="stat-card"><div class="number">{urls}</div><div class="label"><i class="far fa-eye"></i> 监控站点</div></div>
<div class="stat-card"><div class="number">{changes}</div><div class="label"><i class="fas fa-chart-line"></i> 检测到变更</div></div>
</div>""".format(**stats)

    def _render_url_section(self, conn, url: str, assets_dir: Path) -> str:
        snapshots = conn.execute(
            "SELECT * FROM snapshots WHERE url = ? ORDER BY timestamp DESC LIMIT 15", (url,)
        ).fetchall()
        snap_count = conn.execute("SELECT COUNT(*) FROM snapshots WHERE url = ?", (url,)).fetchone()[0]

        timeline = '<div class="timeline">'
        for snap in snapshots:
            ip = snap["image_path"]
            img_name = f"snap_{snap['id']}_{Path(ip).name}"
            dest = assets_dir / img_name
            try:
                if os.path.exists(ip):
                    shutil.copy2(ip, dest)
                rel_path = f"report_assets/{img_name}"
            except Exception as e:
                logger.warning(f"复制图片失败 {ip}: {e}")
                rel_path = ip

            ts = snap["timestamp"][:16]
            ih = snap["image_hash"][:8]
            timeline += f'<div class="snapshot"><img src="{rel_path}" loading="lazy" alt="快照"><div class="meta"><span class="date"><i class="far fa-clock"></i> {ts}</span><span class="hash">{ih}...</span></div></div>'
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
                ch_html += f'<div class="change-item"><span class="sim {cls}">{sim:.1%}</span><img class="diff-thumb" src="{dp_rel}" loading="lazy" alt="diff"><div class="change-text"><i class="fas fa-arrow-right"></i> <span class="muted">{da}</span></div></div>'
        else:
            ch_html += '<p style="color:#6b6b82;padding:10px">暂无变更记录</p>'
        ch_html += '</div>'

        return f'<div class="url-section"><div class="url-header"><h2><i class="fas fa-link"></i> {url}</h2><span class="badge"><i class="far fa-calendar-alt"></i> {snap_count} 张截图</span></div>{timeline}{ch_html}</div>'
