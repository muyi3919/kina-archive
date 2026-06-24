import os
import sys
import subprocess
import platform
import logging
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timedelta

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("kina_archive.screenshot")


def _get_system_font():
    system = platform.system()
    font_paths = []
    if system == "Windows":
        font_paths = [
            "C:\\Windows\\Fonts\\msyh.ttc",
            "C:\\Windows\\Fonts\\msyhbd.ttc",
            "C:\\Windows\\Fonts\\simhei.ttf",
            "C:\\Windows\\Fonts\\simsun.ttc",
            "C:\\Windows\\Fonts\\segoeui.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
        ]
    elif system == "Darwin":
        font_paths = [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/Library/Fonts/Arial.ttf",
        ]
    else:
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        ]
    for fp in font_paths:
        if os.path.exists(fp):
            return fp
    return None


def _load_font(size=20, bold=False):
    font_path = _get_system_font()
    if font_path:
        try:
            return ImageFont.truetype(font_path, size)
        except:
            pass
    return ImageFont.load_default()


# 浏览器检测配置
BROWSER_CONFIGS = {
    "chrome": {
        "name": "Google Chrome",
        "win_paths": [
            r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
            r"C:\\Program Files\\Chromium\\Application\\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\\Google\\Chrome\\Application\\chrome.exe"),
        ],
        "mac_path": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "linux_cmds": ["chromium-browser", "chromium", "google-chrome", "chrome"],
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    },
    "edge": {
        "name": "Microsoft Edge",
        "win_paths": [
            r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
            r"C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\\Microsoft\\Edge\\Application\\msedge.exe"),
        ],
        "mac_path": "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "linux_cmds": ["microsoft-edge", "edge"],
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
    },
    "firefox": {
        "name": "Mozilla Firefox",
        "win_paths": [
            r"C:\\Program Files\\Mozilla Firefox\\firefox.exe",
            r"C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\\Mozilla Firefox\\firefox.exe"),
        ],
        "mac_path": "/Applications/Firefox.app/Contents/MacOS/firefox",
        "linux_cmds": ["firefox"],
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    },
}


def _chrome_screenshot_args(cmd, url, filepath, width, height, full_page, user_agent):
    """Chrome/Edge 截图参数"""
    args = [
        cmd,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-extensions",
        "--disable-software-rasterizer",
        "--hide-scrollbars",
        "--disable-blink-features=AutomationControlled",
        f"--user-agent={user_agent}",
        f"--window-size={width},{height}",
        f"--screenshot={filepath}",
    ]
    if full_page:
        args.append("--screenshot-full-page")
    args.append(url)
    return args


def _firefox_screenshot_args(cmd, url, filepath, width, height, full_page, user_agent):
    """Firefox 截图参数"""
    args = [
        cmd,
        "--headless",
        f"--window-size={width},{height}",
        f"--screenshot={filepath}",
    ]
    if full_page:
        # Firefox 不支持 --screenshot-full-page，用 --window-size 模拟
        pass
    args.append(url)
    return args


BROWSER_SCREENSHOT_BUILDERS = {
    "chrome": _chrome_screenshot_args,
    "edge": _chrome_screenshot_args,
    "firefox": _firefox_screenshot_args,
}


