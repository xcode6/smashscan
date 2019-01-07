import time
import argparse
import cv2
from darkflow.net.build import TFNet

# SmashScan libraries
import preprocess

TFNET_OPTIONS = {
    'config': 'cfg',
    'model': 'cfg/tiny-yolo-voc-6c.cfg',
    'metaLoad': 'cfg/tiny-yolo-voc-6c.meta',
    'pbLoad': 'cfg/tiny-yolo-voc-6c.pb',
    'threshold': 0.25,
    'gpu': 1.0
}

LABELS_LIST = ["battlefield", "dreamland", "finaldest",
               "fountain", "pokemon", "yoshis"]

# Display the main test plot.
def show_tfnet_results(video_name, step_size,
    videos_dir, save_flag, show_flag):

    # Create an OpenCV capture object. https://docs.opencv.org/3.4.2/
    capture = cv2.VideoCapture('%s/%s' % (videos_dir, video_name))
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))

    # A list of the label history to be used in the cleaning algorithm. It 
    # stores the labels as integers, while no result found is (-1).
    dirty_hist = list()

    # A list that stores the corresponding bounding boxes of the timeline.
    bbox_hist = list()

    # Display a cv2 window if the hide flag is disabled.
    if show_flag:
        cv2.namedWindow('frame', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('frame', 1280, 720)

    # Initialize DarkFlow TFNet object with weights from cfg folder.
    start_time = time.time()
    tfnet = TFNet(TFNET_OPTIONS)

    # Iterate through video and use tfnet to perform object detection.
    # while (current_frame < total_frames):
    for current_frame in range(0, total_frames, step_size):
        capture.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        _, frame = capture.read()

        # Get the tfnet result with the largest confidence and extract info.
        result = preprocess.get_tfnet_result(tfnet, frame)
        if result:
            tl = (result['topleft']['x'], result['topleft']['y'])
            br = (result['bottomright']['x'], result['bottomright']['y'])
            label = result['label']
            confidence = result['confidence']

        # Display bounding box, label, and confidence.
        if result and show_flag:
            # Draw bounding box around frame's result.
            frame = cv2.rectangle(frame, tl, br, [0, 0, 255], 6)

            # Add a white rectangle to the frame to emphasize text.
            text_tl = (tl[0] + 10, tl [1] + 30)
            text_br = (text_tl[0] + 240, text_tl[1] + 20)
            frame = cv2.rectangle(frame, tl, text_br, (255, 255, 255), -1)

            # Add text with label and confidence to the displayed frame.
            text = '{}: {:.0f}%'.format(label, confidence * 100)
            frame = cv2.putText(frame, text, text_tl,
                cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 0, 0), 2)

        # Store label if result found, or (-1) if no result was found.
        if result:
            dirty_hist.append(LABELS_LIST.index(result['label']))
            bbox_hist.append((tl, br))
        else:
            dirty_hist.append(-1)
            bbox_hist.append(-1)

        # Display the frame if show_flag is enabled. Close if 'q' pressed.
        if show_flag:
            cv2.imshow('frame', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # Save the frame if the save_flag is enabled.
        if save_flag:
            cv2.imwrite('output/frame%07d.png' % current_frame, frame)

    # End the TfNet session and display time taken to complete.
    finish_time = time.time() - start_time
    print("Initial video sweep tfnet results in %.2fs" % finish_time)
    print("\tAverage FPS: %.2f" % (len(dirty_hist) / finish_time))

    # Fill holes in the history timeline list, and filter out timeline
    # sections that are smaller than a particular size.
    clean_hist = preprocess.hist_fill_filter(dirty_hist)
    clean_hist = preprocess.hist_size_filter(clean_hist, step_size)
    preprocess.show_hist_plots(dirty_hist, clean_hist, LABELS_LIST)

    # Get a list of the matches and avg bboxes according to clean_hist.
    match_ranges = preprocess.get_match_ranges(clean_hist)
    match_bboxes = preprocess.get_match_bboxes(match_ranges, bbox_hist)

    # Show the beginning and end of each match according to the filters.
    for i, match_range in enumerate(match_ranges):
        capture.set(cv2.CAP_PROP_POS_FRAMES, match_range[0]*step_size)
        _, frame = capture.read()
        frame = cv2.rectangle(frame, match_bboxes[i][0], 
            match_bboxes[i][1], [0, 0, 255], 6)
        cv2.imshow('frame', frame)
        cv2.waitKey(0)

        capture.set(cv2.CAP_PROP_POS_FRAMES, match_range[1]*step_size)
        _, frame = capture.read()
        frame = cv2.rectangle(frame, match_bboxes[i][0],
            match_bboxes[i][1], [0, 0, 255], 6)
        cv2.imshow('frame', frame)
        cv2.waitKey(0)

    # Improving match range accuracy.
    accurate_match_ranges = preprocess.get_accurate_match_ranges(
        match_ranges, step_size, capture, tfnet)
    for i, match_range in enumerate(accurate_match_ranges):
        capture.set(cv2.CAP_PROP_POS_FRAMES, match_range[0])
        _, frame = capture.read()
        frame = cv2.rectangle(frame, match_bboxes[i][0], 
            match_bboxes[i][1], [0, 0, 255], 6)
        cv2.imshow('frame', frame)
        cv2.waitKey(0)

        capture.set(cv2.CAP_PROP_POS_FRAMES, match_range[1])
        _, frame = capture.read()
        frame = cv2.rectangle(frame, match_bboxes[i][0],
            match_bboxes[i][1], [0, 0, 255], 6)
        cv2.imshow('frame', frame)
        cv2.waitKey(0)

    tfnet.sess.close()
    capture.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='A testing tool used to \
        analyze the performance of trained DarkNet weights.')
    parser.add_argument('video_name', type=str, 
        help='The name of the video file to be tested on.')
    parser.add_argument('-save', '--save_flag', action='store_true',
        help='A flag used to determine if frames are saved.')
    parser.add_argument('-hide', '--hide_flag', action='store_true',
        help='A flag used to hide the plot, so testing runs faster.')
    parser.add_argument('-step', '--step_size', type=int, default=60,
        nargs='?', help='The step size used when testing.')
    parser.add_argument('-dir', '--video_dir', type=str, default='videos',
        nargs='?', help='The video file directory to be used.')

    args = parser.parse_args()

    show_tfnet_results(args.video_name, args.step_size,
        args.video_dir, args.save_flag, not args.hide_flag)
