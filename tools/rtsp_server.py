#!/usr/bin/env python3
"""
RTSP 视频流服务器
支持 webcam 和视频文件循环播放
依赖：opencv-python, gstreamer1.0-rtsp-server, pygobject

安装依赖：
  pip install opencv-python
  sudo apt-get install gstreamer1.0-rtsp-server libgirepository1.0-dev gstreamer1.0-plugins-base
  pip install PyGObject
"""

import cv2
import argparse
import threading
import time
import sys
from pathlib import Path

try:
    import gi
    gi.require_version('Gst', '1.0')
    gi.require_version('GstRtspServer', '1.0')
    from gi.repository import Gst, GstRtspServer, GLib
    GSTREAMER_AVAILABLE = True
except ImportError:
    GSTREAMER_AVAILABLE = False
    print("[WARNING] GStreamer not available, will use FFmpeg backend")

try:
    import numpy as np
except ImportError:
    np = None


class VideoSource:
    """视频源基类"""
    def __init__(self):
        self.width = 640
        self.height = 480
        self.fps = 30
        self.cap = None

    def get_frame(self, timeout=0.05):
        """获取一帧，返回 numpy 数组 (BGR)"""
        raise NotImplementedError

    def release(self):
        """释放资源"""
        raise NotImplementedError


class WebcamSource(VideoSource):
    """Web摄像头视频源"""
    def __init__(self, camera_id=0):
        super().__init__()
        self.cap = cv2.VideoCapture(camera_id)
        if not self.cap.isOpened():
            raise RuntimeError(f"无法打开摄像头 {camera_id}")
        
        # 设置分辨率和帧率
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = int(self.cap.get(cv2.CAP_PROP_FPS)) or 30

    def get_frame(self, timeout=0.05):
        """获取一帧"""
        ret, frame = self.cap.read()
        if ret:
            return frame
        return None

    def release(self):
        if self.cap:
            self.cap.release()


class VideoFileSource(VideoSource):
    """视频文件循环播放源"""
    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath
        self.cap = cv2.VideoCapture(filepath)
        if not self.cap.isOpened():
            raise RuntimeError(f"无法打开视频文件 {filepath}")
        
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = int(self.cap.get(cv2.CAP_PROP_FPS)) or 30
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

    def get_frame(self, timeout=0.05):
        """获取一帧，循环播放"""
        ret, frame = self.cap.read()
        if not ret:
            # 文件结尾，重新开始
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
        
        if ret:
            return frame
        return None

    def release(self):
        if self.cap:
            self.cap.release()


