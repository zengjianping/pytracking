#!/bin/bash
# WebSocket 脱靶量功能快速启动脚本
# 此脚本演示如何启动完整的 WebSocket 跟踪系统

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

print_header "PyTracking WebSocket 脱靶量功能"

# 1. 检查 Python 环境
print_info "检查 Python 环境..."

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 未找到，请先安装 Python 3"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
print_success "Python $PYTHON_VERSION"

# 2. 检查依赖
print_info "检查必需的 Python 包..."

REQUIRED_PACKAGES=("websocket-client" "websockets" "cv2" "numpy")
MISSING_PACKAGES=()

for package in "${REQUIRED_PACKAGES[@]}"; do
    if python3 -c "import ${package//-/_}" 2>/dev/null; then
        print_success "$package"
    else
        print_warning "$package 未找到"
        MISSING_PACKAGES+=("$package")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    print_info "需要安装缺失的包："
    echo "  pip install ${MISSING_PACKAGES[*]}"
    read -p "现在安装吗? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pip install "${MISSING_PACKAGES[@]}"
        print_success "包安装完成"
    else
        print_warning "跳过安装，某些功能可能无法使用"
    fi
fi

# 3. 显示快速开始
print_header "快速开始"

echo ""
echo "您有几个选择："
echo ""
echo "1. 查看快速开始指南"
echo "   python3 tools/websocket_quick_start.py"
echo ""
echo "2. 启动 WebSocket 接收服务"
echo "   python3 tools/websocket_receiver_example.py"
echo ""
echo "3. 启动跟踪器"
echo "   python3 scripts/run_tracker_with_websocket.py --ws-url ws://localhost:8765"
echo ""
echo "4. 查看完整文档"
echo "   cat docs/WEBSOCKET_OFFSET_TRACKING.md"
echo ""

# 4. 询问用户要进行的操作
read -p "请输入要执行的选项 (1-4)，或按 Enter 退出: " choice

case $choice in
    1)
        print_info "启动快速开始指南..."
        python3 tools/websocket_quick_start.py
        ;;
    2)
        print_info "启动 WebSocket 接收服务..."
        echo "服务将监听 ws://localhost:8765"
        echo "按 Ctrl+C 停止"
        python3 tools/websocket_receiver_example.py
        ;;
    3)
        print_info "启动跟踪器..."
        echo "请确保 WebSocket 接收服务已在另一个终端启动"
        echo "按 Ctrl+C 停止"
        python3 scripts/run_tracker_with_websocket.py --ws-url ws://localhost:8765
        ;;
    4)
        print_info "查看完整文档..."
        less docs/WEBSOCKET_OFFSET_TRACKING.md
        ;;
    *)
        print_info "退出"
        ;;
esac

echo ""
print_header "完成"
print_success "更多信息请查看 docs/WEBSOCKET_OFFSET_TRACKING.md"
