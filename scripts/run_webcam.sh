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

python pytracking/run_webcam.py $tracker_name $tracker_param \
    --debug 1 \
    --use_visdom true \
    --visdom_server localhost \
    --visdom_port 8097