class Screenshotter:
    def __init__(self, output_dir: str = "snapshots", browser: str = None, timeout: int = 60):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.system = platform.system()
        self.browser_info = self._detect_browser(browser)
        self.chrome_cmd = self.browser_info["cmd"] if self.browser_info else None
        self.timeout = timeout
        logger.info(f"Screenshotter initialized, browser={self.browser_info['key'] if self.browser_info else None}, timeout={timeout}s")

    def _detect_browser(self, preferred: str = None) -> dict:
        """检测可用浏览器，支持指定优先级"""
        system = self.system

        if preferred and preferred in BROWSER_CONFIGS:
            result = self._try_browser(preferred, BROWSER_CONFIGS[preferred])
            if result:
                return result
            logger.warning(f"指定的浏览器 {preferred} 未找到，尝试其他浏览器...")
            print(f"⚠️  指定的浏览器 {preferred} 未找到，尝试其他浏览器...")

        for key, config in BROWSER_CONFIGS.items():
            if preferred and key == preferred:
                continue
            result = self._try_browser(key, config)
            if result:
                return result

        logger.error("未检测到任何支持的浏览器")
        print("⚠️  未检测到任何支持的浏览器")
        print("   请安装以下浏览器之一:")
        print("   • Google Chrome / Chromium")
        print("   • Microsoft Edge")
        print("   • Mozilla Firefox")
        print("   安装后确保已添加到系统 PATH")
        return None

    def _try_browser(self, key: str, config: dict) -> dict:
        """尝试检测单个浏览器"""
        system = self.system

        if system == "Windows":
            for p in config["win_paths"]:
                if os.path.exists(p):
                    logger.info(f"检测到 {config['name']}: {p}")
                    print(f"✅ 检测到 {config['name']}: {p}")
                    return {"key": key, "cmd": p, "config": config}
            for cmd in [key] + config.get("win_cmds", []):
                try:
                    result = subprocess.run(
                        [cmd, "--version"], capture_output=True, text=True,
                        timeout=5, shell=True, encoding="utf-8", errors="ignore"
                    )
                    if result.returncode == 0:
                        logger.info(f"检测到 {config['name']}: {result.stdout.strip()}")
                        print(f"✅ 检测到 {config['name']}: {result.stdout.strip()}")
                        return {"key": key, "cmd": cmd, "config": config}
                except:
                    pass

        elif system == "Darwin":
            if os.path.exists(config["mac_path"]):
                logger.info(f"检测到 {config['name']}: {config['mac_path']}")
                print(f"✅ 检测到 {config['name']}: {config['mac_path']}")
                return {"key": key, "cmd": config["mac_path"], "config": config}

        for cmd in config["linux_cmds"]:
            try:
                result = subprocess.run(
                    [cmd, "--version"], capture_output=True, text=True,
                    timeout=5, encoding="utf-8", errors="ignore"
                )
                if result.returncode == 0:
                    logger.info(f"检测到 {config['name']}: {result.stdout.strip()}")
                    print(f"✅ 检测到 {config['name']}: {result.stdout.strip()}")
                    return {"key": key, "cmd": cmd, "config": config}
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

        return None

    def capture(self, url: str, width: int = 1920, height: int = 1080,
                full_page: bool = True) -> tuple:
        """截图并返回 (路径, 宽, 高)"""
        domain = urlparse(url).netloc.replace(".", "_").replace(":", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{domain}_{timestamp}.png"
        filepath = self.output_dir / filename
        filepath_abs = str(filepath.resolve())

        if self.browser_info:
            success = self._browser_screenshot(url, filepath_abs, width, height, full_page)
            if not success:
                logger.warning("浏览器截图失败，使用备用方案")
                print("⚠️  浏览器截图失败，使用备用方案")
                self._fallback_screenshot(url, filepath)
        else:
            logger.warning("无可用浏览器，使用备用方案")
            print("⚠️  无可用浏览器，使用备用方案")
            self._fallback_screenshot(url, filepath)

        if not filepath.exists():
            logger.error("截图未生成，使用备用方案")
            print("⚠️  截图未生成，使用备用方案")
            self._fallback_screenshot(url, filepath)

        with Image.open(filepath) as img:
            img_width, img_height = img.size
        return str(filepath), img_width, img_height

    def _browser_screenshot(self, url: str, filepath: str,
                            width: int, height: int, full_page: bool) -> bool:
        """使用浏览器 headless 截图，返回是否成功"""
        key = self.browser_info["key"]
        cmd_path = self.browser_info["cmd"]
        user_agent = self.browser_info["config"]["user_agent"]

        # 使用浏览器特定的截图参数构建器
        builder = BROWSER_SCREENSHOT_BUILDERS[key]
        cmd = builder(cmd_path, url, filepath, width, height, full_page, user_agent)

        shell = False
        logger.info(f"执行截图命令: {cmd[0]} ...")

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.timeout,
                shell=shell, encoding="utf-8", errors="ignore"
            )
            if result.returncode != 0 and result.stderr:
                err = result.stderr.strip()
                if err:
                    logger.warning(f"浏览器警告: {err[:200]}")
                    print(f"⚠️  浏览器警告: {err[:200]}")
            return os.path.exists(filepath) and os.path.getsize(filepath) > 1000
        except subprocess.TimeoutExpired:
            logger.error(f"截图超时 ({self.timeout}s)，强制终止")
            print(f"⚠️  截图超时 ({self.timeout}s)，强制终止")
            return False
        except Exception as e:
            logger.error(f"截图失败: {e}")
            print(f"❌ 截图失败: {e}")
            return False

    def _fallback_screenshot(self, url: str, filepath: Path):
        """备用截图"""
        img = Image.new("RGB", (1920, 1080), color=(26, 26, 46))
        draw = ImageDraw.Draw(img)

        font_large = _load_font(60, bold=True)
        font_mid = _load_font(32)
        font_small = _load_font(20)

        draw.text((100, 200), "kina-archive", fill=(233, 69, 96), font=font_large)
        draw.text((100, 300), f"URL: {url}", fill=(200, 200, 200), font=font_mid)

        if self.browser_info:
            draw.text((100, 360), "Browser screenshot failed", fill=(255, 100, 100), font=font_mid)
        else:
            draw.text((100, 360), "No browser detected", fill=(255, 100, 100), font=font_mid)

        hints = [
            "Install one of the following browsers:",
            "• Google Chrome / Chromium",
            "• Microsoft Edge",
            "• Mozilla Firefox",
        ]
        y = 420
        for hint in hints:
            draw.text((100, y), hint, fill=(150, 150, 150), font=font_small)
            y += 30

        draw.line([(100, 560), (900, 560)], fill=(15, 52, 96), width=2)
        img.save(filepath)
        logger.info(f"备用截图已保存: {filepath}")

    def cleanup_old(self, days: int = 30):
        """清理旧截图"""
        cutoff = datetime.now() - timedelta(days=days)
        count = 0
        for f in self.output_dir.glob("*.png"):
            if f.stat().st_mtime < cutoff.timestamp():
                f.unlink()
                count += 1
        logger.info(f"清理了 {count} 个旧截图")
        return count
