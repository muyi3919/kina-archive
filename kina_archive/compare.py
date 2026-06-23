import os
import hashlib
from pathlib import Path
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont


def _load_font(size=20, bold=False):
    import platform
    font_paths = []
    system = platform.system()
    if system == "Windows":
        font_paths = [
            "C:\\Windows\\Fonts\\msyh.ttc",
            "C:\\Windows\\Fonts\\msyhbd.ttc",
            "C:\\Windows\\Fonts\\simhei.ttf",
            "C:\\Windows\\Fonts\\segoeui.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
        ]
    elif system == "Darwin":
        font_paths = [
            "/System/Library/Fonts/PingFang.ttc",
            "/Library/Fonts/Arial.ttf",
        ]
    else:
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except:
                pass
    return ImageFont.load_default()


class ImageComparator:
    """图片对比器，支持多种对比模式"""

    def __init__(self, output_dir: str = "snapshots"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def compare(self, img1_path: str, img2_path: str, mode: str = "pixel",
                ignore_regions: list = None) -> tuple:
        """
        对比两张图片

        Args:
            img1_path: 旧图路径
            img2_path: 新图路径
            mode: 对比模式 - "pixel"(像素级) / "phash"(感知哈希) / "content"(内容结构)
            ignore_regions: 忽略区域列表 [(x, y, w, h), ...]

        Returns:
            (similarity, diff_path, pixel_diff_count)
        """
        if mode == "phash":
            return self._compare_phash(img1_path, img2_path)
        elif mode == "content":
            return self._compare_content(img1_path, img2_path, ignore_regions)
        else:
            return self._compare_pixel(img1_path, img2_path, ignore_regions)

    def _compare_pixel(self, img1_path: str, img2_path: str, ignore_regions: list = None) -> tuple:
        """像素级对比"""
        img1 = Image.open(img1_path).convert("RGB")
        img2 = Image.open(img2_path).convert("RGB")

        size = (min(img1.width, img2.width), min(img1.height, img2.height))
        img1 = img1.resize(size, Image.LANCZOS)
        img2 = img2.resize(size, Image.LANCZOS)

        diff = Image.new("RGB", size)
        px1 = img1.load()
        px2 = img2.load()
        pxd = diff.load()

        diff_count = 0
        total = size[0] * size[1]
        threshold = 30

        # 构建忽略区域掩码
        ignore_mask = set()
        if ignore_regions:
            for (x, y, w, h) in ignore_regions:
                for ix in range(x, min(x + w, size[0])):
                    for iy in range(y, min(y + h, size[1])):
                        ignore_mask.add((ix, iy))

        for y in range(size[1]):
            for x in range(size[0]):
                if (x, y) in ignore_mask:
                    pxd[x, y] = (50, 50, 80)  # 忽略区域标记为深蓝灰
                    continue

                p1 = px1[x, y]
                p2 = px2[x, y]
                distance = sum((a - b) ** 2 for a, b in zip(p1, p2)) ** 0.5

                if distance > threshold:
                    pxd[x, y] = (255, 50, 50)
                    diff_count += 1
                else:
                    gray = sum((a + b) // 4 for a, b in zip(p1, p2))
                    pxd[x, y] = (gray, gray, gray)

        # 有效像素数（排除忽略区域）
        valid_pixels = total - len(ignore_mask)
        similarity = max(0, 1 - (diff_count / valid_pixels)) if valid_pixels > 0 else 1.0

        diff = self._add_overlay(diff, similarity, diff_count, size, mode="像素级")
        diff_path = self._save_diff(diff, img1_path, img2_path)

        return similarity, diff_path, diff_count

    def _compare_phash(self, img1_path: str, img2_path: str) -> tuple:
        """感知哈希对比（忽略细微视觉差异）"""
        img1 = Image.open(img1_path).convert("L")
        img2 = Image.open(img2_path).convert("L")

        # 缩放到 32x32 计算感知哈希
        size = (32, 32)
        img1 = img1.resize(size, Image.LANCZOS)
        img2 = img2.resize(size, Image.LANCZOS)

        # 计算平均灰度
        pixels1 = list(img1.getdata())
        pixels2 = list(img2.getdata())

        avg1 = sum(pixels1) / len(pixels1)
        avg2 = sum(pixels2) / len(pixels2)

        # 生成哈希
        hash1 = "".join("1" if p > avg1 else "0" for p in pixels1)
        hash2 = "".join("1" if p > avg2 else "0" for p in pixels2)

        # 计算汉明距离
        hamming = sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
        max_bits = len(hash1)
        similarity = max(0, 1 - (hamming / max_bits))

        # 生成可视化差异图（基于原始尺寸）
        orig1 = Image.open(img1_path).convert("RGB")
        orig2 = Image.open(img2_path).convert("RGB")
        size_orig = (min(orig1.width, orig2.width), min(orig1.height, orig2.height))
        orig1 = orig1.resize(size_orig, Image.LANCZOS)
        orig2 = orig2.resize(size_orig, Image.LANCZOS)

        diff = Image.blend(orig1, orig2, alpha=0.5)
        diff = self._add_overlay(diff, similarity, hamming, size_orig, mode="感知哈希")
        diff_path = self._save_diff(diff, img1_path, img2_path)

        return similarity, diff_path, hamming

    def _compare_content(self, img1_path: str, img2_path: str, ignore_regions: list = None) -> tuple:
        """内容结构对比（忽略背景/颜色变化，关注布局结构）"""
        img1 = Image.open(img1_path).convert("L")
        img2 = Image.open(img2_path).convert("L")

        size = (min(img1.width, img2.width), min(img1.height, img2.height))
        img1 = img1.resize(size, Image.LANCZOS)
        img2 = img2.resize(size, Image.LANCZOS)

        # 使用边缘检测（简化版：相邻像素差异）
        px1 = img1.load()
        px2 = img2.load()

        diff_count = 0
        total = (size[0] - 1) * (size[1] - 1)
        threshold = 20

        # 构建忽略区域掩码
        ignore_mask = set()
        if ignore_regions:
            for (x, y, w, h) in ignore_regions:
                for ix in range(x, min(x + w, size[0])):
                    for iy in range(y, min(y + h, size[1])):
                        ignore_mask.add((ix, iy))

        for y in range(size[1] - 1):
            for x in range(size[0] - 1):
                if (x, y) in ignore_mask:
                    continue

                # 计算梯度（边缘强度）
                grad1 = abs(px1[x, y] - px1[x + 1, y]) + abs(px1[x, y] - px1[x, y + 1])
                grad2 = abs(px2[x, y] - px2[x + 1, y]) + abs(px2[x, y] - px2[x, y + 1])

                if abs(grad1 - grad2) > threshold:
                    diff_count += 1

        valid_pixels = total - len(ignore_mask)
        similarity = max(0, 1 - (diff_count / valid_pixels)) if valid_pixels > 0 else 1.0

        # 生成可视化
        orig1 = Image.open(img1_path).convert("RGB")
        orig2 = Image.open(img2_path).convert("RGB")
        orig1 = orig1.resize(size, Image.LANCZOS)
        orig2 = orig2.resize(size, Image.LANCZOS)

        diff = Image.blend(orig1, orig2, alpha=0.5)
        diff = self._add_overlay(diff, similarity, diff_count, size, mode="内容结构")
        diff_path = self._save_diff(diff, img1_path, img2_path)

        return similarity, diff_path, diff_count

    def _add_overlay(self, img: Image, similarity: float, diff_count: int, 
                     size: tuple, mode: str = "像素级") -> Image:
        """添加信息覆盖层"""
        overlay = ImageDraw.Draw(img)
        font = _load_font(24, bold=True)
        font_small = _load_font(16)

        # 背景条
        overlay.rectangle([0, 0, size[0], 60], fill=(0, 0, 0))

        # 相似度颜色
        if similarity > 0.95:
            sim_color = (100, 255, 100)
        elif similarity > 0.9:
            sim_color = (255, 200, 100)
        elif similarity > 0.5:
            sim_color = (255, 100, 100)
        else:
            sim_color = (255, 50, 50)

        overlay.text((10, 8), f"相似度: {similarity:.2%}", fill=sim_color, font=font)
        overlay.text((250, 8), f"差异: {diff_count}", fill=(255, 255, 255), font=font)
        overlay.text((450, 8), f"模式: {mode}", fill=(200, 200, 200), font=font_small)
        overlay.text((650, 8), f"分辨率: {size[0]}x{size[1]}", fill=(200, 200, 200), font=font_small)

        # 极低相似度警告
        if similarity < 0.2:
            overlay.rectangle([0, 60, size[0], 110], fill=(80, 0, 0))
            warning_font = _load_font(20, bold=True)
            overlay.text((10, 65), "⚠️  相似度极低，可能是验证码/故障页面", fill=(255, 100, 100), font=warning_font)

        return img

    def _save_diff(self, diff_img: Image, img1_path: str, img2_path: str) -> str:
        """保存差异图到固定位置，避免不同终端路径问题"""
        # 使用两个图片的哈希生成固定文件名
        hash_input = f"{img1_path}|{img2_path}|{datetime.now().strftime('%Y%m%d')}"
        name_hash = hashlib.md5(hash_input.encode()).hexdigest()[:12]
        diff_name = f"diff_{name_hash}.png"
        diff_path = str(self.output_dir / diff_name)
        diff_img.save(diff_path)
        return diff_path
