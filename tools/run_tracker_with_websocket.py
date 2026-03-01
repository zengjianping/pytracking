#!/usr/bin/env python3
"""
使用 WebSocket 发送跟踪脱靶量的跟踪脚本

脱靶量定义：目标框中心相对于图像中心的偏移量（pixel）

使用方法：
    python scripts/run_tracker_with_websocket.py \
        --rtsp-url rtsp://localhost:8554/live \
        --ws-url ws://localhost:8765 \
        --tracker-name dimp \
        --param-name dimp50
"""

import argparse
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pytracking.evaluation.tracker import Tracker


def main():
    parser = argparse.ArgumentParser(
        description='Run tracker with WebSocket offset transmission',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # 从 RTSP 流跟踪并发送脱靶量到 WebSocket
  python scripts/run_tracker_with_websocket.py \\
      --rtsp-url rtsp://localhost:8554/live \\
      --ws-url ws://localhost:8765
  
  # 从本地视频文件跟踪
  python scripts/run_tracker_with_websocket.py \\
      --video-file /path/to/video.mp4 \\
      --ws-url ws://localhost:8765
  
  # 从摄像头跟踪
  python scripts/run_tracker_with_websocket.py \\
      --ws-url ws://localhost:8765

WebSocket 消息格式：
  {{
    "type": "tracking_offset",
    "frame_number": 123,
    "object_id": 0,
    "offset": {{
      "x": -50.5,          # 相对图像中心的 X 偏移（像素）
      "y": 30.2,           # 相对图像中心的 Y 偏移（像素）
      "distance": 59.2     # 欧氏距离（像素）
    }},
    "target_center": {{
      "x": 640.0,          # 目标中心 X 坐标
      "y": 360.0           # 目标中心 Y 坐标
    }},
    "image_center": {{
      "x": 640.0,          # 图像中心 X 坐标
      "y": 360.0           # 图像中心 Y 坐标
    }},
    "image_size": {{
      "width": 1280,       # 图像宽度
      "height": 720        # 图像高度
    }},
    "timestamp": 1234567890.123
  }}
        '''
    )
    
    # 视频源参数
    source_group = parser.add_argument_group('视频源参数')
    source_group.add_argument('--rtsp-url', type=str, default=None,
                              help='RTSP 流地址（如: rtsp://localhost:8554/live）')
    source_group.add_argument('--video-file', type=str, default=None,
                              help='本地视频文件路径')
    source_group.add_argument('--camera-id', type=int, default=0,
                              help='摄像头 ID（默认: 0）')
    
    # WebSocket 参数
    ws_group = parser.add_argument_group('WebSocket 参数')
    ws_group.add_argument('--ws-url', type=str, required=True,
                          help='WebSocket 服务器地址（如: ws://localhost:8765）')
    
    # 跟踪器参数
    tracker_group = parser.add_argument_group('跟踪器参数')
    tracker_group.add_argument('--tracker-name', type=str, default='dimp',
                               help='跟踪器名称（默认: dimp）')
    tracker_group.add_argument('--param-name', type=str, default='dimp50',
                               help='参数名（默认: dimp50）')
    
    # 输出参数
    output_group = parser.add_argument_group('输出参数')
    output_group.add_argument('--save-results', action='store_true',
                              help='保存跟踪结果')
    output_group.add_argument('--expand-roi', action='store_true',
                              help='扩展感兴趣区域')
    output_group.add_argument('--tracker-type', type=str, default='none',
                              help='跟踪器类型标签（默认: none）')
    
    # 调试参数
    parser.add_argument('--debug', type=int, default=0,
                        help='调试级别（0-3，默认: 0）')
    
    args = parser.parse_args()
    
    # 创建跟踪器（注意：添加了 ws_url 参数）
    tracker = Tracker(
        args.tracker_name,
        args.param_name,
        ws_url=args.ws_url  # 传入 WebSocket URL
    )
    
    print(f"\n{'='*60}")
    print(f"PyTracking 跟踪器（带 WebSocket 脱靶量发送）")
    print(f"{'='*60}")
    print(f"跟踪器: {args.tracker_name} ({args.param_name})")
    print(f"WebSocket 服务器: {args.ws_url}")
    
    if args.rtsp_url:
        print(f"视频源: RTSP 流 ({args.rtsp_url})")
        video_source = args.rtsp_url
    elif args.video_file:
        print(f"视频源: 本地视频文件 ({args.video_file})")
        video_source = args.video_file
    else:
        print(f"视频源: 网络摄像头 (ID: {args.camera_id})")
        video_source = None
    
    print(f"{'='*60}\n")
    
    # 运行跟踪器
    try:
        tracker.run_video_generic(
            debug=args.debug,
            videofilepath=video_source if args.video_file else None,
            rtsp_url=args.rtsp_url,
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
        print(f"[INFO] 跟踪已结束")


if __name__ == '__main__':
    main()
