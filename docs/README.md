# PyTracking RTSP 文档归档

此目录包含 PyTracking RTSP 功能的参考文档。这些是原有的分散文档，已整合到主指南 `RTSP_TRACKING_GUIDE.md` 中。

## 📚 文档列表

### 主文档 ⭐
位置：`../RTSP_TRACKING_GUIDE.md`

这是完整的综合指南，包含所有必要信息：
- 快速开始（3 步，5 分钟）
- 详细用法（4 种视频源）
- 代码示例
- 故障排除
- 常见问题解答
- 性能指标

**推荐：新用户和大多数使用场景都应从这个文件开始。**

---

### 参考文档（归档）

#### 1. RTSP_QUICK_REFERENCE.md
**大小：** 5.2 KB  
**内容：** 快速查询参考

- 快速命令速查
- 常用 RTSP URL 格式
- 简明参数列表
- 常见错误快速解决

**何时使用：** 当你需要快速查找某个命令或参数时

---

#### 2. RTSP_IMPLEMENTATION_SUMMARY.md
**大小：** 7.5 KB  
**内容：** 技术实现细节

- 架构设计说明
- 后端对比分析
- 性能优化方法
- 依赖和兼容性
- 技术细节

**何时使用：** 当你想理解技术实现或进行高级定制时

---

#### 3. PROJECT_COMPLETION_REPORT.md
**大小：** 9.3 KB  
**内容：** 项目完成报告

- 项目概述和目标
- 功能清单
- 完成统计
- 性能测试结果
- 验收标准
- 版本信息

**何时使用：** 当你需要了解项目的完整历程和最终状态时

---

#### 4. WEBSOCKET_OFFSET_TRACKING.md ⭐ 新增
**大小：** 15+ KB  
**内容：** WebSocket 脱靶量实时发送

- 功能概述和快速开始
- WebSocket 消息格式详解
- Python 集成示例
- 实现架构（线程安全设计）
- 配置参数说明
- 性能指标
- 故障排除指南
- 云台联动、虚拟焦点等应用示例

**何时使用：** 当你需要实时获取目标偏离图像中心的位移量数据时

---

## 🗂️ 文档使用指南

### 快速开始用户
```
1. 打开 ../RTSP_TRACKING_GUIDE.md
2. 找到"快速开始"章节
3. 按 3 步操作
```

### 需要完整信息的用户
```
1. 阅读 ../RTSP_TRACKING_GUIDE.md 全文
2. 遇到特定问题时查看"故障排除"章节
3. 有高级需求时查看本目录的参考文档
```

### 开发者和维护人员
```
1. 查看 ../RTSP_TRACKING_GUIDE.md 中的"核心改动"
2. 查看 RTSP_IMPLEMENTATION_SUMMARY.md 了解技术细节
3. 参考 PROJECT_COMPLETION_REPORT.md 了解完整的验收标准
```

---

## 📊 文件统计

| 文件 | 大小 | 行数 | 用途 |
|------|------|------|------|
| RTSP_QUICK_REFERENCE.md | 5.2 KB | 207 | 快速参考 |
| RTSP_IMPLEMENTATION_SUMMARY.md | 7.5 KB | 250+ | 技术细节 |
| PROJECT_COMPLETION_REPORT.md | 9.3 KB | 300+ | 项目报告 |
| WEBSOCKET_OFFSET_TRACKING.md | 15+ KB | 400+ | WebSocket 脱靶量 |
| **总计** | **37+ KB** | **1150+** | 参考资料 |

---

## 🎯 推荐阅读顺序

**第一次使用：**
1. 📖 ../RTSP_TRACKING_GUIDE.md - 快速开始章节
2. 💻 运行示例命令
3. 🔍 查看故障排除章节（如有问题）

**深入学习：**
1. 📖 ../RTSP_TRACKING_GUIDE.md - 详细用法章节
2. 📚 RTSP_IMPLEMENTATION_SUMMARY.md - 技术背景
3. 📊 PROJECT_COMPLETION_REPORT.md - 性能数据

**维护和扩展：**
1. 📖 ../RTSP_TRACKING_GUIDE.md - 核心改动章节
2. 📚 RTSP_IMPLEMENTATION_SUMMARY.md - 架构设计
3. 🧪 运行 test_rtsp_support.py 验证功能

---

## ✨ 功能总览

本 RTSP 功能包括：

✅ **RTSP 视频流读取**
- 本地 RTSP 服务器
- 远程 IP 摄像头
- 带认证的连接

✅ **自动重连机制**
- 连接失败重试（最多 10 次）
- 流断开自动重连
- 指数退避延迟

✅ **三种后端支持**
- GStreamer（低延迟）
- FFmpeg（高兼容性）
- HTTP MJPEG（纯 Python）

✅ **完整的文档**
- 快速开始指南
- 详细使用教程
- 代码示例
- 故障排除指南
- 常见问题解答

✅ **自动化测试**
- 5 个测试用例
- 100% 通过率
- 功能验证

---

## 🔗 快速链接

- **主文档：** `../RTSP_TRACKING_GUIDE.md`
- **示例脚本：** `../EXAMPLES.sh`
- **核心代码：** `../pytracking/evaluation/tracker.py`
- **服务器：** `../tools/rtsp_server.py`
- **CLI 工具：** `../scripts/run_tracker_with_rtsp.py`
- **测试脚本：** `../scripts/test_rtsp_support.py`

---

## 📅 文档信息

**创建日期：** 2024 年 3 月 1 日  
**最后更新：** 2024 年 3 月 1 日  
**版本：** v1.0.0  
**状态：** ✅ 生产就绪

---

## 📞 需要帮助？

1. **查看主文档：** `../RTSP_TRACKING_GUIDE.md`
2. **查看快速参考：** `RTSP_QUICK_REFERENCE.md`
3. **运行自动化测试：** `python3 ../scripts/test_rtsp_support.py`
4. **查看使用示例：** `../EXAMPLES.sh`

---

**提示：** 这些参考文档包含了原有分散文档中的所有信息，都已整合到主文档 `RTSP_TRACKING_GUIDE.md` 中。建议优先使用主文档以获得最佳体验。