class RTSPServerGStreamer:
    """基于 GStreamer 的 RTSP 服务器"""
    
    def __init__(self, video_source, port=8554, path="/live"):
        self.video_source = video_source
        self.port = port
        self.path = path
        self.server = None
        self.factory = None
        self.loop = None
        self._running = False
        self._pts = 0  # 单调递增的时间戳
        self._lock = threading.Lock()
        
        if not GSTREAMER_AVAILABLE:
            raise RuntimeError("GStreamer 未安装")
        
        Gst.init(None)

    def _need_data_callback(self, src, length):
        """GStreamer 请求数据回调"""
        try:
            frame = self.video_source.get_frame(timeout=0.05)
            if frame is not None:
                # 转换为 GStreamer buffer
                data = frame.tobytes()
                buf = Gst.Buffer.new_wrapped(data)
                
                # 设置时间戳（单调递增，基于帧持续时长）
                duration = int(Gst.SECOND / float(self.video_source.fps))
                buf.pts = self._pts
                buf.dts = self._pts
                buf.duration = duration
                self._pts += duration
                
                src.emit("push-buffer", buf)
        except Exception as e:
            print(f"[ERROR] 推送 buffer 时出错: {e}")

    def _enough_data_callback(self, src):
        """GStreamer 缓冲区满回调"""
        pass

    def _on_media_configure(self, factory, media):
        """媒体配置回调"""
        try:
            element = media.get_element()
            appsrc = element.get_by_name("source")
            
            if not appsrc:
                print("[ERROR] 无法找到 appsrc 元素")
                return
            
            # 设置 appsrc 属性
            try:
                appsrc.set_property("format", Gst.Format.TIME)
                appsrc.set_property("is-live", True)
                appsrc.set_property("block", True)
                appsrc.set_property("max-bytes", 
                    self.video_source.width * self.video_source.height * 3 * 4)
            except Exception as e:
                print(f"[WARNING] 设置 appsrc 属性失败: {e}")
            
            # 设置 caps
            caps = Gst.Caps.from_string(
                f"video/x-raw,format=BGR,width={self.video_source.width},"
                f"height={self.video_source.height},framerate={self.video_source.fps}/1"
            )
            appsrc.set_property("caps", caps)
            
            # 重置时间戳计数
            with self._lock:
                self._pts = 0
            
            # 连接数据请求信号
            appsrc.connect("need-data", self._need_data_callback)
            appsrc.connect("enough-data", self._enough_data_callback)
            
            print(f"[INFO] 媒体已配置: {self.video_source.width}x{self.video_source.height}@{self.video_source.fps}fps")
        
        except Exception as e:
            print(f"[ERROR] 媒体配置出错: {e}")

    def start(self):
        """启动 RTSP 服务器"""
        try:
            # 创建 RTSP 服务器
            self.server = GstRtspServer.RTSPServer()
            self.server.set_service(str(self.port))
            
            # 创建媒体工厂
            self.factory = GstRtspServer.RTSPMediaFactory()
            
            # 构建 GStreamer 管道：appsrc -> videoconvert -> x264enc -> rtph264pay
            launch_str = (
                f"( appsrc name=source is-live=true format=time ! "
                f"videoconvert ! video/x-raw,format=I420 ! "
                f"x264enc tune=zerolatency bitrate=2000 speed-preset=ultrafast ! "
                f"rtph264pay name=pay0 pt=96 )"
            )
            
            self.factory.set_launch(launch_str)
            self.factory.set_shared(True)
            self.factory.set_eos_shutdown(False)
            
            # 连接媒体配置信号
            self.factory.connect("media-configure", self._on_media_configure)
            
            # 挂载媒体工厂
            mounts = self.server.get_mount_points()
            mounts.add_factory(self.path, self.factory)
            
            # 启动服务器
            self.server.attach(None)
            self._running = True
            
            print(f"[INFO] RTSP 服务器已启动")
            print(f"[INFO] 访问地址: rtsp://localhost:{self.port}{self.path}")
            print(f"[INFO] 使用 ffplay 播放: ffplay rtsp://localhost:{self.port}{self.path}")
            print(f"[INFO] 使用 VLC 播放: rtsp://localhost:{self.port}{self.path}")
            
            # 运行 GLib 事件循环
            self.loop = GLib.MainLoop()
            self.loop.run()
        
        except Exception as e:
            print(f"[ERROR] 启动服务器失败: {e}")
            import traceback
            traceback.print_exc()

    def stop(self):
        """停止 RTSP 服务器"""
        if self.loop:
            self.loop.quit()
        self._running = False
        self.video_source.release()


class MJPEGServerHTTP:
    """基于 HTTP 的 MJPEG 流服务器（RTSP 的简单替代方案）"""
    
    def __init__(self, video_source, port=8080, path="/stream"):
        self.video_source = video_source
        self.port = port
        self.path = path
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self._latest_frame = None

    def _frame_capture_worker(self):
        """后台线程：持续捕获视频帧"""
        while self._running:
            frame = self.video_source.get_frame(timeout=0.05)
            if frame is not None:
                with self._lock:
                    self._latest_frame = frame
            else:
                time.sleep(0.01)

    def start(self):
        """启动 HTTP MJPEG 服务器"""
        try:
            from http.server import HTTPServer, BaseHTTPRequestHandler
        except ImportError:
            print("[ERROR] HTTP 服务器模块不可用")
            return
        
        video_source = self.video_source
        lock = self._lock
        latest_frame_ref = {'frame': None}
        
        class MJPEGHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == video_source.path or self.path == '/':
                    self.send_response(200)
                    self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
                    self.end_headers()
                    
                    print(f"[INFO] 客户端已连接: {self.client_address}")
                    
                    try:
                        while self._running:
                            with lock:
                                frame = self._latest_frame
                            
                            if frame is not None:
                                ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                                if ret:
                                    self.wfile.write(b'--frame\r\n')
                                    self.wfile.write(b'Content-Type: image/jpeg\r\n')
                                    self.wfile.write(f'Content-Length: {len(jpeg)}\r\n\r\n'.encode())
                                    self.wfile.write(jpeg)
                                    self.wfile.write(b'\r\n')
                            
                            time.sleep(1.0 / video_source.fps)
                    except Exception as e:
                        print(f"[WARNING] 客户端断开: {e}")
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                """禁用日志输出"""
                pass
        
        # 设置 _running 标志用于处理器类
        MJPEGHandler._running = True
        MJPEGHandler._latest_frame = None
        
        # 启动帧捕获线程
        self._running = True
        self._thread = threading.Thread(target=self._frame_capture_worker, daemon=True)
        self._thread.start()
        
        # 创建 HTTP 服务器
        server = HTTPServer(('0.0.0.0', self.port), MJPEGHandler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=False)
        server_thread.start()
        
        print(f"[INFO] HTTP MJPEG 服务器已启动 (端口 {self.port})")
        print(f"[INFO] 视频分辨率: {self.video_source.width}x{self.video_source.height}")
        print(f"[INFO] 帧率: {self.video_source.fps} fps")
        print(f"[INFO] 访问地址: http://localhost:{self.port}{self.path}")
        print(f"[INFO] 在浏览器中打开: http://localhost:{self.port}")
        print(f"[INFO] 使用 ffplay: ffplay http://localhost:{self.port}{self.path}")
        print(f"[INFO] 按 Ctrl+C 停止服务器")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[INFO] 收到中断信号，关闭服务器...")
            self.stop()
            server.shutdown()

    def stop(self):
        """停止服务器"""
        self._running = False
        self.video_source.release()
        if self._thread:
            self._thread.join(timeout=5)
        print("[INFO] HTTP 服务器已关闭")


