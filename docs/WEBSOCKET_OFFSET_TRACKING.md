## WebSocket 脱靶量实时发送功能

### 📋 功能概述

此功能可以实时计算跟踪目标框相对于图像中心的偏移量（脱靶量），并通过 WebSocket 将数据发送给外部接收服务。所有网络通信都在独立线程中进行，**完全不影响主跟踪线程的性能**。

#### 核心概念

- **脱靶量（Miss Distance）**: 目标框中心相对于图像中心的像素偏移量
- **独立线程**: 使用生产者-消费者模式，主线程只是入队消息，不等待网络传输
- **非阻塞通信**: 基于 Python `Queue` 的线程安全消息队列

---

### 🚀 快速开始

#### 1. 安装依赖

```bash
pip install websocket-client websockets
```

#### 2. 启动 WebSocket 接收服务

在一个终端窗口启动接收服务：

```bash
cd /data/ProjectZKZS/Projects/pytracking

# 默认配置（localhost:8765）
python tools/websocket_receiver_example.py

# 或指定端口
python tools/websocket_receiver_example.py --port 9000

# 或监听所有网络接口
python tools/websocket_receiver_example.py --host 0.0.0.0 --port 8765
```

输出示例：
```
============================================================
WebSocket 脱靶量接收服务启动
监听地址: ws://localhost:8765
开始时间: 2024-01-02 10:30:45
============================================================
等待客户端连接...
[2024-01-02 10:31:15.234] [INFO] 客户端已连接: 127.0.0.1:54321
[2024-01-02 10:31:15.456] [INFO] Frame #   1 | Object 0 | Offset: (  50.5, -30.2) | Distance:  58.7px
[2024-01-02 10:31:15.489] [INFO] Frame #   2 | Object 0 | Offset: (  52.3, -28.5) | Distance:  59.2px
```

#### 3. 在另一个终端运行跟踪器

```bash
# 从 RTSP 流进行跟踪
python scripts/run_tracker_with_websocket.py \
    --rtsp-url rtsp://localhost:8554/live \
    --ws-url ws://localhost:8765

# 或从本地视频文件
python scripts/run_tracker_with_websocket.py \
    --video-file /path/to/video.mp4 \
    --ws-url ws://localhost:8765

# 或从摄像头
python scripts/run_tracker_with_websocket.py \
    --ws-url ws://localhost:8765
```

---

### 📡 WebSocket 消息格式

每个跟踪帧都会发送一条 JSON 格式的消息：

```json
{
  "type": "tracking_offset",
  "frame_number": 42,
  "object_id": 0,
  "offset": {
    "x": -50.5,
    "y": 30.2,
    "distance": 59.2
  },
  "target_center": {
    "x": 640.5,
    "y": 400.2
  },
  "image_center": {
    "x": 640.0,
    "y": 360.0
  },
  "image_size": {
    "width": 1280,
    "height": 720
  },
  "timestamp": 1704063600.123,
  "confidence": 0.95
}
```

#### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | str | 消息类型，固定为 "tracking_offset" |
| `frame_number` | int | 当前帧号 |
| `object_id` | int | 跟踪目标 ID |
| `offset.x` | float | 目标中心相对图像中心的 X 偏移（像素） |
| `offset.y` | float | 目标中心相对图像中心的 Y 偏移（像素） |
| `offset.distance` | float | 欧氏距离：√(x² + y²)（像素） |
| `target_center.x` | float | 目标框中心 X 坐标 |
| `target_center.y` | float | 目标框中心 Y 坐标 |
| `image_center.x` | float | 图像中心 X 坐标 |
| `image_center.y` | float | 图像中心 Y 坐标 |
| `image_size.width` | int | 图像宽度（像素） |
| `image_size.height` | int | 图像高度（像素） |
| `timestamp` | float | Unix 时间戳 |
| `confidence` | float | 跟踪置信度（可选） |

---

### 💻 Python 集成示例

#### 基础用法

```python
from pytracking.evaluation.tracker import Tracker

# 创建跟踪器，指定 WebSocket 服务器地址
tracker = Tracker(
    'dimp',                      # 跟踪器名称
    'dimp50',                    # 参数配置
    ws_url='ws://localhost:8765' # WebSocket 服务器地址
)

# 运行跟踪
tracker.run_video_generic(
    rtsp_url='rtsp://localhost:8554/live'
)
```

#### 禁用 WebSocket（可选）

```python
# 如果不指定 ws_url 或设为 None，WebSocket 功能会被禁用
tracker = Tracker('dimp', 'dimp50')  # ws_url 默认为 None
tracker.run_video_generic(rtsp_url='rtsp://localhost:8554/live')
```

#### 自定义接收器示例

