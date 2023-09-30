import subprocess

# Input MP3 file
input_file = 'file.mp3'  # Replace with your input MP3 file

# Define the desired segment duration (59 minutes) in seconds
segment_duration = 59 * 60

# Define the output pattern for segment files
output_pattern = 'segment_%03d.mp3'

# Use FFmpeg to create the segments
command = [
    'ffmpeg',
    '-i', input_file,
    '-c', 'copy',
    '-f', 'segment',
    '-segment_time', str(segment_duration),  # 59 minutes = 3540 seconds
    '-reset_timestamps', '1',
    '-map', '0',
    output_pattern
]

subprocess.run(command, check=True)

print("Segments created successfully.")
