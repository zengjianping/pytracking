import os
import sys
import argparse

env_path = os.path.join(os.path.dirname(__file__), '..')
if env_path not in sys.path:
    sys.path.append(env_path)

from pytracking.evaluation import Tracker


def run_video(tracker_name, tracker_param, videofile, optional_box=None, debug=None, save_results=False,
              save_result=False, expand_roi=False):
    """Run the tracker on your webcam.
    args:
        tracker_name: Name of tracking method.
        tracker_param: Name of parameter file.
        debug: Debug level.
    """
    tracker = Tracker(tracker_name, tracker_param)
    tracker_type = f'{tracker_name}-{tracker_param}'
    tracker.run_video_generic(videofilepath=videofile, optional_box=optional_box, debug=debug, save_results=save_results,
                              save_result=save_result, expand_roi=expand_roi, tracker_type=tracker_type)

def main():
    parser = argparse.ArgumentParser(description='Run the tracker on your webcam.')
    parser.add_argument('tracker_name', type=str, help='Name of tracking method.')
    parser.add_argument('tracker_param', type=str, help='Name of parameter file.')
    parser.add_argument('videofile', type=str, help='path to a video file.')
    parser.add_argument('--optional_box', type=float, default=None, nargs="+", help='optional_box with format x y w h.')
    parser.add_argument('--debug', type=int, default=0, help='Debug level.')
    parser.add_argument('--save_results', dest='save_results', action='store_true', help='Save bounding boxes')
    parser.add_argument('--save_result', dest='save_result', action='store_true', help='Save result video')
    parser.add_argument('--expand_roi', dest='expand_roi', action='store_true', help='expand bbox')
    parser.set_defaults(save_results=False)

    args = parser.parse_args()

    run_video(args.tracker_name, args.tracker_param,args.videofile, args.optional_box, args.debug, args.save_results,
              args.save_result, args.expand_roi)


if __name__ == '__main__':
    main()
