#!/usr/bin/env python3
"""
从 RTSP 流和其他视频源运行跟踪器的完整脚本

支持功能:
  - RTSP 流跟踪
  - 本地视频文件跟踪
  - 网络摄像头跟踪
  - WebSocket 脱靶量实时发送（可选）

使用方法:
1. 启动 RTSP 服务器（可选）：
   python3 tools/rtsp_server.py --source camera --backend gstreamer

2. 启动 WebSocket 接收服务（可选）：
   python3 tools/websocket_receiver_example.py --port 8765

3. 运行跟踪器 - RTSP 流：
   python3 tools/run_tracker_with_rtsp.py --rtsp-url rtsp://localhost:8554/live

4. 运行跟踪器 - RTSP + WebSocket：
   python3 tools/run_tracker_with_rtsp.py \
       --rtsp-url rtsp://localhost:8554/live \
       --ws-url ws://localhost:8765

5. 运行跟踪器 - 本地视频 + WebSocket：
   python3 tools/run_tracker_with_rtsp.py \
       --video-file /path/to/video.mp4 \
       --ws-url ws://localhost:8765

6. 在弹出的窗口中：
   - 用鼠标绘制初始边界框
   - 按 'q' 退出
   - 按 'r' 重置跟踪器
   - 按空格暂停/继续（仅视频文件支持）
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pytracking.evaluation.tracker import Tracker


def main():
    parser = argparse.ArgumentParser(
        description='从 RTSP 流或视频文件运行跟踪器（支持 WebSocket 脱靶量发送）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例用法:
  # RTSP 流跟踪
  python3 tools/run_tracker_with_rtsp.py --rtsp-url rtsp://localhost:8554/live
  
  # RTSP + WebSocket 脱靶量
  python3 tools/run_tracker_with_rtsp.py \\
      --rtsp-url rtsp://localhost:8554/live \\
      --ws-url ws://localhost:8765
  
  # 本地视频文件
  python3 tools/run_tracker_with_rtsp.py --video-file video.mp4
  
  # 本地视频 + WebSocket
  python3 tools/run_tracker_with_rtsp.py \\
      --video-file video.mp4 \\
      --ws-url ws://localhost:8765
  
  # 网络摄像头 + WebSocket
  python3 tools/run_tracker_with_rtsp.py \\
      --camera-id 0 \\
      --ws-url ws://localhost:8765

WebSocket 脱靶量消息格式:
  {{
    "type": "tracking_offset",
    "frame_number": 123,
    "object_id": 0,
    "offset": {{
      "x": -50.5,              # 相对图像中心的 X 偏移（像素）
      "y": 30.2,               # 相对图像中心的 Y 偏移（像素）
      "distance": 59.2         # 欧氏距离（像素）
    }},
    "target_center": {{"x": 640.0, "y": 360.0}},
    "image_center": {{"x": 640.0, "y": 360.0}},
    "image_size": {{"width": 1280, "height": 720}},
    "timestamp": 1234567890.123,
    "confidence": 0.95
  }}
        '''
    )
    
    # 视频源参数
    source_group = parser.add_argument_group('视频源参数（选择其中一个）')
    source_group.add_argument('--rtsp-url', type=str, default=None,
                      help='RTSP 流 URL 例如: rtsp://localhost:8554/live')
    source_group.add_argument('--video-file', type=str, default=None,
                      help='本地视频文件路径')
    source_group.add_argument('--camera-id', type=int, default=0,
                      help='网络摄像头 ID (默认: 0，如果不指定视频源则使用)')
    
    # WebSocket 参数
    ws_group = parser.add_argument_group('WebSocket 参数（可选）')
    ws_group.add_argument('--ws-url', type=str, default=None,
                      help='WebSocket 服务器地址 例如: ws://localhost:8765')
    
    # 跟踪器参数
    tracker_group = parser.add_argument_group('跟踪器参数')
    tracker_group.add_argument('--tracker-name', type=str, default='dimp',
                      help='跟踪器名称 (默认: dimp)')
    tracker_group.add_argument('--param-name', type=str, default='dimp50',
                      help='参数名称 (默认: dimp50)')
    
    # 输出参数
    output_group = parser.add_argument_group('输出参数')
    output_group.add_argument('--save-results', action='store_true',
                      help='保存跟踪结果')
    output_group.add_argument('--expand-roi', action='store_true',
                      help='扩展感兴趣区域')
    output_group.add_argument('--tracker-type', type=str, default='none',
                      help='跟踪器类型标签')
    
    # 调试参数
    debug_group = parser.add_argument_group('调试参数')
    debug_group.add_argument('--debug', type=int, default=0,
                      help='调试级别 (0-3，默认: 0)')
    
    args = parser.parse_args()
    
    # 验证参数
    if args.rtsp_url is None and args.video_file is None:
        print("[INFO] 没有指定视频源，使用默认网络摄像头 (ID: {})".format(args.camera_id))
        video_source_type = 'camera'
        video_source = None
    elif args.rtsp_url is not None and args.video_file is not None:
        print("[WARNING] 同时指定了 RTSP URL 和视频文件，优先使用 RTSP URL")
        video_source_type = 'rtsp'
        video_source = args.rtsp_url
    elif args.rtsp_url is not None:
        video_source_type = 'rtsp'
        video_source = args.rtsp_url
    else:
        video_source_type = 'file'
        video_source = args.video_file
    
    # 打印配置信息
    print("\n" + "="*70)
    print("PyTracking 完整跟踪系统")
    print("="*70)
    print(f"跟踪器: {args.tracker_name} ({args.param_name})")
    
    if video_source_type == 'rtsp':
        print(f"视频源: RTSP 流 ({video_source})")
    elif video_source_type == 'file':
        print(f"视频源: 本地视频文件 ({video_source})")
    else:
        print(f"视频源: 网络摄像头 (ID: {args.camera_id})")
    
    if args.ws_url:
        print(f"WebSocket: 启用 ({args.ws_url})")
        print("           脱靶量数据将实时发送到 WebSocket 服务器")
    else:
        print(f"WebSocket: 禁用")
    
    print(f"保存结果: {'是' if args.save_results else '否'}")
    print(f"调试级别: {args.debug}")
    print("="*70 + "\n")
    
    # 创建跟踪器（可选择性启用 WebSocket）
    try:
        tracker = Tracker(
            args.tracker_name,
            args.param_name,
            ws_url=args.ws_url  # 如果 ws_url 为 None，WebSocket 功能被禁用
        )
    except Exception as e:
        print(f"[ERROR] 创建跟踪器失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 运行跟踪
    try:
        if video_source_type == 'rtsp':
            print(f"[INFO] 从 RTSP 流开始跟踪: {video_source}")
            tracker.run_video_generic(
                debug=args.debug,
                rtsp_url=video_source,
                save_results=args.save_results,
                expand_roi=args.expand_roi,
                tracker_type=args.tracker_type
            )
        elif video_source_type == 'file':
            print(f"[INFO] 从视频文件开始跟踪: {video_source}")
            tracker.run_video_generic(
                debug=args.debug,
                videofilepath=video_source,
                save_results=args.save_results,
                expand_roi=args.expand_roi,
                tracker_type=args.tracker_type
            )
        else:
            print(f"[INFO] 从摄像头开始跟踪 (ID: {args.camera_id})")
            tracker.run_video_generic(
                debug=args.debug,
                save_results=args.save_results,
                expand_roi=args.expand_roi,
                tracker_type=args.tracker_type
            )
    except KeyboardInterrupt:
        print("\n[INFO] 用户中断跟踪")
    except Exception as e:
        print(f"\n[ERROR] 跟踪过程中出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("[INFO] 跟踪已结束")


if __name__ == '__main__':
    main()
