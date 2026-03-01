#!/usr/bin/env python3
"""
WebSocket 脱靶量功能 - 快速开始指南

此脚本演示完整的工作流程，包括：
1. 启动 WebSocket 接收服务
2. 启动跟踪器
3. 接收和处理脱靶量数据

使用方法：
    python tools/websocket_quick_start.py
"""

import os
import sys
import time
import subprocess
import signal
from pathlib import Path


class Colors:
    """终端颜色输出"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_section(title):
    """打印章节标题"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")


def print_success(msg):
    """打印成功信息"""
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")


def print_info(msg):
    """打印信息"""
    print(f"{Colors.CYAN}ℹ {msg}{Colors.RESET}")


def print_warning(msg):
    """打印警告"""
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.RESET}")


def print_error(msg):
    """打印错误"""
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")


def check_dependencies():
    """检查必需的依赖"""
    print_section("1️⃣  检查依赖")
    
    required_packages = {
        #'websocket-client': 'WebSocket 客户端库',
        'websockets': 'WebSocket 服务器库',
        'cv2': 'OpenCV',
        'numpy': 'NumPy'
    }
    
    missing = []
    for package, description in required_packages.items():
        try:
            __import__(package.replace('-', '_'))
            print_success(f"{description} ({package})")
        except ImportError:
            print_error(f"{description} ({package})")
            missing.append(package)
    
    if missing:
        print_warning("缺少以下依赖，请安装：")
        print(f"  pip install {' '.join(missing)}")
        return False
    
    return True


def show_architecture():
    """展示系统架构"""
    print_section("2️⃣  系统架构")
    
    architecture = """
    ┌─────────────────────────────────────────────────────────────────┐
    │                                                                  │
    │  📹 视频源                                                      │
    │  (RTSP/本地文件/摄像头)                                          │
    │           ↓                                                     │
    │  ┌──────────────────────────────────────────────────────┐      │
    │  │  主跟踪线程 (main thread)                              │      │
    │  │  - 处理视频帧                                         │      │
    │  │  - 执行跟踪算法                                       │      │
    │  │  - 计算脱靶量                                         │      │
    │  │  - 入队消息 (非阻塞)                                  │      │
    │  └──────────────────────────────────────────────────────┘      │
    │           ↓                                                     │
    │  ┌──────────────────────────────────────────────────────┐      │
    │  │  线程安全队列 (Queue, maxsize=100)                    │      │
    │  └──────────────────────────────────────────────────────┘      │
    │           ↓                                                     │
    │  ┌──────────────────────────────────────────────────────┐      │
    │  │  WebSocket 发送线程 (sender thread, daemon)           │      │
    │  │  - 从队列取消息                                       │      │
    │  │  - 建立 WebSocket 连接                               │      │
    │  │  - 发送 JSON 数据                                    │      │
    │  │  - 处理网络错误                                       │      │
    │  └──────────────────────────────────────────────────────┘      │
    │           ↓                                                     │
    │  🌐 WebSocket 服务器                                           │
    │  (ws://localhost:8765)                                        │
    │           ↓                                                     │
    │  📊 接收器应用                                                  │
    │  (实时处理脱靶量数据)                                           │
    │                                                                  │
    └─────────────────────────────────────────────────────────────────┘
    
    关键特性：
    ✓ 主线程不被网络延迟阻塞
    ✓ 独立的消息队列管理
    ✓ 自动错误恢复
    ✓ 完全线程安全
    """
    print(architecture)


def show_message_format():
    """显示消息格式"""
    print_section("3️⃣  WebSocket 消息格式")
    
    message_example = """{
  "type": "tracking_offset",
  "frame_number": 42,
  "object_id": 0,
  "offset": {
    "x": -50.5,           # 相对图像中心的 X 偏移（像素）
    "y": 30.2,            # 相对图像中心的 Y 偏移（像素）
    "distance": 59.2      # 欧氏距离
  },
  "target_center": {
    "x": 640.5,           # 目标中心 X 坐标
    "y": 400.2            # 目标中心 Y 坐标
  },
  "image_center": {
    "x": 640.0,           # 图像中心 X 坐标
    "y": 360.0            # 图像中心 Y 坐标
  },
  "image_size": {
    "width": 1280,        # 图像宽度
    "height": 720         # 图像高度
  },
  "timestamp": 1704063600.123
}"""
    
    print_info("每个跟踪帧发送一条 JSON 消息：")
    print(f"{Colors.CYAN}{message_example}{Colors.RESET}")


def show_quick_start():
    """显示快速开始步骤"""
    print_section("4️⃣  快速开始（3 步）")
    
    steps = [
        ("启动 WebSocket 接收服务", 
         "python tools/websocket_receiver_example.py --port 8765"),
        
        ("启动 RTSP 流服务（可选）",
         "python tools/rtsp_server.py --source camera --backend gstreamer"),
        
        ("运行跟踪器",
         "python tools/run_tracker_with_websocket.py \\\n"
         "    --rtsp-url rtsp://localhost:8554/live \\\n"
         "    --ws-url ws://localhost:8765")
    ]
    
    for i, (title, cmd) in enumerate(steps, 1):
        print(f"{Colors.BOLD}步骤 {i}: {title}{Colors.RESET}")
        print(f"  {Colors.CYAN}$ {cmd}{Colors.RESET}\n")


