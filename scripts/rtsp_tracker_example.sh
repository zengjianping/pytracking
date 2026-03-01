#!/bin/bash
# PyTracking RTSP 支持 - 使用示例汇总
# 这个脚本展示了所有主要的使用方式

echo "=========================================="
echo "PyTracking RTSP 支持 - 使用示例"
echo "=========================================="
echo ""

# 示例 1: 显示帮助信息
echo "[示例 1] 查看脚本帮助"
echo "命令："
echo "  python3 tools/run_tracker_with_rtsp.py --help"
echo ""

# 示例 2: 从本地摄像头启动 RTSP 服务器
echo "[示例 2] 启动 RTSP 服务器 (从摄像头)"
echo "命令（终端1）:"
echo "  python3 tools/rtsp_server.py --source camera --backend gstreamer"
echo ""
echo "备选方案（如果 GStreamer 不可用）:"
echo "  python3 tools/rtsp_server.py --source camera --backend ffmpeg"
echo "  python3 tools/rtsp_server.py --source camera --backend mjpeg"
echo ""

# 示例 3: 从本地 RTSP 服务器跟踪
echo "[示例 3] 运行跟踪器 (连接到本地 RTSP)"
echo "命令（终端2，服务器启动后）:"
echo "  python3 tools/run_tracker_with_rtsp.py --rtsp-url rtsp://localhost:8554/live"
echo ""

# 示例 4: 循环播放视频文件
echo "[示例 4] RTSP 服务器循环播放视频文件"
echo "命令（终端1）:"
echo "  python3 tools/rtsp_server.py --source file --video-file /path/to/video.mp4"
echo ""

# 示例 5: 使用 HTTP MJPEG 后端（最简单）
echo "[示例 5] 使用 HTTP MJPEG 后端"
echo "启动服务器（终端1）:"
echo "  python3 tools/rtsp_server.py --source camera --backend mjpeg"
echo ""
echo "运行跟踪器（终端2）:"
echo "  python3 tools/run_tracker_with_rtsp.py --rtsp-url http://localhost:8080"
echo ""
echo "在浏览器中查看视频流:"
echo "  http://localhost:8080"
echo ""

# 示例 6: 真实 IP 摄像头
echo "[示例 6] 使用真实 IP 摄像头"
echo "命令:"
echo "  python3 tools/run_tracker_with_rtsp.py \\"
echo "    --rtsp-url rtsp://admin:password@192.168.1.100:554/stream/profile1 \\"
echo "    --tracker-name dimp \\"
echo "    --param-name dimp50"
echo ""

# 示例 7: 保存跟踪结果
echo "[示例 7] 保存跟踪结果"
echo "命令:"
echo "  python3 tools/run_tracker_with_rtsp.py \\"
echo "    --rtsp-url rtsp://localhost:8554/live \\"
echo "    --save-results \\"
echo "    --tracker-type mytest"
echo ""

# 示例 8: 不同的跟踪器
echo "[示例 8] 使用不同的跟踪器"
echo "DiMP 跟踪器:"
echo "  python3 tools/run_tracker_with_rtsp.py --rtsp-url ... --tracker-name dimp --param-name dimp50"
echo ""
echo "KeepTrack 跟踪器:"
echo "  python3 tools/run_tracker_with_rtsp.py --rtsp-url ... --tracker-name keep_track --param-name default"
echo ""
echo "其他可用跟踪器:"
echo "  ls pytracking/tracker/"
echo ""

# 示例 9: Python 代码直接集成
echo "[示例 9] 在 Python 代码中使用"
cat << 'EOF'
代码示例：
```python
from pytracking.evaluation.tracker import Tracker

# 创建跟踪器
tracker = Tracker('dimp', 'dimp50')

# 从 RTSP 流开始跟踪
tracker.run_video_generic(
    rtsp_url='rtsp://localhost:8554/live',
    debug=1,
    save_results=True,
    tracker_type='test'
)
```
EOF
echo ""

# 示例 10: 测试功能
echo "[示例 10] 验证 RTSP 功能"
echo "运行测试脚本:"
echo "  python3 scripts/test_rtsp_support.py"
echo ""

# 示例 11: 调试模式
echo "[示例 11] 启用调试输出"
echo "命令:"
echo "  python3 tools/run_tracker_with_rtsp.py \\"
echo "    --rtsp-url rtsp://localhost:8554/live \\"
echo "    --debug 2"
echo ""

# 示例 12: 自定义参数
echo "[示例 12] 完整参数示例"
echo "命令:"
echo "  python3 tools/run_tracker_with_rtsp.py \\"
echo "    --rtsp-url rtsp://admin:pass@192.168.1.100:554/stream \\"
echo "    --tracker-name dimp \\"
echo "    --param-name dimp50 \\"
echo "    --save-results \\"
echo "    --expand-roi \\"
echo "    --tracker-type custom \\"
echo "    --debug 1"
echo ""

echo "=========================================="
echo "更多信息："
echo "  - 详细指南: cat RTSP_TRACKING_GUIDE.md"
echo "  - 快速参考: cat RTSP_QUICK_REFERENCE.md"
echo "  - 实现总结: cat RTSP_IMPLEMENTATION_SUMMARY.md"
echo "=========================================="
