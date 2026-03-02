#!/usr/bin/env python3
"""
WebSocket 接收器示例 - 用于接收和处理跟踪脱靶量数据

此脚本演示如何创建一个 WebSocket 服务器来接收跟踪脱靶量数据。

安装依赖：
    pip install websockets

运行：
    python tools/websocket_receiver_example.py --port 8765
    
然后在另一个终端运行跟踪器：
    python scripts/run_tracker_with_websocket.py \\
        --rtsp-url rtsp://localhost:8554/live \\
        --ws-url ws://localhost:8765
"""

import asyncio
import json
import argparse
import sys
import os
import websockets
from datetime import datetime
from collections import deque


class OffsetTracker:
    """用于跟踪和分析脱靶量的类"""
    
    def __init__(self, window_size=30):
        """初始化偏移跟踪器
        
        Args:
            window_size: 用于计算移动平均的样本窗口大小
        """
        self.window_size = window_size
        self.frame_count = 0
        self.offset_history = deque(maxlen=window_size)
        self.distance_history = deque(maxlen=window_size)
        
    def update(self, offset_data):
        """更新偏移数据
        
        Args:
            offset_data: 包含 offset 信息的字典
        """
        self.frame_count += 1
        
        offset_x = offset_data.get('offset', {}).get('x', 0)
        offset_y = offset_data.get('offset', {}).get('y', 0)
        distance = offset_data.get('offset', {}).get('distance', 0)
        
        self.offset_history.append((offset_x, offset_y))
        self.distance_history.append(distance)
        
    def get_stats(self):
        """获取统计信息
        
        Returns:
            dict: 包含平均、最大、最小等统计值
        """
        if not self.distance_history:
            return {}
        
        distances = list(self.distance_history)
        offsets = list(self.offset_history)
        
        if not offsets:
            return {}
        
        avg_distance = sum(distances) / len(distances)
        max_distance = max(distances)
        min_distance = min(distances)
        
        avg_offset_x = sum(x for x, y in offsets) / len(offsets)
        avg_offset_y = sum(y for x, y in offsets) / len(offsets)
        
        return {
            'avg_distance': round(avg_distance, 2),
            'max_distance': round(max_distance, 2),
            'min_distance': round(min_distance, 2),
            'avg_offset_x': round(avg_offset_x, 2),
            'avg_offset_y': round(avg_offset_y, 2),
        }


