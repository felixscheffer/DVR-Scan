# -*- coding: utf-8 -*-
#
#      DVR-Scan: Video Motion Event Detection & Extraction Tool
#   --------------------------------------------------------------
#       [  Site: https://www.dvr-scan.com/                 ]
#       [  Repo: https://github.com/Breakthrough/DVR-Scan  ]
#
# Copyright (C) 2014-2023 Brandon Castellano <http://www.bcastell.com>.
# DVR-Scan is licensed under the BSD 2-Clause License; see the included
# LICENSE file, or visit one of the above pages for details.
#
"""DVR-Scan MotionScanner Tests

Validates functionality of the motion scanning context using various parameters.
"""

import pytest

from dvr_scan.detector import Rectangle
from dvr_scan.scanner import DetectorType, MotionScanner
from dvr_scan.subtractor import SubtractorCNT, SubtractorCudaMOG2
from dvr_scan.region import Point

# ROI within the frame used for the test case (see traffic_camera.txt for details).
TRAFFIC_CAMERA_ROI = [
    Point(631, 532),
    Point(841, 532),
    Point(841, 659),
    Point(631, 659),
]

TRAFFIC_CAMERA_EVENTS = [
    (9, 149),
    (358, 491),
    (542, 576),
]

# Allow up to 1 frame difference in ground truth due to different floating point handling.
CUDA_EVENT_TOLERANCE = 1

TRAFFIC_CAMERA_EVENTS_TIME_PRE_5 = [
    (3, 149),
    (352, 491),
    (536, 576),
]

# Last event still ends on end of video even though we specified to include 40 frames extra.
TRAFFIC_CAMERA_EVENTS_TIME_POST_40 = [
    (9, 139),
    (358, 481),
    (542, 576),
]

TRAFFIC_CAMERA_EVENTS_CNT = [
    (15, 149),
    (364, 491),
    (543, 576),
]

# Small ROI for faster test execution.
CORRUPT_VIDEO_ROI = [
    Point(0, 0),
    Point(32, 0),
    Point(32, 32),
    Point(0, 32),
]
CORRUPT_VIDEO_EVENTS = [
    (152, 366),
]


def test_scan_context(traffic_camera_video):
    """Test functionality of MotionScanner with default parameters (DetectorType.MOG2)."""
    scanner = MotionScanner([traffic_camera_video])
    scanner.set_detection_params()
    scanner.set_regions(regions=[TRAFFIC_CAMERA_ROI])
    scanner.set_event_params(min_event_len=4, time_pre_event=0)
    event_list = scanner.scan().event_list
    event_list = [(event.start.frame_num, event.end.frame_num) for event in event_list]
    assert event_list == TRAFFIC_CAMERA_EVENTS


@pytest.mark.skipif(not SubtractorCudaMOG2.is_available(), reason="CUDA module not available.")
def test_scan_context_cuda(traffic_camera_video):
    """ Test functionality of MotionScanner with the DetectorType.MOG2_CUDA. """
    scanner = MotionScanner([traffic_camera_video])
    scanner.set_detection_params(detector_type=DetectorType.MOG2_CUDA)
    scanner.set_regions(regions=[TRAFFIC_CAMERA_ROI])
    scanner.set_event_params(min_event_len=4, time_pre_event=0)
    event_list = scanner.scan().event_list
    assert len(event_list) == len(TRAFFIC_CAMERA_EVENTS)
    event_list = [(event.start.frame_num, event.end.frame_num) for event in event_list]
    for i, event in enumerate(event_list):
        start_matches = abs(event.start - TRAFFIC_CAMERA_EVENTS[i][0]) <= CUDA_EVENT_TOLERANCE
        end_matches = abs(event.start - TRAFFIC_CAMERA_EVENTS[i][0]) <= CUDA_EVENT_TOLERANCE
        assert start_matches and end_matches, (
            "Event mismatch at index %d with tolerance %d:\n Actual:   %s\n Expected: %s" %
            (i, CUDA_EVENT_TOLERANCE, str(event), str(TRAFFIC_CAMERA_EVENTS[i])))


@pytest.mark.skipif(not SubtractorCNT.is_available(), reason="CNT algorithm not available.")
def test_scan_context_cnt(traffic_camera_video):
    """ Test basic functionality of MotionScanner using the CNT algorithm. """
    scanner = MotionScanner([traffic_camera_video])
    scanner.set_detection_params(detector_type=DetectorType.CNT)
    scanner.set_regions(regions=[TRAFFIC_CAMERA_ROI])
    scanner.set_event_params(min_event_len=3, time_pre_event=0)
    event_list = scanner.scan().event_list
    event_list = [(event.start.frame_num, event.end.frame_num) for event in event_list]
    assert event_list == TRAFFIC_CAMERA_EVENTS_CNT


