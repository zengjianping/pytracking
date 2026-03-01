#!/bin/bash
#ALGO="keep_track-default_fast"
#ALGO="rts-rts50"
#ALGO="lwl-lwl_boxinit"
#ALGO="eco-default"
#ALGO="atom-default"
ALGO="tomp-tomp50"
#ALGO="tomp-tomp101"
#ALGO="dimp-dimp50"

arr=(${ALGO//-/ })
tracker_name=${arr[0]}
tracker_param=${arr[1]}

python3 tools/run_tracker_with_rtsp.py \
    --tracker-name $tracker_name \
    --param-name $tracker_param \
    --rtsp-url rtsp://localhost:8554/live \
    --ws-url ws://localhost:8765