class RTSPServerFFmpeg:
    """基于 FFmpeg 的简单 RTSP 服务器替代方案（用于测试）"""
    
    def __init__(self, video_source, port=8554, path="/live"):
        self.video_source = video_source
        self.port = port
        self.path = path
        self._running = False
        self._thread = None

    def _stream_worker(self):
        """后台线程：推送帧给 FFmpeg"""
        import subprocess
        
        retry_count = 0
        max_retries = 3
        
        while self._running and retry_count < max_retries:
            try:
                # FFmpeg 命令：从 pipe 读取 BGR 帧，编码为 H.264，输出为 RTSP
                cmd = [
                    'ffmpeg',
                    '-f', 'rawvideo',
                    '-pix_fmt', 'bgr24',
                    '-s', f'{self.video_source.width}x{self.video_source.height}',
                    '-framerate', str(self.video_source.fps),  # 使用 -framerate 代替 -r（输入端）
                    '-i', 'pipe:0',
                    '-c:v', 'libx264',
                    '-preset', 'ultrafast',
                    '-b:v', '2000k',
                    '-g', '10',  # 关键帧间隔（GOP）
                    '-f', 'rtsp',
                    '-rtsp_transport', 'tcp',  # 使用 TCP 而不是 UDP
                    f'rtsp://127.0.0.1:{self.port}{self.path}',
                ]
                
                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    bufsize=0  # 无缓冲，提高实时性
                )
                
                print(f"[INFO] FFmpeg 进程已启动 (PID: {proc.pid}, 尝试 {retry_count + 1}/{max_retries})")
                retry_count = 0  # 重置重试计数（成功连接后）
                
                frame_count = 0
                frame_size = self.video_source.width * self.video_source.height * 3  # BGR 每像素 3 字节
                
                while self._running:
                    # 检查 FFmpeg 进程是否还活着
                    if proc.poll() is not None:
                        stderr_output = proc.stderr.read()
                        if stderr_output:
                            print(f"[ERROR] FFmpeg 进程已退出，错误信息: {stderr_output.decode('utf-8', errors='ignore')}")
                        else:
                            print("[ERROR] FFmpeg 进程已退出")
                        break
                    
                    frame = self.video_source.get_frame(timeout=0.05)
                    if frame is not None:
                        try:
                            # 确保帧大小正确
                            if frame.nbytes != frame_size:
                                print(f"[WARNING] 帧大小不匹配: 期望 {frame_size}，实际 {frame.nbytes}")
                                frame = cv2.resize(frame, (self.video_source.width, self.video_source.height))
                            
                            proc.stdin.write(frame.tobytes())
                            frame_count += 1
                            
                            # 每 30 帧打印一条日志
                            if frame_count % 30 == 0:
                                print(f"[INFO] 已推送 {frame_count} 帧")
                        
                        except BrokenPipeError:
                            print("[WARNING] FFmpeg 管道已断开，尝试重新连接...")
                            break
                        except IOError as e:
                            print(f"[WARNING] 写入管道失败: {e}，尝试重新连接...")
                            break
                    else:
                        time.sleep(0.01)
                
                # 正常关闭 FFmpeg
                try:
                    proc.stdin.close()
                except:
                    pass
                
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                
                if not self._running:
                    break
                
                # 准备重新连接
                retry_count += 1
                if retry_count < max_retries:
                    print(f"[INFO] 等待 2 秒后重新连接... ({retry_count}/{max_retries})")
                    time.sleep(2)
            
            except FileNotFoundError:
                print("[ERROR] FFmpeg 未安装，请运行: sudo apt-get install ffmpeg")
                break
            except Exception as e:
                print(f"[ERROR] FFmpeg 流处理出错: {e}")
                import traceback
                traceback.print_exc()
                
                retry_count += 1
                if retry_count < max_retries:
                    print(f"[INFO] 等待 2 秒后重新连接... ({retry_count}/{max_retries})")
                    time.sleep(2)
        
        if retry_count >= max_retries:
            print(f"[ERROR] FFmpeg 连接失败，已达到最大重试次数 ({max_retries})")
            self._running = False

    def start(self):
        """启动 FFmpeg RTSP 服务器"""
        import subprocess
        
        # 启动 RTSP 服务器（使用 GStreamer RTSP 服务器作为媒介）
        # 如果不可用，直接用 FFmpeg 流
        try:
            # 尝试检查本地 RTSP 服务器是否可用
            result = subprocess.run(['which', 'rtsp-server'], 
                                  capture_output=True, timeout=1)
            if result.returncode != 0:
                print("[INFO] 未找到 RTSP 服务器，使用 FFmpeg 直接流模式")
        except:
            pass
        
        self._running = True
        self._thread = threading.Thread(target=self._stream_worker, daemon=False)
        self._thread.start()
        
        print(f"[INFO] RTSP 服务器已启动 (FFmpeg 后端)")
        print(f"[INFO] 视频分辨率: {self.video_source.width}x{self.video_source.height}")
        print(f"[INFO] 帧率: {self.video_source.fps} fps")
        print(f"[INFO] 访问地址: rtsp://localhost:{self.port}{self.path}")
        print(f"[INFO] 使用 ffplay 播放: ffplay -rtsp_transport tcp rtsp://localhost:{self.port}{self.path}")
        print(f"[INFO] 使用 VLC 播放: rtsp://localhost:{self.port}{self.path}")
        print(f"[INFO] 按 Ctrl+C 停止服务器")
        
        # 主线程保持运行
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[INFO] 收到中断信号，关闭服务器...")
            self.stop()

    def stop(self):
        """停止 RTSP 服务器"""
        self._running = False
        self.video_source.release()
        if self._thread:
            self._thread.join(timeout=5)
        print("[INFO] RTSP 服务器已关闭")


