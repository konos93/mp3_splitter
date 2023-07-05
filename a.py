import os
import subprocess

def split_file(input_file, output_pattern):
    # Create the output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_pattern), exist_ok=True)

    # Command to split the file using FFmpeg
    command = [
        'ffmpeg',
        '-i', input_file,
        '-c', 'copy',
        '-f', 'segment',
        '-segment_time', '3540',  # 59 minutes = 3540 seconds
        '-reset_timestamps', '1',
        '-map', '0',
        output_pattern
    ]

    # Execute the FFmpeg command
    subprocess.run(command)

# Get the path of the Python script
script_path = os.path.dirname(os.path.abspath(__file__))

# Input file path (assuming it's in the same folder as the script)
input_file = os.path.join(script_path, 'file.mp3')

# Output file pattern (e.g., output/output_001.mp3, output/output_002.mp3, ...)
output_pattern = os.path.join(script_path, 'output', 'output_%03d.mp3')

split_file(input_file, output_pattern)
