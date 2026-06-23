# 🕐 kina-archive

> 网页时光机 - 截图、对比、追踪、回溯
>
> 定期对网页截图，自动检测视觉变化，生成时间轴对比报告。

[![Version](https://img.shields.io/badge/version-1.0.0-blue)](https://github.com/muyi3919/kina-archive)
[![License](https://img.shields.io/badge/license-MIT-green)](https://github.com/muyi3919/kina-archive/blob/main/LICENSE)

---

## 目录

- [功能特性](#功能特性)
- [安装部署](#安装部署)
- [使用方法](#使用方法)
- [对比模式说明](#对比模式说明)
- [反 Bot 检测](#反-bot-检测)
- [截图对比原理](#截图对比原理)
- [应用场景](#应用场景)
- [技术栈](#技术栈)
- [作者](#作者)
- [License](#license)

---

## 功能特性

- **多浏览器支持**：Chrome / Edge / Firefox 自动检测，可指定优先级
- **反检测**：模拟真实 User-Agent，绕过基础 Bot 检测
- **多种对比模式**：像素级 / 感知哈希 / 内容结构
- **忽略区域**：支持排除动态背景、广告等干扰区域
- **HTML 报告**：自动生成带时间轴的对比报告
- **跨平台**：Windows / macOS / Linux 全支持

---

## 安装部署

### 安装

```bash
# 克隆仓库
git clone https://github.com/muyi3919/kina-archive.git
cd kina-archive

# 安装
pip install -e .
```

### 浏览器依赖

至少安装以下浏览器之一：

| 浏览器 | Windows | macOS | Linux |
|--------|---------|-------|-------|
| Google Chrome | [官网下载](https://www.google.com/chrome) | [官网下载](https://www.google.com/chrome) | `sudo apt install chromium-browser` |
| Microsoft Edge | [官网下载](https://www.microsoft.com/edge) | [官网下载](https://www.microsoft.com/edge) | - |
| Mozilla Firefox | [官网下载](https://www.mozilla.org/firefox) | [官网下载](https://www.mozilla.org/firefox) | `sudo apt install firefox` |

---

## 使用方法

### 基础截图

```bash
# 自动检测浏览器
kina-archive snapshot https://kina.ink

# 指定浏览器
kina-archive snapshot https://kina.ink --browser edge
```

### 对比模式（解决动态背景问题）

```bash
# 感知哈希模式 - 忽略背景图变化，推荐用于随机背景站点
kina-archive snapshot https://kina.ink --mode phash

# 内容结构模式 - 关注布局结构，忽略颜色/背景变化
kina-archive snapshot https://kina.ink --mode content

# 像素级模式（默认）- 最严格，适合静态页面
kina-archive snapshot https://kina.ink --mode pixel
```

### 忽略区域

如果你的页面有动态背景图、轮播广告等干扰区域，可以排除：

```bash
# 忽略顶部 300px 区域（常见背景图位置）
kina-archive snapshot https://kina.ink --ignore 0,0,1920,300

# 忽略多个区域（分号分隔）
kina-archive snapshot https://kina.ink --ignore "0,0,1920,300;0,800,1920,280"
```

### 持续监控

```bash
# 每小时监控，使用感知哈希模式（适合动态背景站点）
kina-archive watch https://kina.ink -i 3600 --mode phash

# 监控 10 次后停止
kina-archive watch https://kina.ink -i 1800 -c 10 --mode phash
```

### 其他命令

| 命令 | 说明 |
|------|------|
| `kina-archive history https://kina.ink -l 20` | 查看历史 |
| `kina-archive report` | 生成报告 |
| `kina-archive stats` | 查看统计 |

---

## 对比模式说明

| 模式 | 适用场景 | 特点 |
|------|---------|------|
| `pixel` | 静态页面、UI 测试 | 像素级严格对比，背景变化会触发告警 |
| `phash` | 动态背景、随机图片 | 感知哈希，忽略细微视觉差异，推荐用于博客/个人站 |
| `content` | 布局监控、结构对比 | 关注页面结构，忽略颜色和背景变化 |

---

## 反 Bot 检测

部分网站（如开启阿里云 ESA、Cloudflare 等 CDN 防护的站点）可能会拦截 headless 浏览器请求，显示验证码页面。

**解决方案：**

1. **使用真实浏览器**：工具已内置 User-Agent 伪装和反自动化检测参数
2. **指定不同浏览器尝试**：`--browser edge` 或 `--browser firefox`
3. **使用感知哈希模式**：`--mode phash` 可减少因验证码页面导致的误报
4. **在服务器部署**：将工具部署到与目标网站同 IP 段的服务器，避免 CDN 拦截
5. **忽略干扰区域**：`--ignore` 排除验证码弹窗区域

---

## 截图对比原理

- **像素级**：逐像素对比 RGB 差异，阈值 30
- **感知哈希**：缩放至 32x32 计算平均灰度哈希，汉明距离比对
- **内容结构**：检测边缘梯度变化，关注布局而非颜色

---

## 应用场景

- 监控博客改版效果（用 `phash` 模式忽略随机背景）
- 追踪竞品网站更新
- 记录网页历史状态
- 检测友链页面变更
- 验证部署是否生效
- UI 回归测试（用 `pixel` 模式）

---

## 技术栈

- Python 3.8+
- Pillow（图像处理）
- SQLite（数据存储）
- Chrome / Edge / Firefox Headless（截图引擎）

---

## 作者

**kina漫记** · [kina.ink](https://kina.ink)

---

## License

MIT License

---

*🕐 kina-archive — 记录网页的每一个瞬间*
