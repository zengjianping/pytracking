import importlib
import os
import numpy as np
from collections import OrderedDict
from pytracking.evaluation.environment import env_settings
import time
import cv2 as cv
from pytracking.utils.visdom import Visdom
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pytracking.utils.plotting import draw_figure, overlay_mask
from pytracking.utils.convert_vot_anno_to_rect import convert_vot_anno_to_rect
from ltr.data.bounding_box_utils import masks_to_bboxes
from pytracking.evaluation.multi_object_wrapper import MultiObjectWrapper
from pathlib import Path
import torch
import yaml, cv2
import threading
import json
import websocket
from queue import Queue


_tracker_disp_colors = [(0, 255, 0), (0, 0, 255), (255, 0, 0),
                         (0, 255, 128), (255, 128, 0), (128, 0, 255)]


class WebSocketSender:
    """独立线程中发送 WebSocket 消息的工具类"""
    
    def __init__(self, ws_url=None):
        """
        初始化 WebSocket 发送器
        args:
            ws_url: WebSocket 服务器地址，格式: ws://host:port
        """
        self.ws_url = ws_url
        self.message_queue = Queue(maxsize=100)  # 限制队列大小
        self.send_thread = None
        self.running = False
        self.ws_connection = None
        
        if ws_url:
            self.start()
    
    def start(self):
        """启动发送线程"""
        if self.running:
            return
        
        self.running = True
        self.send_thread = threading.Thread(target=self._send_worker, daemon=True)
        self.send_thread.start()
        print(f"[WebSocket] 发送线程已启动，地址: {self.ws_url}")
    
    def _send_worker(self):
        """发送线程的工作函数"""
        while self.running:
            try:
                # 从队列获取消息（带超时以便定期检查 running 状态）
                message = self.message_queue.get(timeout=1.0)
                
                if message is None:  # None 作为停止信号
                    break

                #print(f"[WebSocket] 发送消息: {message}")
                self._send_message(message)
                
            except Exception as e:
                #if self.running:
                #    print(f"[WebSocket] 队列获取错误: {e}")
                continue
    
    def _send_message(self, message):
        """发送单个消息到 WebSocket 服务器"""
        try:
            # 连接到 WebSocket 服务器
            ws = websocket.create_connection(self.ws_url, timeout=5)
            ws.send(json.dumps(message))
            ws.close()
            
        except Exception as e:
            print(f"[WebSocket] 发送失败: {e}")

    def send_start(self, frame_number, object_state, object_id):
        """
        发送目标框起始信息
        """
        message = {
            'msg': 'pc_track_ctrl',
            'state': 0,
            'x': float(object_state[0]),
            'y': float(object_state[1]),
            'w': float(object_state[2]),
            'h': float(object_state[3])
        }

        try:
            self.message_queue.put_nowait(message)
        except Exception as e:
            print(f"[WebSocket] 队列已满或其他错误: {e}")

    def send_stop(self):
        """
        发送目标框结束信息
        """
        message = {
            'msg': 'pc_track_ctrl',
            'state': 1,
            'x': 0,
            'y': 0,
            'w': 0,
            'h': 0
        }

        try:
            self.message_queue.put_nowait(message)
        except Exception as e:
            print(f"[WebSocket] 队列已满或其他错误: {e}")

    def send_offset(self, frame_number, object_state, object_id, offset_x, offset_y, center_x, center_y,
                   image_width, image_height, confidence=None):
        """
        发送目标框脱靶量信息
        args:
            frame_number: 帧号
            object_id: 目标 ID
            offset_x: 目标中心相对图像中心的 X 偏移量（像素）
            offset_y: 目标中心相对图像中心的 Y 偏移量（像素）
            center_x: 目标中心 X 坐标
            center_y: 目标中心 Y 坐标
            image_width: 图像宽度
            image_height: 图像高度
            confidence: 置信度（可选）
        """
        
        if False:
            message = {
                'type': 'tracking_offset',
                'frame_number': int(frame_number),
                'object_id': int(object_id),
                'offset': {
                    'x': float(offset_x),
                    'y': float(offset_y),
                    'distance': float(np.sqrt(offset_x**2 + offset_y**2))  # 欧氏距离
                },
                'target_center': {
                    'x': float(center_x),
                    'y': float(center_y)
                },
                'image_center': {
                    'x': float(image_width / 2),
                    'y': float(image_height / 2)
                },
                'image_size': {
                    'width': int(image_width),
                    'height': int(image_height)
                },
                'timestamp': time.time()
            }
            if confidence is not None:
                message['confidence'] = float(confidence)
        else:
            message = {
                'msg': 'pc_track_ctrl',
                'state': 2,
                'x': object_state[0],
                'y': object_state[1],
                'w': object_state[2],
                'h': object_state[3]
            }
        
        try:
            self.message_queue.put_nowait(message)
        except Exception as e:
            print(f"[WebSocket] 队列已满或其他错误: {e}")
    
    def send_frame_info(self, frame_number, tracked_objects):
        """
        发送整帧的跟踪信息
        args:
            frame_number: 帧号
            tracked_objects: 字典，格式 {object_id: {'bbox': [x,y,w,h], 'confidence': score}}
        """
        message = {
            'type': 'frame_info',
            'frame_number': int(frame_number),
            'tracked_objects': tracked_objects,
            'timestamp': time.time()
        }
        
        try:
            self.message_queue.put_nowait(message)
        except Exception as e:
            print(f"[WebSocket] 队列已满或其他错误: {e}")
    
    def stop(self):
        """停止发送线程"""
        if not self.running:
            return
        
        self.running = False
        self.message_queue.put(None)  # 发送停止信号
        
        if self.send_thread:
            self.send_thread.join(timeout=5)
        
        print("[WebSocket] 发送线程已停止")
    
    def is_connected(self):
        """检查是否已配置 WebSocket 地址"""
        return self.ws_url is not None


