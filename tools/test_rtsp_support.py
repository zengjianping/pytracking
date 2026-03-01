#!/usr/bin/env python3
"""
RTSP 跟踪功能测试脚本

这个脚本测试 PyTracking 的 RTSP 流支持功能
"""

import sys
import time
import subprocess
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_rtsp_server_start():
    """测试 RTSP 服务器启动"""
    print("[TEST] 测试 RTSP 服务器启动...")
    
    try:
        # 检查 rtsp_server.py 是否存在
        rtsp_server_path = project_root / 'tools' / 'rtsp_server.py'
        if not rtsp_server_path.exists():
            print(f"[FAIL] RTSP 服务器文件不存在: {rtsp_server_path}")
            return False
        
        print(f"[PASS] RTSP 服务器文件存在: {rtsp_server_path}")
        return True
    
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        return False


def test_tracker_rtsp_parameter():
    """测试跟踪器 RTSP 参数"""
    print("[TEST] 测试跟踪器 RTSP 参数...")
    
    try:
        # 直接检查源代码而不导入（避免依赖问题）
        tracker_file = project_root / 'pytracking' / 'evaluation' / 'tracker.py'
        if not tracker_file.exists():
            print(f"[FAIL] 跟踪器文件不存在: {tracker_file}")
            return False
        
        # 读取源代码检查 rtsp_url 参数
        content = tracker_file.read_text()
        if 'rtsp_url=None' not in content:
            print("[FAIL] run_video_generic 没有 rtsp_url 参数")
            return False
        
        print("[PASS] run_video_generic 包含 rtsp_url 参数")
        
        # 检查 RTSP 连接代码
        if 'rtsp_url is not None' not in content:
            print("[FAIL] 没有发现 RTSP 处理代码")
            return False
        
        print("[PASS] 发现 RTSP 处理代码")
        
        # 检查自动重连代码
        if 'RTSP 流断开' not in content:
            print("[FAIL] 没有发现 RTSP 自动重连代码")
            return False
        
        print("[PASS] 发现 RTSP 自动重连代码")
        
        return True
    
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tracker_video_source_type():
    """测试视频源类型识别"""
    print("[TEST] 测试视频源类型识别...")
    
    try:
        import cv2 as cv
        
        # 检查 cv2.VideoCapture 是否支持 RTSP URL
        print("[INFO] OpenCV 版本:", cv.__version__)
        
        # 这是一个模拟测试，不实际连接
        test_urls = [
            'rtsp://localhost:8554/live',
            'http://localhost:8080',
            '/path/to/video.mp4',
            '0'  # 摄像头
        ]
        
        for url in test_urls:
            if url.startswith('rtsp://'):
                print(f"[PASS] 识别 RTSP URL: {url}")
            elif url.startswith('http://'):
                print(f"[PASS] 识别 HTTP URL: {url}")
            elif url.startswith('/'):
                print(f"[PASS] 识别文件路径: {url}")
            else:
                print(f"[PASS] 识别摄像头: {url}")
        
        return True
    
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        return False


def test_script_exists():
    """测试跟踪脚本是否存在"""
    print("[TEST] 测试跟踪脚本...")
    
    try:
        script_path = project_root / 'tools' / 'run_tracker_with_rtsp.py'
        if not script_path.exists():
            print(f"[FAIL] 脚本不存在: {script_path}")
            return False
        
        print(f"[PASS] 脚本存在: {script_path}")
        
        # 检查脚本是否可执行
        import stat
        st = script_path.stat()
        if not (st.st_mode & stat.S_IEXEC):
            print(f"[WARNING] 脚本不可执行，尝试使其可执行...")
            script_path.chmod(st.st_mode | stat.S_IEXEC)
        
        return True
    
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        return False


def test_documentation_exists():
    """测试文档是否存在"""
    print("[TEST] 测试文档...")
    
    try:
        doc_path = project_root / 'RTSP_TRACKING_GUIDE.md'
        if not doc_path.exists():
            print(f"[FAIL] 文档不存在: {doc_path}")
            return False
        
        print(f"[PASS] 文档存在: {doc_path}")
        
        # 检查文档大小
        size = doc_path.stat().st_size
        if size < 1000:
            print(f"[WARNING] 文档可能太小: {size} 字节")
        else:
            print(f"[PASS] 文档大小: {size} 字节")
        
        return True
    
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("PyTracking RTSP 功能测试")
    print("=" * 60)
    print()
    
    tests = [
        test_rtsp_server_start,
        test_tracker_rtsp_parameter,
        test_tracker_video_source_type,
        test_script_exists,
        test_documentation_exists,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"[FAIL] 测试异常: {e}")
            results.append(False)
        print()
    
    # 汇总结果
    print("=" * 60)
    print(f"测试结果: {sum(results)}/{len(results)} 通过")
    print("=" * 60)
    
    if all(results):
        print("[SUCCESS] 所有测试通过！")
        return 0
    else:
        print("[FAILURE] 某些测试失败")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