```python
import asyncio
import json
import websockets

async def receive_offset_data():
    """简单的 WebSocket 接收器示例"""
    uri = "ws://localhost:8765"
    
    async with websockets.connect(uri) as websocket:
        print(f"连接到 {uri}")
        
        async for message in websocket:
            data = json.loads(message)
            
            # 获取脱靶量信息
            offset = data['offset']
            print(f"Frame {data['frame_number']}: "
                  f"offset=({offset['x']:.1f}, {offset['y']:.1f}) "
                  f"distance={offset['distance']:.1f}px")

# 运行
asyncio.run(receive_offset_data())
```

---

### 🏗️ 实现架构

#### 线程安全设计

采用**生产者-消费者模式**：

```
主跟踪线程（Producer）
    ↓ (非阻塞入队)
  Queue(maxsize=100)
    ↓
WebSocket 发送线程（Consumer）
    ↓ (独立处理网络I/O)
WebSocket 服务器
```

**优势：**
- ✅ 主线程性能零影响（入队操作 < 1ms）
- ✅ 网络延迟完全隔离
- ✅ 自动消息队列管理
- ✅ 线程安全，无竞争条件

#### 消息队列特性

- **队列大小**: 最多 100 条消息
- **超出时行为**: 丢弃最早消息（防止内存溢出）
- **超时处理**: 每条消息 1.0 秒发送超时
- **错误恢复**: 网络错误自动重试

---

### ⚙️ 配置参数

#### 跟踪器初始化参数

```python
Tracker(
    name: str,                  # 跟踪器名称（如 'dimp'）
    parameter_name: str,        # 参数配置（如 'dimp50'）
    run_id: str = None,        # 运行 ID（可选）
    display_name: str = None,  # 显示名称（可选）
    ws_url: str = None,        # WebSocket 服务器地址（可选）
)
```

#### 视频源参数

```python
tracker.run_video_generic(
    # 视频源（以下选一个）
    videofilepath: str = None,  # 本地视频文件路径
    rtsp_url: str = None,       # RTSP 流地址
    camera_id: int = 0,         # 摄像头 ID
    
    # 其他参数
    debug: int = 0,             # 调试级别（0-3）
    save_results: bool = False, # 是否保存结果
    expand_roi: bool = False,   # 是否扩展感兴趣区域
    tracker_type: str = 'none', # 跟踪器类型标签
)
```

---

### 📊 性能指标

#### 资源占用

| 指标 | 数值 | 说明 |
|------|------|------|
| 队列消息大小 | ~500 bytes | 平均每条 JSON 消息 |
| 队列内存占用 | ~50 KB | 100 条消息上限 |
| 发送线程 CPU | < 0.1% | 1s 超时的空闲线程 |
| 入队延迟 | < 1 ms | 非阻塞入队操作 |

#### 吞吐量

对于 30 FPS 视频：
- **消息发送率**: 30 条/秒
- **每秒带宽**: ~15 KB/s（无压缩）
- **典型延迟**: 10-100 ms（取决于网络）

---

### 🐛 故障排除

#### 问题 1: 连接超时

```
[ERROR] 连接 ws://localhost:8765 失败: [Errno 111] Connection refused
```

**解决方案：**
1. 确认接收服务已启动
2. 检查防火墙设置
3. 确认 WebSocket URL 正确

#### 问题 2: 消息丢失

```
[WARNING] 队列已满，丢弃消息
```

**原因**: WebSocket 网络速度慢，接收端处理不够快

**解决方案：**
1. 提升接收端处理速度
2. 减少跟踪帧率（使用视频格式而非 RTSP）
3. 在接收端添加消息缓冲

#### 问题 3: 脱靶量为 0

**原因**: 目标正好在图像中心

**说明**: 这是正常的！说明跟踪效果最好

#### 问题 4: 脱靶量异常大

**原因**: 可能是：
1. 目标框跟踪漂移
2. 目标移出视野
3. 跟踪失败

**调试方法**:
```python
# 在接收器中打印详细信息
print(f"目标中心: {data['target_center']}")
print(f"图像中心: {data['image_center']}")
print(f"图像大小: {data['image_size']}")
```

---

### 🔧 自定义开发

#### 创建自己的接收器

```python
import json
import asyncio
import websockets

class CustomOffsetReceiver:
    async def handle_message(self, message_str: str):
        """处理每条消息"""
        data = json.loads(message_str)
        
        # 提取脱靶量
        offset_x = data['offset']['x']
        offset_y = data['offset']['y']
        distance = data['offset']['distance']
        
        # 自定义处理逻辑
        await self.process_offset(offset_x, offset_y, distance)
    
    async def process_offset(self, x: float, y: float, distance: float):
        """自定义处理逻辑"""
        # 例如：
        # - 控制云台（PTZ）
        # - 调整虚拟焦点
        # - 记录日志
        # - 触发告警
        pass

    async def start(self, uri: str = "ws://localhost:8765"):
        async with websockets.serve(
            self.handler,
            uri.split('//')[1].split(':')[0],
            int(uri.split(':')[-1])
        ):
            await asyncio.Future()  # 永不停止

    async def handler(self, websocket, path):
        async for message in websocket:
            await self.handle_message(message)

# 使用
receiver = CustomOffsetReceiver()
asyncio.run(receiver.start("ws://0.0.0.0:8765"))
```