class WebSocketOffsetReceiver:
    """WebSocket 脱靶量接收服务"""
    
    def __init__(self, host='localhost', port=8765, verbose=True):
        """初始化接收器
        
        Args:
            host: 监听主机地址
            port: 监听端口
            verbose: 是否打印详细信息
        """
        self.host = host
        self.port = port
        self.verbose = verbose
        self.tracker = OffsetTracker()
        self.message_count = 0
        self.start_time = None
        
    def log(self, message, level='INFO'):
        """记录消息
        
        Args:
            message: 消息内容
            level: 日志级别（INFO, WARNING, ERROR）
        """
        if self.verbose:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            print(f"[{timestamp}] [{level}] {message}")
    
    def format_offset_message(self, data):
        """格式化并显示偏移消息
        
        Args:
            data: WebSocket 消息数据
        """
        frame_number = data.get('frame_number', 'N/A')
        object_id = data.get('object_id', 0)
        
        offset = data.get('offset', {})
        offset_x = offset.get('x', 0)
        offset_y = offset.get('y', 0)
        distance = offset.get('distance', 0)
        
        target_center = data.get('target_center', {})
        image_center = data.get('image_center', {})
        image_size = data.get('image_size', {})
        
        # 格式化显示
        status_str = f"Frame #{frame_number:4d} | Object {object_id} | "
        status_str += f"Offset: ({offset_x:7.1f}, {offset_y:7.1f}) | "
        status_str += f"Distance: {distance:6.1f}px"
        
        self.log(status_str)
        
        # 每 30 帧显示统计信息
        if self.message_count % 30 == 0:
            stats = self.tracker.get_stats()
            if stats:
                stats_str = "  📊 Statistics (last 30 frames): "
                stats_str += f"Avg Distance: {stats['avg_distance']}px | "
                stats_str += f"Max: {stats['max_distance']}px | "
                stats_str += f"Avg Offset: ({stats['avg_offset_x']}, {stats['avg_offset_y']})"
                self.log(stats_str)
    
    async def handle_client(self, websocket):
        """处理客户端连接
        
        Args:
            websocket: WebSocket 连接对象
            path: 连接路径
        """
        client_addr = websocket.remote_address
        self.log(f"客户端已连接: {client_addr[0]}:{client_addr[1]}", "INFO")
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    self.message_count += 1
                    #self.tracker.update(data)
                    #self.format_offset_message(data)
                    
                except json.JSONDecodeError as e:
                    self.log(f"JSON 解析错误: {e}", "ERROR")
                except Exception as e:
                    self.log(f"处理消息时出错: {e}", "ERROR")
                    
        except asyncio.CancelledError:
            self.log(f"客户端连接被取消: {client_addr}", "INFO")
        except Exception as e:
            self.log(f"客户端连接异常: {e}", "ERROR")
        finally:
            self.log(f"客户端已断开: {client_addr[0]}:{client_addr[1]}", "INFO")
            
            # 显示最终统计信息
            stats = self.tracker.get_stats()
            if stats:
                self.log("="*60)
                self.log("📈 最终统计信息 (所有帧):")
                self.log(f"  总帧数: {self.tracker.frame_count}")
                self.log(f"  总消息数: {self.message_count}")
                self.log(f"  平均脱靶距离: {stats['avg_distance']} px")
                self.log(f"  最大脱靶距离: {stats['max_distance']} px")
                self.log(f"  最小脱靶距离: {stats['min_distance']} px")
                self.log(f"  平均 X 偏移: {stats['avg_offset_x']} px")
                self.log(f"  平均 Y 偏移: {stats['avg_offset_y']} px")
                self.log("="*60)
            
            self.log("="*60)
            self.log(data)
    
    async def start(self):
        """启动 WebSocket 服务器"""
        self.start_time = datetime.now()
        
        self.log("="*60)
        self.log(f"WebSocket 脱靶量接收服务启动", "INFO")
        self.log(f"监听地址: ws://{self.host}:{self.port}", "INFO")
        self.log(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
        self.log("="*60)
        
        #async with asyncio.Server.websockets.serve(
        async with websockets.serve(
            self.handle_client,
            self.host,
            self.port
        ):
            self.log(f"等待客户端连接...", "INFO")
            await asyncio.Future()  # 运行直到中断


def main():
    parser = argparse.ArgumentParser(
        description='WebSocket 脱靶量接收服务',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例用法：
  # 启动本地服务（默认端口 8765）
  python tools/websocket_receiver_example.py
  
  # 指定端口
  python tools/websocket_receiver_example.py --port 9000
  
  # 监听所有网络接口
  python tools/websocket_receiver_example.py --host 0.0.0.0
  
  # 静默模式（不打印详细信息）
  python tools/websocket_receiver_example.py --quiet
        '''
    )
    
    parser.add_argument('--host', type=str, default='localhost',
                        help='监听主机地址（默认: localhost）')
    parser.add_argument('--port', type=int, default=8765,
                        help='监听端口（默认: 8765）')
    parser.add_argument('--quiet', action='store_true',
                        help='静默模式（不打印详细信息）')
    
    args = parser.parse_args()
    
    try:
        # 导入 websockets 库
        import websockets
    except ImportError:
        print("错误: 需要安装 websockets 库")
        print("请运行: pip install websockets")
        sys.exit(1)
    
    receiver = WebSocketOffsetReceiver(
        host=args.host,
        port=args.port,
        verbose=not args.quiet
    )
    
    try:
        asyncio.run(receiver.start())
    except KeyboardInterrupt:
        print("\n[INFO] 服务已停止")
    except Exception as e:
        print(f"[ERROR] 服务异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
