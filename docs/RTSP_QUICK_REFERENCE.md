# RTSP 跟踪快速参考

## 一句话总结
在 `run_video_generic()` 中添加了 `rtsp_url` 参数，现在可以从 RTSP 流进行目标跟踪！

## 最快上手（5 分钟）

### 步骤 1：启动 RTSP 服务器（终端 1）
```bash
cd /data/ProjectZKZS/Projects/pytracking
python3 tools/rtsp_server.py --source camera --backend gstreamer
# 或者用 mjpeg 后端
python3 tools/rtsp_server.py --source camera --backend mjpeg
```

### 步骤 2：运行跟踪器（终端 2）
```bash
cd /data/ProjectZKZS/Projects/pytracking
python3 scripts/run_tracker_with_rtsp.py --rtsp-url rtsp://localhost:8554/live
```

### 步骤 3：在弹出窗口中
1. 鼠标拖拽绘制目标边界框
2. 按 `q` 退出

## 核心改动

### 1. 跟踪器代码修改
文件：`pytracking/evaluation/tracker.py`

**新增参数：**
```python
def run_video_generic(self, ..., rtsp_url=None):
    """
    rtsp_url: RTSP 流 URL，例如 'rtsp://localhost:8554/live'
    """
```

**新增功能：**
- ✅ RTSP 流自动连接和重试
- ✅ 自动重连机制（最多 10 次）
- ✅ 支持 TCP 和 UDP 传输
- ✅ 实时显示帧数和视频源信息

### 2. 新增脚本
文件：`scripts/run_tracker_with_rtsp.py`

命令行工具，支持参数：
```bash
--rtsp-url      # RTSP 流 URL
--video-file    # 或本地视频文件
--tracker-name  # 跟踪器名称（默认 dimp）
--param-name    # 参数名（默认 dimp50）
--save-results  # 保存跟踪结果
--expand-roi    # 扩展感兴趣区域
--debug         # 调试级别
```

### 3. 新增 RTSP 服务器
文件：`tools/rtsp_server.py`

支持三种后端：
- **GStreamer** - 低延迟，高性能（需要 GStreamer）
- **FFmpeg** - 通用，可靠（需要 FFmpeg）
- **MJPEG** - 简单，无需 RTSP 服务器（HTTP）

## 代码示例

### Python 中直接使用
```python
from pytracking.evaluation.tracker import Tracker

tracker = Tracker('dimp', 'dimp50')

# 从 RTSP 流跟踪
tracker.run_video_generic(
    rtsp_url='rtsp://localhost:8554/live',
    debug=1,
    save_results=True
)
```

### 命令行使用
```bash
# 基本用法
python3 scripts/run_tracker_with_rtsp.py \
    --rtsp-url rtsp://localhost:8554/live

# 指定跟踪器
python3 scripts/run_tracker_with_rtsp.py \
    --rtsp-url rtsp://192.168.1.100:554/stream \
    --tracker-name keep_track \
    --param-name default

# 保存结果
python3 scripts/run_tracker_with_rtsp.py \
    --rtsp-url rtsp://localhost:8554/live \
    --save-results \
    --tracker-type test
```

## 支持的视频源

| 源类型 | 用法 | 示例 |
|--------|------|------|
| 本地摄像头 | （默认） | `tracker.run_video_generic()` |
| 视频文件 | `videofilepath=...` | `tracker.run_video_generic(videofilepath='/path/to/video.mp4')` |
| RTSP 流 | `rtsp_url=...` | `tracker.run_video_generic(rtsp_url='rtsp://localhost:8554/live')` |
| IP 摄像头 | `rtsp_url=...` | `tracker.run_video_generic(rtsp_url='rtsp://admin:pass@192.168.1.100:554/stream')` |

## 常见问题

**Q1：如何使用真实的 IP 摄像头？**
```bash
python3 scripts/run_tracker_with_rtsp.py \
    --rtsp-url rtsp://admin:password@192.168.1.100:554/stream/profile1 \
    --tracker-name dimp
```

**Q2：RTSP 断开了怎么办？**
代码会自动重试连接（最多 10 次），如果仍失败会退出。

**Q3：如何降低延迟？**
- 使用 FFmpeg 后端而不是 GStreamer
- 确保网络稳定
- 使用 TCP 传输（已默认）

**Q4：GStreamer 不可用怎么办？**
使用 FFmpeg 或 MJPEG 后端：
```bash
python3 tools/rtsp_server.py --source camera --backend ffmpeg
# 或
python3 tools/rtsp_server.py --source camera --backend mjpeg
```

**Q5：如何保存跟踪结果？**
```bash
python3 scripts/run_tracker_with_rtsp.py \
    --rtsp-url rtsp://localhost:8554/live \
    --save-results
```

## 文件列表

| 文件 | 说明 |
|------|------|
| `tools/rtsp_server.py` | RTSP/MJPEG 服务器（改进） |
| `pytracking/evaluation/tracker.py` | 跟踪器核心（新增 rtsp_url 参数） |
| `scripts/run_tracker_with_rtsp.py` | 新增跟踪脚本 |
| `scripts/test_rtsp_support.py` | 新增功能测试脚本 |
| `RTSP_TRACKING_GUIDE.md` | 详细使用指南 |

## 测试

运行测试脚本验证功能：
```bash
python3 scripts/test_rtsp_support.py
```

预期输出：
```
============================================================
PyTracking RTSP 功能测试
============================================================
...
[SUCCESS] 所有测试通过！
```

## 性能参考

| 场景 | FPS | 延迟 |
|------|-----|------|
| 本地摄像头 | 30+ | <100ms |
| RTSP 同机 | 25-30 | 100-500ms |
| 远程 IP 摄像头 | 15-25 | 500ms-2s |

## 键盘快捷键

| 按键 | 功能 |
|------|------|
| 鼠标拖拽 | 绘制边界框 |
| 左键点击 | 确认边界框 |
| `q` | 退出 |
| `r` | 重置 |
| 空格 | 暂停（仅视频文件） |

## 获取帮助

```bash
# 查看脚本帮助
python3 scripts/run_tracker_with_rtsp.py --help

# 查看 RTSP 服务器帮助
python3 tools/rtsp_server.py --help

# 查看详细文档
cat RTSP_TRACKING_GUIDE.md
```

## 后续改进建议

- [ ] 支持多目标 RTSP 流
- [ ] Web UI 仪表板
- [ ] 结果实时上传到服务器
- [ ] GPU 加速推理
- [ ] 支持更多编码格式（H.265 等）