def show_python_integration():
    """显示 Python 集成示例"""
    print_section("5️⃣  Python 集成示例")
    
    code = """from pytracking.evaluation.tracker import Tracker

# 创建跟踪器，指定 WebSocket 服务器地址
tracker = Tracker(
    'dimp',                      # 跟踪器名称
    'dimp50',                    # 参数配置
    ws_url='ws://localhost:8765' # WebSocket 服务器地址
)

# 从 RTSP 流进行跟踪
tracker.run_video_generic(
    rtsp_url='rtsp://localhost:8554/live'
)

# 或从本地视频文件
tracker.run_video_generic(
    videofilepath='/path/to/video.mp4'
)

# 或从摄像头
tracker.run_video_generic()
"""
    
    print_info("在 Python 代码中使用：")
    print(f"{Colors.CYAN}{code}{Colors.RESET}")


def show_troubleshooting():
    """显示故障排除指南"""
    print_section("6️⃣  故障排除")
    
    issues = [
        ("连接超时", 
         [
             "确认接收服务已启动: ps aux | grep websocket",
             "检查防火墙设置: sudo ufw allow 8765",
             "检查 WebSocket URL: ws://localhost:8765"
         ]),
        
        ("消息丢失",
         [
             "网络速度可能太慢",
             "增加队列大小（修改 tracker.py 中的 maxsize）",
             "减少帧率或使用本地视频文件而不是 RTSP"
         ]),
        
        ("脱靶量为 0",
         [
             "这是正常的！说明目标在图像中心",
             "说明跟踪效果最好"
         ]),
        
        ("脱靶量异常大",
         [
             "检查目标框是否跟踪漂移",
             "检查目标是否移出视野",
             "在接收器中打印调试信息"
         ])
    ]
    
    for issue, solutions in issues:
        print(f"{Colors.YELLOW}{issue}:{Colors.RESET}")
        for solution in solutions:
            print(f"  • {solution}")
        print()


def show_use_cases():
    """显示应用场景"""
    print_section("7️⃣  常见应用场景")
    
    use_cases = [
        ("云台联动 (PTZ)",
         "根据脱靶量实时控制摄像头云台方向"),
        
        ("虚拟焦点",
         "动态调整虚拟焦点位置，始终聚焦于目标中心"),
        
        ("精准定位",
         "将脱靶量转换为世界坐标，进行精准定位"),
        
        ("数据记录",
         "记录脱靶量历史用于分析跟踪效果"),
        
        ("警告告警",
         "当脱靶量超过阈值时触发告警"),
        
        ("性能评估",
         "实时计算跟踪稳定性指标")
    ]
    
    for i, (use_case, description) in enumerate(use_cases, 1):
        print(f"{Colors.BOLD}{i}. {use_case}{Colors.RESET}")
        print(f"   {description}\n")


def show_resources():
    """显示参考资源"""
    print_section("8️⃣  参考资源")
    
    resources = [
        ("完整文档", "docs/WEBSOCKET_OFFSET_TRACKING.md"),
        ("跟踪脚本", "tools/run_tracker_with_websocket.py"),
        ("接收器示例", "tools/websocket_receiver_example.py"),
        ("RTSP 指南", "RTSP_TRACKING_GUIDE.md"),
    ]
    
    print_info("相关文件：\n")
    for resource_type, path in resources:
        print(f"  📄 {resource_type}: {Colors.CYAN}{path}{Colors.RESET}")


def show_next_steps():
    """显示下一步"""
    print_section("✨ 下一步")
    
    next_steps = """
    1️⃣  安装依赖
       pip install websocket-client websockets
    
    2️⃣  启动 WebSocket 接收服务
       python tools/websocket_receiver_example.py
    
    3️⃣  运行跟踪器
       python tools/run_tracker_with_websocket.py --ws-url ws://localhost:8765
    
    4️⃣  观察接收服务的输出
       你应该看到实时的脱靶量数据
    
    5️⃣  自定义处理逻辑
       修改 tools/websocket_receiver_example.py 中的处理代码
    
    6️⃣  部署到实际应用
       创建自己的 WebSocket 服务来集成到现有系统
    """
    
    print(next_steps)


def main():
    """主程序"""
    
    print(f"\n{Colors.BOLD}{Colors.GREEN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.GREEN}PyTracking WebSocket 脱靶量功能 - 快速开始{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.GREEN}{'='*60}{Colors.RESET}")
    
    # 检查依赖
    if not check_dependencies():
        print_warning("请先安装缺失的依赖，然后重新运行此脚本")
        sys.exit(1)
    
    # 显示各个部分
    show_architecture()
    show_message_format()
    show_quick_start()
    show_python_integration()
    show_troubleshooting()
    show_use_cases()
    show_resources()
    show_next_steps()
    
    # 底部信息
    print(f"\n{Colors.BOLD}{Colors.GREEN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.GREEN}文档和支持{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.GREEN}{'='*60}{Colors.RESET}\n")
    
    print(f"  {Colors.CYAN}完整文档: {Colors.RESET}docs/WEBSOCKET_OFFSET_TRACKING.md")
    print(f"  {Colors.CYAN}快速参考: {Colors.RESET}docs/README.md")
    print(f"  {Colors.CYAN}源代码:   {Colors.RESET}pytracking/evaluation/tracker.py")
    print(f"\n")


if __name__ == '__main__':
    main()