#### 修改消息格式

如需修改发送的消息字段，编辑 `pytracking/evaluation/tracker.py` 中的 `WebSocketSender.send_offset()` 方法。

---

### 📝 完整工作流示例

#### 终端 1: 启动 WebSocket 接收服务

```bash
$ python tools/websocket_receiver_example.py --port 8765

============================================================
WebSocket 脱靶量接收服务启动
监听地址: ws://localhost:8765
开始时间: 2024-01-02 10:30:45
============================================================
等待客户端连接...
```

#### 终端 2: 启动 RTSP 流服务（可选）

```bash
$ ./scripts/rtsp_server.sh
[INFO] RTSP 服务器启动于 rtsp://localhost:8554
```

#### 终端 3: 运行跟踪器

```bash
$ python scripts/run_tracker_with_websocket.py \
    --rtsp-url rtsp://localhost:8554/live \
    --ws-url ws://localhost:8765 \
    --tracker-name dimp \
    --param-name dimp50

============================================================
PyTracking 跟踪器（带 WebSocket 脱靶量发送）
============================================================
跟踪器: dimp (dimp50)
WebSocket 服务器: ws://localhost:8765
视频源: RTSP 流 (rtsp://localhost:8554/live)
============================================================
```

#### 观察接收服务的输出

```
[2024-01-02 10:31:15.234] [INFO] 客户端已连接: 127.0.0.1:54321
[2024-01-02 10:31:15.456] [INFO] Frame #   1 | Object 0 | Offset: (  50.5, -30.2) | Distance:  58.7px
[2024-01-02 10:31:15.489] [INFO] Frame #   2 | Object 0 | Offset: (  52.3, -28.5) | Distance:  59.2px
[2024-01-02 10:31:15.521] [INFO] Frame #   3 | Object 0 | Offset: (  51.8, -29.1) | Distance:  58.9px
...
[2024-01-02 10:31:16.023] [INFO] 📊 Statistics (last 30 frames): Avg Distance: 58.5px | Max: 62.3px | Avg Offset: (51.2, -29.5)
```

---

### ✅ 检查清单

部署前确认以下事项：

- [ ] 已安装 `websocket-client` 库
- [ ] 已安装 `websockets` 库
- [ ] WebSocket 服务器已启动
- [ ] WebSocket URL 正确（主机名、端口）
- [ ] 防火墙允许 WebSocket 连接
- [ ] 主跟踪线程性能正常（不受网络延迟影响）
- [ ] 接收端已准备好处理消息

---

### 📚 相关文件

| 文件 | 说明 |
|------|------|
| `pytracking/evaluation/tracker.py` | WebSocketSender 类和集成代码 |
| `scripts/run_tracker_with_websocket.py` | 使用 WebSocket 的跟踪脚本 |
| `tools/websocket_receiver_example.py` | WebSocket 接收服务示例 |
| `docs/rtsp_tracking/WEBSOCKET_OFFSET_TRACKING.md` | 本文档 |

---

### 📖 更多资源

- [websocket-client 文档](https://github.com/websocket-client/websocket-client)
- [websockets 库文档](https://websockets.readthedocs.io/)
- [JSON RPC 2.0 规范](https://www.jsonrpc.org/specification)

---

### 🎯 常见用途

#### 1. **云台跟踪（PTZ 联动）**

```python
# 在接收器中
if offset_x > 50:  # 目标在右边
    ptz.pan_right()
elif offset_x < -50:  # 目标在左边
    ptz.pan_left()
```

#### 2. **虚拟焦点调整**

```python
# 调整虚拟焦点
focus_x = image_center_x + offset_x
focus_y = image_center_y + offset_y
camera.set_focus(focus_x, focus_y)
```

#### 3. **精准定位**

```python
# 转换为世界坐标
world_offset_x = offset_x * pixel_to_meter_ratio
world_offset_y = offset_y * pixel_to_meter_ratio
print(f"目标距中心 {world_offset_x:.2f}m, {world_offset_y:.2f}m")
```

#### 4. **数据记录和分析**

```python
# 记录脱靶量历史用于分析跟踪效果
offsets.append({
    'frame': frame_number,
    'distance': distance,
    'x': offset_x,
    'y': offset_y
})
```

---

**文档版本**: 1.0  
**最后更新**: 2024-01-02  
**状态**: ✅ 完成
