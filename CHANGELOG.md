# Changelog

## [1.1.0] - 2026-06-25

### 修复 (Fixed)
- **修复 `kina-archive report` 命令崩溃** — CSS 中的 `{margin:0}` 被 `str.format()` 误解析为占位符，导致 `KeyError: 'margin'`
- **修复 Firefox/Edge 浏览器截图完全失效** — 原代码所有浏览器共用 Chrome 参数（`--disable-gpu`、`--no-sandbox` 等），Firefox 不识别导致截图失败并 fallback 到占位图
- **修复 diff 对比图同一天被覆盖** — `_save_diff` 使用 `%Y%m%d` 日期哈希，同一天多次对比会覆盖旧文件，现改为 `%Y%m%d_%H%M%S_%f` 微秒级时间戳
- **修复 HTML 报告图片路径失效** — 报告使用数据库中的相对路径引用截图，移动报告目录后图片 404，现生成报告时自动复制截图/diff 图到 `report_assets/` 目录
- **修复 CI 测试配置错误** — 原 `ci.yml` 测试路径 `tests/` 不存在且执行 `kina-archive stats` 需要数据库，改为 `pytest test_basic.py -v` 和 `kina-archive --version`
- **修复版本号不一致** — `README.md` badge 写 `1.0.0`、`setup.py` 和 `__init__.py` 写 `0.1.0`，现统一为 `1.1.0`

### 新增 (Added)
- **日志系统** — 全模块引入 `logging`，CLI 新增 `--verbose` / `--quiet` 参数控制日志级别
- **截图超时参数** — CLI 新增 `--timeout` 参数（默认 60 秒），支持自定义截图等待时间
- **百分比坐标忽略区域** — `--ignore` 支持百分比格式，如 `0,0,100%,20%` 表示忽略顶部 20%，自动根据截图尺寸换算
- **版本号查看** — CLI 新增 `--version` 参数
- **数据库上下文管理器** — `ArchiveDB` 支持 `with ArchiveDB() as db:` 语法，自动关闭连接
- **测试覆盖** — 新增 phash/pixel 对比测试、百分比坐标解析测试、上下文管理器测试

### 优化 (Changed)
- **阈值硬编码提取为常量** — `PIXEL_DIFF_THRESHOLD`、`CONTENT_GRAD_THRESHOLD`、`PHASH_SIZE`、`SIMILARITY_LOW`、`SIMILARITY_CHANGE` 移至模块顶部，便于调优
- **截图参数按浏览器分离** — Chrome/Edge 和 Firefox 使用独立的参数构建函数，避免参数冲突
- **setup.py 依赖同步** — 自动读取 `requirements.txt` 填充 `install_requires`，避免两边维护不同步

---

## [1.0.0] - 2026-06-23

### 初始版本
- 多浏览器支持：Chrome / Edge / Firefox 自动检测
- 3 种对比模式：pixel（像素级）、phash（感知哈希）、content（内容结构）
- 忽略指定区域：`--ignore x,y,w,h`
- 生成 HTML 时间轴对比报告
- 跨平台：Windows / macOS / Linux
