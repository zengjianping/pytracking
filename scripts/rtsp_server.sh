#!/bin/bash

# install gstreamer
sudo apt-get install libgirepository1.0-dev gstreamer1.0-libav gstreamer1.0-plugins-bad gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly gstreamer1.0-rtsp gir1.2-gst-rtsp-server-1.0 libgirepository1.0-dev
sudo apt-get install libgirepository1.0-dev libcairo2-dev pkg-config python3-dev gir1.2-glib-2.0
pip install PyGObject==3.34.0

# 下载（以 Linux amd64 为例，其他平台请替换对应版本）
wget https://github.com/bluenviron/mediamtx/releases/download/v1.8.5/mediamtx_v1.8.5_linux_amd64.tar.gz
tar -xzf mediamtx_v1.8.5_linux_amd64.tar.gz
./mediamtx

ffmpeg -re -stream_loop -1 -i datas/videos/TestData/反无-20260224/ccd1/可见光视频-ab5944c9a3ce.mp4 -c copy -f rtsp rtsp://localhost:8554/live

# VLC播放器
vlc rtsp://localhost:8554/live

# FFplay
ffplay rtsp://localhost:8554/live -fflags nobuffer -flags low_delay

# 默认使用从摄像头直播
python3 tools/rtsp_server.py --source camera --backend gstreamer
python3 tools/rtsp_server.py --source camera --backend ffmpeg

# 循环播放视频文件
python3 tools/rtsp_server.py --source file --video-file /path/to/video.mp4
python3 tools/rtsp_server.py --source file --video-file datas/videos/TestData/反无-20260224/ccd1/可见光视频-ab5944c9a3ce.mp4

# 自定义端口和路径
python3 tools/rtsp_server.py --source camera --port 5554 --path /stream

