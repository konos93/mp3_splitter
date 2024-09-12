import subprocess

# Input MP3 file
input_file = 'file.mkv'  # Replace with your input MP3 file

# Define the start time (in seconds) or in the format "hh:mm:ss"
start_time = '00:10:00'  # Start at 10 minutes (can also use seconds like 600)

# Define the end time (in seconds) or in the format "hh:mm:ss"
end_time = '01:00:00'  # End at 1 hour (can also use seconds like 3600)

# Define the output pattern for segment files
output_pattern = 'output.mkv'

# Use FFmpeg to extract the specified segment
command = [
    'ffmpeg',
    '-ss', start_time,  # Start time
    '-to', end_time,    # End time
    '-i', input_file,
    '-c', 'copy',
    output_pattern
]

subprocess.run(command, check=True)

print("Segment created successfully.")
