#!/usr/bin/env python3
"""
Cut an MP3 into ~14-minute chunks accurately.
Splits occur inside detected silences, as close to the target duration as possible.
Fixed: Infinite loop bug and inaccurate split point selection.
"""

import subprocess
import sys
import os
import re
import shlex
import tempfile

# --- User-tuneable constants ------------------------------------------------
TARGET_LEN   = 14 * 60          # Ideal chunk length (14 minutes)
MAX_LEN      = 15 * 60          # Hard ceiling; split sooner if possible
MIN_LEN      = 13 * 60          # Hard floor; don't split before this
NOISE_THRESH = "-30dB"          # Silence detection threshold
MIN_GAP      = 2.0              # Minimum duration of silence to consider
LEAVE_SIL    = 1.0              # Seconds of silence to preserve at edges
# ----------------------------------------------------------------------------

def run(cmd, quiet=False):
    if not quiet:
        print("➜", " ".join(shlex.quote(c) for c in cmd))
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def detect_silence(src, logfile):
    cmd = [
        "ffmpeg", "-hide_banner", "-i", src,
        "-af", f"silencedetect=noise={NOISE_THRESH}:d={MIN_GAP}",
        "-f", "null", "-"
    ]
    with open(logfile, "w") as log_fh:
        subprocess.run(cmd, stderr=log_fh, stdout=subprocess.DEVNULL, text=True)

def parse_gaps(logfile):
    gaps = []
    start = None
    silence_start_re = re.compile(r"silence_start:\s*([\d.]+)")
    silence_end_re   = re.compile(r"silence_end:\s*([\d.]+)")

    with open(logfile) as f:
        for line in f:
            if "silence_start" in line:
                match = silence_start_re.search(line)
                if match: start = float(match.group(1))
            elif "silence_end" in line and start is not None:
                match = silence_end_re.search(line)
                if match:
                    end = float(match.group(1))
                    if end - start >= MIN_GAP:
                        gaps.append((start, end))
                    start = None
    return gaps

def pick_split_points(gaps):
    points = []
    cur = 0.0
    
    # We loop as long as there are potential gaps to split at
    while gaps:
        target = cur + TARGET_LEN
        min_split = cur + MIN_LEN
        
        best_split = None
        min_dist = float('inf')
        
        # Iterate through all remaining gaps to find the best candidate
        for s, e in gaps:
            # 1. Determine where we can physically cut inside this gap
            # We need 1s padding from start and end
            gap_start_cut = s + LEAVE_SIL
            gap_end_cut = e - LEAVE_SIL
            
            if gap_start_cut > gap_end_cut:
                continue # Gap too short for padding

            # 2. Determine the ideal cut point within this specific gap
            # We want to cut as close to 'target' as possible
            if target < gap_start_cut:
                candidate = gap_start_cut
            elif target > gap_end_cut:
                candidate = gap_end_cut
            else:
                candidate = target
            
            # 3. Check constraints: Must not be too short
            if candidate < min_split:
                # This gap is too early. 
                # If the gap ends before our minimum allowed split time, 
                # we can mark it for removal later, but for now just skip it.
                if e < min_split:
                    continue
                # If the gap overlaps our min_split, we might be forced to cut at min_split
                # (provided min_split is inside the gap)
                if gap_start_cut <= min_split <= gap_end_cut:
                    candidate = min_split
                else:
                    continue

            # 4. Score this candidate (distance to target)
            dist = abs(candidate - target)
            
            # Prefer the candidate closest to target. 
            # Tie-breaker: prefer earlier gap if distances are equal? 
            # (Implicitly handled by list order usually, but strict < is fine)
            if dist < min_dist:
                min_dist = dist
                best_split = candidate

        # --- Decision Time ---
        if best_split is None:
            # No gaps found that satisfy constraints.
            # This means we have reached the end of usable gaps.
            break
        
        # We found a valid split point
        points.append(best_split)
        cur = best_split
        
        # Filter gaps: remove gaps that are now behind us.
        # A gap is "used" if it ends before our new current time.
        # Note: We keep gaps that might overlap the new 'cur' (long silences)
        # But the loop logic will naturally skip them next time because 
        # 'min_split' will have advanced.
        gaps = [g for g in gaps if g[1] > cur]

    return points

def segment(src, points, pattern):
    times = ",".join(f"{p:.3f}" for p in points)
    # We must allow ffmpeg to overwrite
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-i", src,
        "-c", "copy", "-map", "0",
        "-f", "segment",
        "-segment_times", times,
        "-reset_timestamps", "1",
        pattern
    ]
    run(cmd)

def get_duration(src):
    cmd = [
        "ffprobe", "-v", "error", 
        "-show_entries", "format=duration", 
        "-of", "default=noprint_wrappers=1:nokey=1", 
        src
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None

def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 split_nopad.py <input.mp3>")
    
    infile = sys.argv[1]
    outpat = f"{os.path.splitext(os.path.basename(infile))[0]}_%03d.mp3"
    
    total_duration = get_duration(infile)
    if total_duration:
        print(f"ℹ️  Input duration: {total_duration/60:.2f} minutes")

    with tempfile.TemporaryDirectory() as tmp:
        log = os.path.join(tmp, "sil.log")
        
        print("🔍 Detecting silence...")
        detect_silence(infile, log)
        
        silences = parse_gaps(log)
        if not silences:
            sys.exit("❌  No silences found matching criteria.")
        
        print(f"✅  Found {len(silences)} silence intervals.")

        splits = pick_split_points(silences)
        
        if not splits:
            print("ℹ️  No split points needed or possible.")
            return

        print(f"✂️  Splitting at: {[f'{s/60:.2f}m' for s in splits]}")
        segment(infile, splits, outpat)

    print(f"✅  Done. Segments written to: {os.getcwd()}")

if __name__ == "__main__":
    main()