def test_pre_event_shift(traffic_camera_video):
    """ Test setting time_pre_event. """
    scanner = MotionScanner([traffic_camera_video])
    scanner.set_regions(regions=[TRAFFIC_CAMERA_ROI])
    scanner.set_event_params(min_event_len=4, time_pre_event=6)
    event_list = scanner.scan().event_list
    event_list = [(event.start.frame_num, event.end.frame_num) for event in event_list]
    assert event_list == TRAFFIC_CAMERA_EVENTS_TIME_PRE_5


def test_pre_event_shift_with_frame_skip(traffic_camera_video):
    """ Test setting time_pre_event when using frame_skip. """
    for frame_skip in range(1, 6):
        scanner = MotionScanner([traffic_camera_video], frame_skip=frame_skip)
        scanner.set_regions(regions=[TRAFFIC_CAMERA_ROI])
        scanner.set_event_params(min_event_len=4, time_pre_event=6)
        event_list = scanner.scan().event_list
        event_list = [(event.start.frame_num, event.end.frame_num) for event in event_list]
        # The start times should not differ from the ground truth (non-frame-skipped) by the amount
        # of frames that we are skipping. End times can vary more since the default value of
        # time_post_event is relatively large.
        assert all([
            abs(x[0] - y[0]) <= frame_skip
            for x, y in zip(event_list, TRAFFIC_CAMERA_EVENTS_TIME_PRE_5)
        ]), "Comparison failure when frame_skip = %d" % (
            frame_skip)


def test_post_event_shift(traffic_camera_video):
    """ Test setting time_post_event. """

    scanner = MotionScanner([traffic_camera_video])
    scanner.set_regions(regions=[TRAFFIC_CAMERA_ROI])
    scanner.set_event_params(min_event_len=4, time_pre_event=0, time_post_event=40)

    event_list = scanner.scan().event_list
    assert len(event_list) == len(TRAFFIC_CAMERA_EVENTS_TIME_POST_40)
    event_list = [(event.start.frame_num, event.end.frame_num) for event in event_list]
    assert all([x == y for x, y in zip(event_list, TRAFFIC_CAMERA_EVENTS_TIME_POST_40)])


def test_post_event_shift_with_frame_skip(traffic_camera_video):
    """ Test setting time_post_event. """
    for frame_skip in range(1, 6):
        scanner = MotionScanner([traffic_camera_video], frame_skip=frame_skip)
        scanner.set_regions(regions=[TRAFFIC_CAMERA_ROI])
        scanner.set_event_params(min_event_len=4, time_post_event=40)
        event_list = scanner.scan().event_list
        assert len(event_list) == len(TRAFFIC_CAMERA_EVENTS_TIME_POST_40)
        event_list = [(event.start.frame_num, event.end.frame_num) for event in event_list]
        # The calculated end times should not differ by more than frame_skip from the ground truth.
        assert all([
            abs(x[1] - y[1]) <= frame_skip
            for x, y in zip(event_list, TRAFFIC_CAMERA_EVENTS_TIME_POST_40)
        ]), "Comparison failure when frame_skip = %d" % (
            frame_skip)
        # The calculated end times must always be >= the ground truth's frame number, otherwise
        # we may be discarding frames containing motion due to skipping them.
        assert all([x[1] >= y[1] for x, y in zip(event_list, TRAFFIC_CAMERA_EVENTS_TIME_POST_40)
                   ]), "Comparison failure when frame_skip = %d" % (
                       frame_skip)


def test_decode_corrupt_video(corrupt_video):
    """Ensure we can process a video with a single bad frame."""
    scanner = MotionScanner([corrupt_video])
    scanner.set_event_params(min_event_len=2)
    scanner.set_regions(regions=[CORRUPT_VIDEO_ROI])
    event_list = scanner.scan().event_list
    event_list = [(event.start.frame_num, event.end.frame_num) for event in event_list]
    assert event_list == CORRUPT_VIDEO_EVENTS


def test_start_end_time(traffic_camera_video):
    """ Test basic functionality of MotionScanner with start and stop times defined. """
    scanner = MotionScanner([traffic_camera_video])
    scanner.set_regions(regions=[TRAFFIC_CAMERA_ROI])
    scanner.set_event_params(min_event_len=4, time_pre_event=0)
    scanner.set_video_time(start_time=200, end_time=500)
    event_list = scanner.scan().event_list
    event_list = [(event.start.frame_num, event.end.frame_num) for event in event_list]
    # The set duration should only cover the middle event.
    assert event_list == TRAFFIC_CAMERA_EVENTS[1:2]


def test_start_duration(traffic_camera_video):
    """ Test basic functionality of MotionScanner with start and duration defined. """
    scanner = MotionScanner([traffic_camera_video])
    scanner.set_regions(regions=[TRAFFIC_CAMERA_ROI])
    scanner.set_event_params(min_event_len=4, time_pre_event=0)
    scanner.set_video_time(start_time=200, duration=300)
    event_list = scanner.scan().event_list
    event_list = [(event.start.frame_num, event.end.frame_num) for event in event_list]
    # The set duration should only cover the middle event.
    assert event_list == TRAFFIC_CAMERA_EVENTS[1:2]
