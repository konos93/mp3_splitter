#!/usr/bin/env python3

import subprocess
import json
import os

# Input MP3 file
input_file = 'file.mp3'  # Replace with your input MP3 file

# Define the target segment duration (29 minutes) and max duration (30 minutes) in seconds
target_segment_duration = 14 * 60  # 14 min
max_segment_duration = 15* 60    # 15 min

# Define the output pattern for segment files
output_pattern = 'segment_%03d.mp3'

# Step 1: Detect silence in the audio file
silence_log = 'silence_times.txt'
command_silence = [
    'ffmpeg',
    '-i', input_file,
    '-af', 'silencedetect=noise=-20dB:d=2',  # Detect silence (noise threshold -30dB, min duration 0.5s)
    '-f', 'null',
    '-'
]

# Run silence detection and capture stderr
with open(silence_log, 'w') as log_file:
    result = subprocess.run(command_silence, stderr=subprocess.PIPE, text=True)
    log_file.write(result.stderr)

# Step 2: Parse silence timestamps from the log
silence_timestamps = []
with open(silence_log, 'r') as log_file:
    for line in log_file:
        if 'silence_end' in line:
            parts = line.split()
            for i, part in enumerate(parts):
                if part == 'silence_end:':
                    timestamp = float(parts[i + 1])
                    silence_timestamps.append(timestamp)

# Step 3: Find split points near 29-minute intervals, ensuring no segment exceeds 30 minutes
split_points = []
current_time = 0
tolerance = 60  # Allow splits within ±1 minute of the target

while current_time < max(silence_timestamps, default=0):
    target = current_time + target_segment_duration
    max_time = current_time + max_segment_duration
    # Find silences within the window [target - tolerance, max_time]
    candidate_silences = [t for t in silence_timestamps if target - tolerance <= t <= max_time]
    if candidate_silences:
        # Choose the silence closest to the target
        closest_silence = min(candidate_silences, key=lambda x: abs(x - target))
        split_points.append(closest_silence)
        current_time = closest_silence
    else:
        # If no silence found, split at max_segment_duration
        split_points.append(max_time)
        current_time = max_time

# Step 4: Use FFmpeg to split the audio at the selected points
if split_points:
    split_points_str = ','.join(map(str, split_points))
    command_split = [
        'ffmpeg',
        '-i', input_file,
        '-c', 'copy',
        '-f', 'segment',
        '-segment_times', split_points_str,
        '-reset_timestamps', '1',
        '-map', '0',
        output_pattern
    ]
    subprocess.run(command_split, check=True)
    print("Segments created successfully.")
else:
    print("No suitable split points found.")

# Clean up
if os.path.exists(silence_log):
    os.remove(silence_log)
