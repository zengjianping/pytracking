#!/bin/bash

#RTSP_URL="rtsp://localhost:8554/live"
#WSCK_URL="ws://localhost:8765"

RTSP_URL="rtsp://192.168.1.90:8554/ir/video"
WSCK_URL="ws://192.168.1.90:12345"

#ALGO="keep_track-default"
ALGO="tomp-tomp50"
#ALGO="tomp-tomp101"
#ALGO="dimp-dimp50"

arr=(${ALGO//-/ })
tracker_name=${arr[0]}
tracker_param=${arr[1]}

python3 tools/run_tracker_with_rtsp.py \
    --tracker-name $tracker_name \
    --param-name $tracker_param \
    --rtsp-url $RTSP_URL \
    --ws-url $WSCK_URL

