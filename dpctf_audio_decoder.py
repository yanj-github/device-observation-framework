# -*- coding: utf-8 -*-
"""WAVE DPCTF Audio decoder

Translates the detected Audio Segments into AudioSegment object

The Software is provided to you by the Licensor under the License, as
defined below, subject to the following condition.

Without limiting other conditions in the License, the grant of rights under
the License will not include, and the License does not grant to you, the
right to Sell the Software.

For purposes of the foregoing, “Sell” means practicing any or all of the
rights granted to you under the License to provide to third parties, for a
fee or other consideration (including without limitation fees for hosting
or consulting/ support services related to the Software), a product or
service whose value derives, entirely or substantially, from the
functionality of the Software. Any license notice or attribution required
by the License must also include this Commons Clause License Condition
notice.

Software: WAVE Observation Framework
License: Apache 2.0 https://www.apache.org/licenses/LICENSE-2.0.txt
Licensor: Consumer Technology Association
Contributor: Resillion UK Limited
"""
import logging
import math
from typing import Tuple

import matplotlib.pyplot as plt

from audio_file_reader import get_time_from_segment
from exceptions import AudioAlignError
from global_configurations import GlobalConfigurations

logging.getLogger("matplotlib.font_manager").disabled = True


class AudioSegment:
    """audio segment class"""

    audio_content_id: str
    """The content id from audio mezzanine"""
    duration: float
    """The duration of audio segment"""
    media_time: float
    """The media time of audio segment"""
    audio_segment_timing: float
    """timings in where audio segment found"""

    def __init__(
        self,
        audio_content_id: str,
        duration: float,
        media_time: float,
        audio_segment_timing: float,
    ):
        self.audio_content_id = audio_content_id
        self.duration = duration
        self.media_time = media_time
        self.audio_segment_timing = audio_segment_timing


def get_trim_from(
    subject_data: list,
    segment_data: list,
    sample_rate: int,
    audio_sample_length: int,
    global_configurations: GlobalConfigurations,
    exact: bool = False,
) -> int:
    """
    Accepts
    1) subject_data:
      a first audio file that was presumably recorded with some dead time
      before the audio of interest,
    2) segment_data:
      a segment of PN audio that should mark the end of the audio of interest,
    Returns: trim audio from position
    To trim off the leading audio based on first occurrence of matching segment_data.
    Align the archived copy of PN data (segment_data) with the PN data
    in the recorded audio (subject_data)
    """
    offset = 0
    observation_period = sample_rate * audio_sample_length
    tolerance = sample_rate * global_configurations.get_audio_alignment_tolerance()

    alignment_count = 0
    check_count = global_configurations.get_audio_alignment_check_count()

    for count in range(0, check_count):
        alignment_count = 0
        # Checking if last 3 segments are aligned within the tolerance of segment duration.
        segments_to_check = count + 2
        for i in range(count, segments_to_check):
            segment_data_1_start = observation_period * (i)
            segment_data_1_end = observation_period * (i + 1)
            segment_data_1 = segment_data[segment_data_1_start:segment_data_1_end]

            segment_data_2_start = observation_period * (i + 1)
            segment_data_2_end = observation_period * (i + 2)
            segment_data_2 = segment_data[segment_data_2_start:segment_data_2_end]

            offset1 = get_time_from_segment(subject_data, segment_data_1)
            offset2 = get_time_from_segment(subject_data, segment_data_2)

            if i == count:
                if exact:
                    offset = offset1
                else:
                    offset = offset1 - observation_period * count
            diff = offset2 - offset1
            if diff < 0 or abs(diff - observation_period) > tolerance:
                break
            alignment_count += 1

        # break when alignment found where 3 adjacent segments are aligned
        if alignment_count > 1:
            break

    # raise exception unable to align recording with PN file
    if alignment_count < 2:
        raise AudioAlignError(
            "Unable to align the archived copy of PN data (segment_data) "
            "with the PN data in the recorded audio (subject_data)"
        )

    trim_from = offset
    if trim_from < 0:
        trim_from = 0

    return trim_from


def get_trim_to(
    subject_data: list,
    segment_data: list,
    sample_rate: int,
    audio_sample_length: int,
    global_configurations: GlobalConfigurations,
) -> int:
    """
    Accepts
    1) subject_data:
      a first audio file that was presumably recorded with some dead time
      before the audio of interest,
    2) segment_data:
      a segment of PN audio that should mark the end of the audio of interest,
    Returns: trim audio to position
    To trim off the trailing audio based on last occurrence of matching segment_data.
    Align the archived copy of PN data (segment_data) with the PN data
    in the recorded audio (subject_data)
    """
    offset = len(subject_data)
    observation_period = sample_rate * audio_sample_length
    tolerance = sample_rate * global_configurations.get_audio_alignment_tolerance()
    segment_len = len(segment_data)

    alignment_count = 0
    check_count = global_configurations.get_audio_alignment_check_count() + 1

    for count in range(1, check_count):
        alignment_count = 0
        # Checking if last 3 segments are aligned within the tolerance of segment duration.
        segments_to_check = count + 2
        for i in range(count, segments_to_check):
            segment_data_1_start = segment_len - (observation_period * i)
            segment_data_1_end = segment_len - (observation_period * (i - 1))
            segment_data_1 = segment_data[segment_data_1_start:segment_data_1_end]

            segment_data_2_start = segment_len - (observation_period * (i + 1))
            segment_data_2_end = segment_len - (observation_period * i)
            segment_data_2 = segment_data[segment_data_2_start:segment_data_2_end]

            offset1 = get_time_from_segment(subject_data, segment_data_1)
            offset2 = get_time_from_segment(subject_data, segment_data_2)

            if i == count:
                offset = offset1 + observation_period * count
            diff = offset1 - offset2
            if diff < 0 or abs(diff - observation_period) > tolerance:
                break
            alignment_count += 1

        # break when alignment found where 3 adjacent segments are aligned
        if alignment_count > 1:
            break

    # raise exception unable to align recording with PN file
    if alignment_count < 2:
        raise AudioAlignError(
            "Unable to align the archived copy of PN data (segment_data) "
            "with the PN data in the recorded audio (subject_data)"
        )

    # no margin added to trim_to as last segment is correctly detected
    trim_to = offset
    if trim_to > len(subject_data):
        trim_to = len(subject_data)

    return trim_to


