#!/usr/bin/env python3
"""
Cut an MP3 into ~14-minute chunks.
Every chunk **begins and ends with 1 s of pre-existing silence**.
No samples are added, deleted, or re-encoded.

Usage:
    python3 split_nopad.py input.mp3
"""

import subprocess, sys, os, shlex, tempfile

# --- user-tuneable constants ----------------------------------------------
TARGET_LEN   = 14 * 60          # 14 minutes
MAX_LEN      = 15 * 60          # soft ceiling; can be exceeded if no gap
NOISE_THRESH = "-30dB"          # silencedetect threshold
MIN_GAP      = 2.0              # only use silences ≥ 2 s
LEAVE_SIL    = 1.0              # keep 1 s at each side
# --------------------------------------------------------------------------

def run(cmd, quiet=False):
    if not quiet:
        print("➜", " ".join(shlex.quote(c) for c in cmd))
    subprocess.run(cmd, check=True)

def detect_silence(src, logfile):
    run([
        "ffmpeg", "-hide_banner", "-i", src,
        "-af", f"silencedetect=n={NOISE_THRESH}:d={MIN_GAP}",
        "-f", "null", "-"
    ], quiet=True, )
    # stderr already captured via shell redirection when function called

def parse_gaps(logfile):
    gaps, start = [], None
    with open(logfile) as f:
        for line in f:
            if "silence_start:" in line:
                start = float(line.split("silence_start:")[1].split()[0])
            elif "silence_end:" in line and start is not None:
                end = float(line.split("silence_end:")[1].split()[0])
                if end - start >= MIN_GAP:
                    gaps.append((start, end))
                start = None
    return gaps

def pick_split_points(gaps):
    points, cur = [], 0.0
    while gaps:
        target, ceiling = cur + TARGET_LEN, cur + MAX_LEN
        # silences whose **start** lies between cur+13 min and cur+15 min
        window = [g for g in gaps if cur + (TARGET_LEN - 60) <= g[0] <= ceiling]
        if window:
            # take gap whose start is closest to 14 min mark
            g = min(window, key=lambda x: abs(x[0] - target))
            split = g[0] + LEAVE_SIL              # 1 s into the gap
            points.append(split)
            cur = split
            # discard gaps we’ve passed
            gaps = [g for g in gaps if g[0] > cur]
        else:
            # no suitable silence before ceiling → look further ahead
            nxt = gaps[0][0] + LEAVE_SIL          # first future gap
            points.append(nxt)
            cur = nxt
            gaps = [g for g in gaps if g[0] > cur]
    return points

def segment(src, points, pattern):
    times = ",".join(f"{p:.3f}" for p in points)
    run([
        "ffmpeg", "-hide_banner", "-i", src,
        "-c", "copy", "-map", "0",
        "-f", "segment",
        "-segment_times", times,
        "-reset_timestamps", "1",            # fresh time-base per file :contentReference[oaicite:2]{index=2}
        pattern
    ])

def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 split_nopad.py <input.mp3>")
    infile = sys.argv[1]
    outpat = f"{os.path.splitext(os.path.basename(infile))[0]}_%03d.mp3"

    with tempfile.TemporaryDirectory() as tmp:
        log = os.path.join(tmp, "sil.log")
        # 1) detect and capture stderr to log
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-i", infile,
             "-af", f"silencedetect=n={NOISE_THRESH}:d={MIN_GAP}",
             "-f", "null", "-"],
            stderr=open(log, "w"), stdout=subprocess.DEVNULL, text=True, check=True)

        # 2) harvest silence pairs
        silences = parse_gaps(log)
        if not silences:
            sys.exit("❌  No ≥2 s silences found; nothing to do.")

        # 3) choose cut points & split
        splits = pick_split_points(silences)
        segment(infile, splits, outpat)

    print("✅  Segments written to:", os.getcwd())

if __name__ == "__main__":
    main()