def main():
    parser = argparse.ArgumentParser(description='视频流服务器（RTSP/MJPEG）')
    parser.add_argument('--source', choices=['camera', 'file'], default='camera',
                      help='视频源类型')
    parser.add_argument('--camera-id', type=int, default=0,
                      help='摄像头 ID')
    parser.add_argument('--video-file', type=str,
                      help='视频文件路径 (当 source=file 时使用)')
    parser.add_argument('--port', type=int, default=8554,
                      help='服务器端口')
    parser.add_argument('--path', type=str, default='/live',
                      help='服务路径')
    parser.add_argument('--backend', choices=['gstreamer', 'ffmpeg', 'mjpeg'], 
                      default='gstreamer',
                      help='后端选择 (gstreamer=RTSP+GStreamer, ffmpeg=RTSP+FFmpeg, mjpeg=HTTP MJPEG)')
    
    args = parser.parse_args()
    
    # 选择视频源
    try:
        if args.source == 'camera':
            print(f"[INFO] 使用摄像头 {args.camera_id}")
            video_source = WebcamSource(args.camera_id)
        else:
            if not args.video_file:
                print("[ERROR] 请通过 --video-file 指定视频文件路径")
                sys.exit(1)
            print(f"[INFO] 使用视频文件: {args.video_file}")
            video_source = VideoFileSource(args.video_file)
    except Exception as e:
        print(f"[ERROR] 打开视频源失败: {e}")
        sys.exit(1)
    
    # 选择后端
    try:
        if args.backend == 'gstreamer':
            if not GSTREAMER_AVAILABLE:
                print("[ERROR] GStreamer 未安装，请使用 --backend ffmpeg 或 --backend mjpeg")
                print("[INFO] 安装 GStreamer: sudo apt-get install gstreamer1.0-rtsp-server libgirepository1.0-dev")
                sys.exit(1)
            print("[INFO] 使用 GStreamer RTSP 后端")
            server = RTSPServerGStreamer(video_source, port=args.port, path=args.path)
        elif args.backend == 'ffmpeg':
            print("[INFO] 使用 FFmpeg RTSP 后端")
            server = RTSPServerFFmpeg(video_source, port=args.port, path=args.path)
        else:  # mjpeg
            print("[INFO] 使用 HTTP MJPEG 后端")
            if args.port == 8554:  # 使用默认 RTSP 端口时，改用 MJPEG 默认端口
                args.port = 8080
            server = MJPEGServerHTTP(video_source, port=args.port, path=args.path)
        
        server.start()
    
    except KeyboardInterrupt:
        print("\n[INFO] 收到中断信号，关闭服务器...")
        server.stop()
    except Exception as e:
        print(f"[FATAL] 未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