def trim_audio(
    index: int,
    subject_data: list,
    segment_data: list,
    sample_rate: int,
    audio_sample_length: int,
    global_configurations: GlobalConfigurations,
    observation_data_export_file: str,
) -> Tuple[list, int]:
    """
    Accepts
    1) subject_data:
      a first audio file that was presumably recorded with some dead time before
      the audio of interest,
    2) segment_data:
      a segment of PN audio that should mark the end of the audio of interest,
    Returns: a shorter copy of subject_data with leading and trailing audio trimmed and
    offset of mezzanine from recording
    prior to first occurrence of segment_data.
    """
    trim_from = get_trim_from(
        subject_data,
        segment_data,
        sample_rate,
        audio_sample_length,
        global_configurations,
    )
    trim_to = get_trim_to(
        subject_data,
        segment_data,
        sample_rate,
        audio_sample_length,
        global_configurations,
    )
    trimmed_data = subject_data[trim_from:trim_to].copy()

    logger = global_configurations.get_logger()
    if logger.getEffectiveLevel() == logging.DEBUG and observation_data_export_file:
        plt.figure(index)
        plt.figure(figsize=(30, 6))
        plt.xlabel("Time")
        plt.ylabel("Audio Wave")
        subject_data_file = (
            observation_data_export_file + "subject_data_" + str(index) + ".png"
        )
        plt.title("subject_data")
        plt.plot(subject_data)
        plt.axvline(x=trim_from, color="b")
        plt.axvline(x=trim_to, color="g")
        plt.savefig(subject_data_file)
        plt.close()

    return trimmed_data, trim_from


def decode_audio_segments(
    start_media_time: float,
    audio_segment_data_list: list,
    audio_subject_data: list,
    sample_rate: int,
    audio_sample_length: int,
    global_configurations: GlobalConfigurations,
    observation_data_export_file: str,
) -> list:
    """Decode audio segment and return starting offset and audio segment data"""
    audio_segments = []
    observation_period = sample_rate * audio_sample_length
    neighborhood = (
        sample_rate * global_configurations.get_audio_observation_neighborhood()
    )

    first_offset = None
    index = 0
    for audio_segment_data in audio_segment_data_list:
        # Trim off any leading (useless) audio prior to the watermarked portion
        trimmed_data, offset = trim_audio(
            index,
            audio_subject_data,
            audio_segment_data,
            sample_rate,
            audio_sample_length,
            global_configurations,
            observation_data_export_file,
        )
        if not first_offset:
            first_offset = offset

        trimmed_data_len = len(trimmed_data)
        duration = math.floor((len(audio_segment_data)) / sample_rate)
        max_segments = math.floor(duration * sample_rate / observation_period)
        # To speed things up, only check in the expected neighborhood of the segment
        # (e.g., +/- 500mS).
        for i in range(0, max_segments):
            if trimmed_data_len < neighborhood:
                # when too little data in recording raise exception
                raise AudioAlignError(
                    "Too little valid data in recording the recorded audio (subject_data)"
                )
            else:
                neighbor_start = (i * observation_period) - (neighborhood // 2)
                neighbor_end = (i * observation_period) + (neighborhood // 2)
                if neighbor_start < 0:
                    neighbor_start = 0
                    neighbor_end = neighborhood
                if neighbor_end > trimmed_data_len:
                    neighbor_start = trimmed_data_len - neighborhood
                    neighbor_end = trimmed_data_len

                subject_data = trimmed_data[neighbor_start:neighbor_end]
                if i == max_segments - 1:
                    # if the last segment
                    this_segment = audio_segment_data[(i * observation_period) :]
                    segment_duration = len(this_segment) / sample_rate
                    media_time = start_media_time + i * audio_sample_length
                    start_media_time += segment_duration - audio_sample_length
                else:
                    this_segment = audio_segment_data[
                        (i * observation_period) : ((i + 1) * observation_period)
                    ]
                    segment_duration = len(this_segment) / sample_rate
                    media_time = start_media_time + i * audio_sample_length
                segment_time = (
                    get_time_from_segment(subject_data, this_segment) + neighbor_start
                )
                segment_time_in_ms = (segment_time + offset) / sample_rate

            # content ID is index of splicing points starts from 0
            audio_content_id = str(index)
            audio_segment = AudioSegment(
                audio_content_id,
                segment_duration,
                media_time,
                segment_time_in_ms,
            )
            audio_segments.append(audio_segment)
        index += 1
        start_media_time = start_media_time + max_segments * audio_sample_length

    return first_offset, audio_segments
