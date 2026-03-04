#!/bin/bash
#ALGO="keep_track-default"
#ALGO="dimp-dimp50"
#ALGO="tomp-tomp101"
ALGO="tomp-tomp50"
#ALGO="eco-default"
#ALGO="atom-default"
#ALGO="rts-rts50"
#ALGO="lwl-lwl_boxinit"

arr=(${ALGO//-/ })
tracker_name=${arr[0]}
tracker_param=${arr[1]}

#video="datas/videos/UavData/uav/复杂背景/ccd/20250912_143012196_chnccd2.mp4"
#video="datas/videos/UavData/uav/复杂背景/ir/20250912_143012156_chnir1.mp4"
#video="datas/videos/UavData/uav2.5/多旋翼/ccd/ccd12.mp4"

#video="datas/videos/UavData/UAV2.6/多旋翼/ir/20250912_143012156_chnir2.mp4"
#video="datas/videos/UavData/UAV2.6/多旋翼/ir/20250926_191414923_chnir1.mp4"
#video="datas/videos/UavData/UAV2.6/多旋翼/ir/20250927_200126080_chnir1.mp4"
video="datas/videos/UavData/UAV2.6/多旋翼/ccd/ccd10.mp4"
video="datas/videos/UavData/UAV2.6/多旋翼/ccd/ccd14.mp4"

video="datas/videos/UavData/UAV2.6/固定翼/ccd/ccd6.mp4"
video="datas/videos/UavData/UAV2.6/固定翼/ccd/ccd7.mp4"
video="datas/videos/UavData/UAV2.6/固定翼/ir/ir4.mp4"
video="datas/videos/UavData/UAV2.6/固定翼/ir/ir6.mp4"

video="datas/videos/TestData/反无-20260224/ir1/红外视频-456b75e696a0.mp4"
video="datas/videos/TestData/反无-20260224/ir1/红外视频-9e250143244e.mp4"

video="datas/videos/TestData/反无-20260224/ir2/红外视频-e2d2e2d16316.mp4"

video="datas/videos/TestData/反无-20260224/ccd/可见光视频-649258d6481b.mp4"
video="datas/videos/TestData/反无-20260224/ccd1/可见光视频-b3da05532276.mp4"
video="datas/videos/TestData/反无-20260224/ccd2/可见光视频-f87fd5c424fe.mp4"
video="datas/videos/TestData/反无-20260224/ccd1/可见光视频-ab5944c9a3ce.mp4"

#python pytracking/run_video.py $tracker_name $tracker_param $video
python pytracking/run_video.py $tracker_name $tracker_param $video --save_result