def trackerlist(name: str, parameter_name: str, run_ids = None, display_name: str = None):
    """Generate list of trackers.
    args:
        name: Name of tracking method.
        parameter_name: Name of parameter file.
        run_ids: A single or list of run_ids.
        display_name: Name to be displayed in the result plots.
    """
    if run_ids is None or isinstance(run_ids, int):
        run_ids = [run_ids]
    return [Tracker(name, parameter_name, run_id, display_name) for run_id in run_ids]


class Tracker:
    """Wraps the tracker for evaluation and running purposes.
    args:
        name: Name of tracking method.
        parameter_name: Name of parameter file.
        run_id: The run id.
        display_name: Name to be displayed in the result plots.
    """

    def __init__(self, name: str, parameter_name: str, run_id: int = None, display_name: str = None, ws_url: str = None):
        assert run_id is None or isinstance(run_id, int)

        self.name = name
        self.parameter_name = parameter_name
        self.run_id = run_id
        self.display_name = display_name
        self.ws_sender = WebSocketSender(ws_url)  # 初始化 WebSocket 发送器

        env = env_settings()
        if self.run_id is None:
            self.results_dir = '{}/{}/{}'.format(env.results_path, self.name, self.parameter_name)
            self.segmentation_dir = '{}/{}/{}'.format(env.segmentation_path, self.name, self.parameter_name)
        else:
            self.results_dir = '{}/{}/{}_{:03d}'.format(env.results_path, self.name, self.parameter_name, self.run_id)
            self.segmentation_dir = '{}/{}/{}_{:03d}'.format(env.segmentation_path, self.name, self.parameter_name, self.run_id)

        tracker_module_abspath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tracker', self.name))
        if os.path.isdir(tracker_module_abspath):
            tracker_module = importlib.import_module('pytracking.tracker.{}'.format(self.name))
            self.tracker_class = tracker_module.get_tracker_class()
        else:
            self.tracker_class = None

        self.visdom = None


    def _init_visdom(self, visdom_info, debug):
        visdom_info = {} if visdom_info is None else visdom_info
        self.pause_mode = False
        self.step = False
        if debug > 0 and visdom_info.get('use_visdom', True):
            try:
                self.visdom = Visdom(debug, {'handler': self._visdom_ui_handler, 'win_id': 'Tracking'},
                                     visdom_info=visdom_info)

                # Show help
                help_text = 'You can pause/unpause the tracker by pressing ''space'' with the ''Tracking'' window ' \
                            'selected. During paused mode, you can track for one frame by pressing the right arrow key.' \
                            'To enable/disable plotting of a data block, tick/untick the corresponding entry in ' \
                            'block list.'
                self.visdom.register(help_text, 'text', 1, 'Help')
            except:
                time.sleep(0.5)
                print('!!! WARNING: Visdom could not start, so using matplotlib visualization instead !!!\n'
                      '!!! Start Visdom in a separate terminal window by typing \'visdom\' !!!')

    def _visdom_ui_handler(self, data):
        if data['event_type'] == 'KeyPress':
            if data['key'] == ' ':
                self.pause_mode = not self.pause_mode

            elif data['key'] == 'ArrowRight' and self.pause_mode:
                self.step = True


    def create_tracker(self, params):
        tracker = self.tracker_class(params)
        tracker.visdom = self.visdom
        return tracker

    def run_sequence(self, seq, visualization=None, debug=None, visdom_info=None, multiobj_mode=None):
        """Run tracker on sequence.
        args:
            seq: Sequence to run the tracker on.
            visualization: Set visualization flag (None means default value specified in the parameters).
            debug: Set debug level (None means default value specified in the parameters).
            visdom_info: Visdom info.
            multiobj_mode: Which mode to use for multiple objects.
        """
        params = self.get_parameters()
        visualization_ = visualization

        debug_ = debug
        if debug is None:
            debug_ = getattr(params, 'debug', 0)
        if visualization is None:
            if debug is None:
                visualization_ = getattr(params, 'visualization', False)
            else:
                visualization_ = True if debug else False

        params.visualization = visualization_
        params.debug = debug_

        self._init_visdom(visdom_info, debug_)
        if visualization_ and self.visdom is None:
            self.init_visualization()

        # Get init information
        init_info = seq.init_info()
        is_single_object = not seq.multiobj_mode

        if multiobj_mode is None:
            multiobj_mode = getattr(params, 'multiobj_mode', getattr(self.tracker_class, 'multiobj_mode', 'default'))

        if multiobj_mode == 'default' or is_single_object:
            tracker = self.create_tracker(params)
        elif multiobj_mode == 'parallel':
            tracker = MultiObjectWrapper(self.tracker_class, params, self.visdom)
        else:
            raise ValueError('Unknown multi object mode {}'.format(multiobj_mode))

        output = self._track_sequence(tracker, seq, init_info)
        return output

    def _track_sequence(self, tracker, seq, init_info):
        # Define outputs
        # Each field in output is a list containing tracker prediction for each frame.

        # In case of single object tracking mode:
        # target_bbox[i] is the predicted bounding box for frame i
        # time[i] is the processing time for frame i
        # segmentation[i] is the segmentation mask for frame i (numpy array)

        # In case of multi object tracking mode:
        # target_bbox[i] is an OrderedDict, where target_bbox[i][obj_id] is the predicted box for target obj_id in
        # frame i
        # time[i] is either the processing time for frame i, or an OrderedDict containing processing times for each
        # object in frame i
        # segmentation[i] is the multi-label segmentation mask for frame i (numpy array)

        output = {'target_bbox': [],
                  'time': [],
                  'segmentation': [],
                  'object_presence_score': []}

        def _store_outputs(tracker_out: dict, defaults=None):
            defaults = {} if defaults is None else defaults
            for key in output.keys():
                val = tracker_out.get(key, defaults.get(key, None))
                if key in tracker_out or val is not None:
                    output[key].append(val)

        # Initialize
        image = self._read_image(seq.frames[0])

        if tracker.params.visualization and self.visdom is None:
            self.visualize(image, init_info.get('init_bbox'))

        start_time = time.time()
        out = tracker.initialize(image, init_info)
        if out is None:
            out = {}

        prev_output = OrderedDict(out)

        init_default = {'target_bbox': init_info.get('init_bbox'),
                        'clf_target_bbox': init_info.get('init_bbox'),
                        'time': time.time() - start_time,
                        'segmentation': init_info.get('init_mask'),
                        'object_presence_score': 1.}

        _store_outputs(out, init_default)

        segmentation = out['segmentation'] if 'segmentation' in out else None
        bboxes = [init_default['target_bbox']]
        if 'clf_target_bbox' in out:
            bboxes.append(out['clf_target_bbox'])
        if 'clf_search_area' in out:
            bboxes.append(out['clf_search_area'])
        if 'segm_search_area' in out:
            bboxes.append(out['segm_search_area'])

        if self.visdom is not None:
            tracker.visdom_draw_tracking(image, bboxes, segmentation)
        elif tracker.params.visualization:
            self.visualize(image, bboxes, segmentation)

        for frame_num, frame_path in enumerate(seq.frames[1:], start=1):
            while True:
                if not self.pause_mode:
                    break
                elif self.step:
                    self.step = False
                    break
                else:
                    time.sleep(0.1)

            image = self._read_image(frame_path)

            start_time = time.time()

            info = seq.frame_info(frame_num)
            info['previous_output'] = prev_output

            out = tracker.track(image, info)
            prev_output = OrderedDict(out)
            _store_outputs(out, {'time': time.time() - start_time})

            segmentation = out['segmentation'] if 'segmentation' in out else None

            bboxes = [out['target_bbox']]
            if 'clf_target_bbox' in out:
                bboxes.append(out['clf_target_bbox'])
            if 'clf_search_area' in out:
                bboxes.append(out['clf_search_area'])
            if 'segm_search_area' in out:
                bboxes.append(out['segm_search_area'])

            if self.visdom is not None:
                tracker.visdom_draw_tracking(image, bboxes, segmentation)
            elif tracker.params.visualization:
                self.visualize(image, bboxes, segmentation)

        for key in ['target_bbox', 'segmentation']:
            if key in output and len(output[key]) <= 1:
                output.pop(key)

        # next two lines are needed for oxuva output format.
        output['image_shape'] = image.shape[:2]
        output['object_presence_score_threshold'] = tracker.params.get('object_presence_score_threshold', 0.55)

        return output

    def run_video_generic(self, debug=None, visdom_info=None, videofilepath=None, optional_box=None, save_results=False,
                          save_result=False, expand_roi=False, tracker_type='none', rtsp_url=None):
        """Run the tracker with the webcam, a provided video file, or RTSP stream.
        args:
            debug: Debug level.
            videofilepath: Path to video file (optional).
            rtsp_url: RTSP stream URL (optional), e.g., 'rtsp://localhost:8554/live'.
        """

        params = self.get_parameters()

        debug_ = debug
        if debug is None:
            debug_ = getattr(params, 'debug', 0)
        params.debug = debug_

        params.tracker_name = self.name
        params.param_name = self.parameter_name

        self._init_visdom(visdom_info, debug_)

        multiobj_mode = getattr(params, 'multiobj_mode', getattr(self.tracker_class, 'multiobj_mode', 'default'))

        if multiobj_mode == 'default':
            tracker = self.create_tracker(params)
            if hasattr(tracker, 'initialize_features'):
                tracker.initialize_features()
        elif multiobj_mode == 'parallel':
            tracker = MultiObjectWrapper(self.tracker_class, params, self.visdom, fast_load=True)
        else:
            raise ValueError('Unknown multi object mode {}'.format(multiobj_mode))

        class UIControl:
            def __init__(self):
                self.mode = 'init'  # init, select, track
                self.target_tl = (-1, -1)
                self.target_br = (-1, -1)
                self.new_init = False

            def mouse_callback(self, event, x, y, flags, param):
                if event == cv.EVENT_LBUTTONDOWN and self.mode == 'init':
                    self.target_tl = (x, y)
                    self.target_br = (x, y)
                    self.mode = 'select'
                elif event == cv.EVENT_MOUSEMOVE and self.mode == 'select':
                    self.target_br = (x, y)
                elif event == cv.EVENT_LBUTTONDOWN and self.mode == 'select':
                    self.target_br = (x, y)
                    self.mode = 'init'
                    self.new_init = True

            def get_tl(self):
                return self.target_tl if self.target_tl[0] < self.target_br[0] else self.target_br

            def get_br(self):
                return self.target_br if self.target_tl[0] < self.target_br[0] else self.target_tl

            def get_bb(self):
                tl = self.get_tl()
                br = self.get_br()

                bb = [min(tl[0], br[0]), min(tl[1], br[1]), abs(br[0] - tl[0]), abs(br[1] - tl[1])]
                return bb

        ui_control = UIControl()

        display_name = 'Display: ' + self.name
        cv.namedWindow(display_name, cv.WINDOW_AUTOSIZE)
        #cv.namedWindow(display_name, cv.WINDOW_NORMAL | cv.WINDOW_KEEPRATIO)
        #cv.resizeWindow(display_name, 960, 720)
        cv.setMouseCallback(display_name, ui_control.mouse_callback)

        frame_number = 0

        process_option = {
            'time_range': [0,0],
            'zoom_size': [0,0]
        }
        video_writer = None

        if videofilepath is not None and os.path.isfile(videofilepath):
            option_file = os.path.splitext(videofilepath)[0] + '.yaml'
            if os.path.isfile(option_file):
                data = open(option_file, 'r', encoding='utf-8').read()
                process_option.update(yaml.safe_load(data))
            else:
                with open(option_file, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(process_option, f)
        
        time_range = process_option['time_range']
        zoom_size = process_option['zoom_size']
        init_bbox = process_option.get('init_bbox', None)
        if init_bbox is not None:
            x, y, w, h = init_bbox
            if w*h == 0:
                init_bbox = None
        if init_bbox is not None:
            x, y, w, h = init_bbox
            if expand_roi:
                optional_box = [int(x-w/4), int(y-h/4), int(w*3/2), int(h*3/2)]
            else:
                optional_box = [x, y, w, h]

        if videofilepath is not None:
            assert os.path.isfile(videofilepath), "Invalid param {}".format(videofilepath)
            ", videofilepath must be a valid videofile"
            cap = cv.VideoCapture(videofilepath)
            video_source_type = 'file'
            print(f"[INFO] 使用视频文件: {videofilepath}")
            if isinstance(time_range, list) and  time_range[0] > 0:
                cap.set(cv2.CAP_PROP_POS_MSEC, int(time_range[0]*1000))
            ret, frame = cap.read()
            #frame = cv.resize(frame, None, fx=2, fy=2)
            frame_number += 1
            cv.imshow(display_name, frame)
        
            if save_result:
                bbox_name = 'bbox_e' if expand_roi else 'bbox_n'
                result_dir = os.path.join(os.path.dirname(videofilepath), 'outputs', bbox_name, tracker_type)
                result_file = os.path.join(result_dir, os.path.basename(videofilepath))
                os.makedirs(result_dir, exist_ok=True)
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                height, width = frame.shape[:2]
                video_writer = cv2.VideoWriter(result_file, fourcc, 25, (width,height), True)

        elif rtsp_url is not None:
            # RTSP 流源
            cap = cv.VideoCapture(rtsp_url)
            video_source_type = 'rtsp'
            print(f"[INFO] 连接到 RTSP 流: {rtsp_url}")
            
            # 设置 RTSP 连接参数
            cap.set(cv.CAP_PROP_BUFFERSIZE, 1)  # 最小缓冲区，降低延迟
            cap.set(cv.CAP_PROP_FPS, 30)  # 设置帧率
            
            # 尝试读取第一帧（可能需要等待连接建立）
            max_retries = 10
            for retry in range(max_retries):
                ret, frame = cap.read()
                if ret and frame is not None:
                    frame_number += 1
                    cv.imshow(display_name, frame)
                    print(f"[INFO] RTSP 连接成功，开始接收视频流")
                    break
                else:
                    print(f"[WARNING] RTSP 连接失败，重试 {retry + 1}/{max_retries}...")
                    time.sleep(0.5)
            
            if not ret or frame is None:
                print(f"[ERROR] 无法连接到 RTSP 流: {rtsp_url}")
                cap.release()
                cv.destroyAllWindows()
                return
            
            if save_result:
                bbox_name = 'bbox_e' if expand_roi else 'bbox_n'
                # 使用 RTSP URL 作为文件名的一部分
                stream_name = rtsp_url.split('/')[-1] or 'rtsp_stream'
                result_dir = os.path.join(self.results_dir, 'outputs', bbox_name, tracker_type)
                result_file = os.path.join(result_dir, f'{stream_name}.avi')
                os.makedirs(result_dir, exist_ok=True)
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                height, width = frame.shape[:2]
                video_writer = cv2.VideoWriter(result_file, fourcc, 25, (width, height), True)

        else:
            # 摄像头源
            cap = cv.VideoCapture(0)
            video_source_type = 'camera'
            print("[INFO] 使用网络摄像头")

        next_object_id = 0
        sequence_object_ids = []
        prev_output = OrderedDict()
        output_boxes = OrderedDict()

        if optional_box is not None:
            assert isinstance(optional_box, (list, tuple))
            assert len(optional_box) == 4, "valid box's format is [x,y,w,h]"

            out = tracker.initialize(frame, {'init_bbox': OrderedDict({next_object_id: optional_box}),
                                       'init_object_ids': [next_object_id, ],
                                       'object_ids': [next_object_id, ],
                                       'sequence_object_ids': [next_object_id, ]})

            prev_output = OrderedDict(out)

            output_boxes[next_object_id] = [optional_box, ]
            sequence_object_ids.append(next_object_id)
            next_object_id += 1

        # Wait for initial bounding box if video!
        paused = False if init_bbox is not None else videofilepath is not None

        while True:

            if not paused:
                # Capture frame-by-frame
                ret, frame = cap.read()
                frame_number += 1
                
                if frame is None:
                    if video_source_type == 'rtsp':
                        # RTSP 流可能断开，尝试重新连接
                        print("[WARNING] RTSP 流断开，尝试重新连接...")
                        cap.release()
                        time.sleep(1)
                        cap = cv.VideoCapture(rtsp_url)
                        cap.set(cv.CAP_PROP_BUFFERSIZE, 1)
                        ret, frame = cap.read()
                        if frame is None:
                            print("[ERROR] 无法重新连接到 RTSP 流")
                            break
                        else:
                            print("[INFO] RTSP 流已重新连接")
                    else:
                        break
                
                #frame = cv.resize(frame, None, fx=2, fy=2)
                if isinstance(time_range, list):
                    if video_source_type != 'rtsp':  # RTSP 流不支持 POS_MSEC
                        fts = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
                        if time_range[1] > 0 and fts > time_range[1]:
                            break

            frame_disp = frame.copy()

            info = OrderedDict()
            info['previous_output'] = prev_output

            if ui_control.new_init:
                ui_control.new_init = False
                init_state = ui_control.get_bb()
                print('### init bbox:', init_state)

                info['init_object_ids'] = [next_object_id, ]
                info['init_bbox'] = OrderedDict({next_object_id: init_state})
                sequence_object_ids.append(next_object_id)

                if self.ws_sender.is_connected():
                    self.ws_sender.send_start(frame_number, init_state, next_object_id)

                if save_results:
                    output_boxes[next_object_id] = [init_state, ]
                next_object_id += 1

            # Draw box
            if ui_control.mode == 'select':
                cv.rectangle(frame_disp, ui_control.get_tl(), ui_control.get_br(), (255, 0, 0), 2)

            if len(sequence_object_ids) > 0:
                info['sequence_object_ids'] = sequence_object_ids
                out = tracker.track(frame, info)
                prev_output = OrderedDict(out)

                if 'segmentation' in out:
                    frame_disp = overlay_mask(frame_disp, out['segmentation'])
                    mask_image = np.zeros(frame_disp.shape, dtype=frame_disp.dtype)

                    if save_results:
                        mask_image = overlay_mask(mask_image, out['segmentation'])
                        if not os.path.exists(self.results_dir):
                            os.makedirs(self.results_dir)
                        cv.imwrite(self.results_dir + f"seg_{frame_number}.jpg", mask_image)

                if 'target_bbox' in out:
                    obj_idx = 0
                    for obj_id, state in out['target_bbox'].items():
                        state = [int(s) for s in state]
                        cv.rectangle(frame_disp, (state[0], state[1]), (state[2] + state[0], state[3] + state[1]),
                                     _tracker_disp_colors[obj_id%6], 2)
                        if save_results:
                            output_boxes[obj_id].append(state)
                        
                        # 通过 WebSocket 发送脱靶量信息（在独立线程中）
                        if obj_idx == 0 and self.ws_sender.is_connected():
                            # 计算图像中心
                            image_h, image_w = frame.shape[:2]
                            image_center_x = image_w / 2.0
                            image_center_y = image_h / 2.0
                            
                            # 计算目标框的中心点
                            target_center_x = state[0] + state[2] / 2.0
                            target_center_y = state[1] + state[3] / 2.0
                            
                            # 计算脱靶量（相对于图像中心的偏移）
                            offset_x = target_center_x - image_center_x
                            offset_y = target_center_y - image_center_y
                            
                            self.ws_sender.send_offset(
                                frame_number=frame_number,
                                object_state=state,
                                object_id=obj_id,
                                offset_x=offset_x,
                                offset_y=offset_y,
                                center_x=target_center_x,
                                center_y=target_center_y,
                                image_width=image_w,
                                image_height=image_h
                            )
                        obj_idx += 1

            # Put text
            font_color = (0, 255, 0)
            msg = "Select target(s). Press 'r' to reset or 'q' to quit."
            #cv.rectangle(frame_disp, (5, 5), (630, 40), (50, 50, 50), -1)
            #cv.putText(frame_disp, msg, (10, 30), cv.FONT_HERSHEY_COMPLEX_SMALL, 1, font_color, 2)

            if videofilepath is not None:
                #msg = "Press SPACE to pause/resume the video."
                #cv.rectangle(frame_disp, (5, 50), (530, 90), (50, 50, 50), -1)
                #cv.putText(frame_disp, msg, (10, 75), cv.FONT_HERSHEY_COMPLEX_SMALL, 1, font_color, 2)
                progress = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
                duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
                time_progress = f'{progress:.3f}/{duration:.3f} target:{next_object_id-1}'
                cv.putText(frame_disp, time_progress, (10, 30), cv.FONT_HERSHEY_COMPLEX_SMALL, 1, font_color, 1)
            
            elif rtsp_url is not None:
                # RTSP 流显示帧数和目标数量
                time_progress = f'Frame: {frame_number} Target: {next_object_id - 1}'
                cv.putText(frame_disp, time_progress, (10, 30), cv.FONT_HERSHEY_COMPLEX_SMALL, 1, font_color, 1)
                # 显示 RTSP 源
                stream_name = rtsp_url.split('/')[-1] or 'RTSP Stream'
                cv.putText(frame_disp, f'Source: {stream_name}', (10, 60), cv.FONT_HERSHEY_COMPLEX_SMALL, 0.8, font_color, 1)

            # Display the resulting frame
            cv.imshow(display_name, frame_disp)
            if video_writer is not None and not paused:
                video_writer.write(frame_disp)

            key = cv.waitKey(1)
            if key == ord('q'):
                break

            elif key == ord('r'):
                #next_object_id = 1
                sequence_object_ids = []
                prev_output = OrderedDict()

                info = OrderedDict()

                info['object_ids'] = []
                info['init_object_ids'] = []
                info['init_bbox'] = OrderedDict()
                tracker.initialize(frame, info)
                ui_control.mode = 'init'
                
                if self.ws_sender.is_connected():
                    self.ws_sender.send_stop()

            # 'Space' to pause video
            elif key == 32 and videofilepath is not None:
                paused = not paused

        # When everything done, release the capture
        if video_writer is not None:
            video_writer.release()
        cap.release()
        cv.destroyAllWindows()
        
        # 停止 WebSocket 发送线程
        if self.ws_sender.is_connected():
            self.ws_sender.send_stop()
            self.ws_sender.stop()

        if save_results:
            if not os.path.exists(self.results_dir):
                os.makedirs(self.results_dir)
            video_name = "webcam" if videofilepath is None else Path(videofilepath).stem
            base_results_path = os.path.join(self.results_dir, 'video_{}'.format(video_name))
            print(f"Save results to: {base_results_path}")
            for obj_id, bbox in output_boxes.items():
                tracked_bb = np.array(bbox).astype(int)
                bbox_file = '{}_{}.txt'.format(base_results_path, obj_id)
                np.savetxt(bbox_file, tracked_bb, delimiter='\t', fmt='%d')


    def run_vot2020(self, debug=None, visdom_info=None):
        params = self.get_parameters()
        params.tracker_name = self.name
        params.param_name = self.parameter_name
        params.run_id = self.run_id

        debug_ = debug
        if debug is None:
            debug_ = getattr(params, 'debug', 0)

        if debug is None:
            visualization_ = getattr(params, 'visualization', False)
        else:
            visualization_ = True if debug else False

        params.visualization = visualization_
        params.debug = debug_

        self._init_visdom(visdom_info, debug_)

        tracker = self.create_tracker(params)
        tracker.initialize_features()

        output_segmentation = tracker.predicts_segmentation_mask()

        import pytracking.evaluation.vot2020 as vot

        def _convert_anno_to_list(vot_anno):
            vot_anno = [vot_anno[0], vot_anno[1], vot_anno[2], vot_anno[3]]
            return vot_anno

        def _convert_image_path(image_path):
            return image_path

        """Run tracker on VOT."""

        if output_segmentation:
            handle = vot.VOT("mask")
        else:
            handle = vot.VOT("rectangle")

        vot_anno = handle.region()

        image_path = handle.frame()
        if not image_path:
            return
        image_path = _convert_image_path(image_path)

        image = self._read_image(image_path)

        if output_segmentation:
            vot_anno_mask = vot.make_full_size(vot_anno, (image.shape[1], image.shape[0]))
            bbox = masks_to_bboxes(torch.from_numpy(vot_anno_mask), fmt='t').squeeze().tolist()
        else:
            bbox = _convert_anno_to_list(vot_anno)
            vot_anno_mask = None

        out = tracker.initialize(image, {'init_mask': vot_anno_mask, 'init_bbox': bbox})

        if out is None:
            out = {}
        prev_output = OrderedDict(out)

        # Track
        while True:
            image_path = handle.frame()
            if not image_path:
                break
            image_path = _convert_image_path(image_path)

            image = self._read_image(image_path)

            info = OrderedDict()
            info['previous_output'] = prev_output

            out = tracker.track(image, info)
            prev_output = OrderedDict(out)

            if output_segmentation:
                pred = out['segmentation'].astype(np.uint8)
            else:
                state = out['target_bbox']
                pred = vot.Rectangle(*state)
            handle.report(pred, 1.0)

            segmentation = out['segmentation'] if 'segmentation' in out else None
            if self.visdom is not None:
                tracker.visdom_draw_tracking(image, out['target_bbox'], segmentation)
            elif tracker.params.visualization:
                self.visualize(image, out['target_bbox'], segmentation)


    def run_vot(self, debug=None, visdom_info=None):
        params = self.get_parameters()
        params.tracker_name = self.name
        params.param_name = self.parameter_name
        params.run_id = self.run_id

        debug_ = debug
        if debug is None:
            debug_ = getattr(params, 'debug', 0)

        if debug is None:
            visualization_ = getattr(params, 'visualization', False)
        else:
            visualization_ = True if debug else False

        params.visualization = visualization_
        params.debug = debug_

        self._init_visdom(visdom_info, debug_)

        tracker = self.create_tracker(params)
        tracker.initialize_features()

        import pytracking.evaluation.vot as vot

        def _convert_anno_to_list(vot_anno):
            vot_anno = [vot_anno[0][0][0], vot_anno[0][0][1], vot_anno[0][1][0], vot_anno[0][1][1],
                        vot_anno[0][2][0], vot_anno[0][2][1], vot_anno[0][3][0], vot_anno[0][3][1]]
            return vot_anno

        def _convert_image_path(image_path):
            image_path_new = image_path[20:- 2]
            return "".join(image_path_new)

        """Run tracker on VOT."""

        handle = vot.VOT("polygon")

        vot_anno_polygon = handle.region()
        vot_anno_polygon = _convert_anno_to_list(vot_anno_polygon)

        init_state = convert_vot_anno_to_rect(vot_anno_polygon, tracker.params.vot_anno_conversion_type)

        image_path = handle.frame()
        if not image_path:
            return
        image_path = _convert_image_path(image_path)

        image = self._read_image(image_path)
        tracker.initialize(image, {'init_bbox': init_state})

        # Track
        while True:
            image_path = handle.frame()
            if not image_path:
                break
            image_path = _convert_image_path(image_path)

            image = self._read_image(image_path)
            out = tracker.track(image)
            state = out['target_bbox']

            handle.report(vot.Rectangle(state[0], state[1], state[2], state[3]))

            segmentation = out['segmentation'] if 'segmentation' in out else None
            if self.visdom is not None:
                tracker.visdom_draw_tracking(image, out['target_bbox'], segmentation)
            elif tracker.params.visualization:
                self.visualize(image, out['target_bbox'], segmentation)

    def get_parameters(self):
        """Get parameters."""
        param_module = importlib.import_module('pytracking.parameter.{}.{}'.format(self.name, self.parameter_name))
        params = param_module.parameters()
        return params


    def init_visualization(self):
        self.pause_mode = False
        self.fig, self.ax = plt.subplots(1)
        self.fig.canvas.mpl_connect('key_press_event', self.press)
        plt.tight_layout()


    def visualize(self, image, state, segmentation=None):
        self.ax.cla()
        self.ax.imshow(image)
        if segmentation is not None:
            self.ax.imshow(segmentation, alpha=0.5)

        if isinstance(state, (OrderedDict, dict)):
            boxes = [v for k, v in state.items()]
        elif isinstance(state, list):
            boxes = state
        else:
            boxes = (state,)

        for i, box in enumerate(boxes, start=1):
            col = _tracker_disp_colors[i%6]
            col = [float(c) / 255.0 for c in col]
            rect = patches.Rectangle((box[0], box[1]), box[2], box[3], linewidth=1, edgecolor=col, facecolor='none')
            self.ax.add_patch(rect)

        if getattr(self, 'gt_state', None) is not None:
            gt_state = self.gt_state
            rect = patches.Rectangle((gt_state[0], gt_state[1]), gt_state[2], gt_state[3], linewidth=1, edgecolor='g', facecolor='none')
            self.ax.add_patch(rect)
        self.ax.set_axis_off()
        self.ax.axis('equal')
        draw_figure(self.fig)

        if self.pause_mode:
            keypress = False
            while not keypress:
                keypress = plt.waitforbuttonpress()

    def reset_tracker(self):
        pass

    def press(self, event):
        if event.key == 'p':
            self.pause_mode = not self.pause_mode
            print("Switching pause mode!")
        elif event.key == 'r':
            self.reset_tracker()
            print("Resetting target pos to gt!")

    def _read_image(self, image_file: str):
        im = cv.imread(image_file)
        return cv.cvtColor(im, cv.COLOR_BGR2RGB)



