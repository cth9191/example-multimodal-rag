"""Split a video into segments for Gemini Embedding 2 (128s max per chunk)."""

import os
import subprocess
import cv2


def get_duration(video_path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", video_path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def chunk_video(
    input_path: str,
    output_dir: str = "assets/video",
    segment_duration: int = 97,
    overlap: int = 15,
) -> list[str]:
    """Split video into overlapping segments under 128s each.

    Returns list of output chunk file paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    duration = get_duration(input_path)
    chunks = []
    start = 0
    index = 0

    while start < duration:
        chunk_path = os.path.join(output_dir, f"chunk_{index:03d}.mp4")
        cmd = [
            "ffmpeg", "-y", "-ss", str(start), "-t", str(segment_duration),
            "-i", input_path, "-c", "copy", chunk_path,
        ]
        subprocess.run(cmd, capture_output=True)
        chunks.append(chunk_path)
        print(f"Created {chunk_path} (start={start}s)")
        start += segment_duration - overlap
        index += 1

    return chunks


def extract_thumbnail(video_path: str, output_path: str | None = None) -> str:
    """Extract the middle frame from a video as a JPEG thumbnail."""
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames // 2)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise RuntimeError(f"Failed to read frame from {video_path}")

    if output_path is None:
        base = os.path.splitext(video_path)[0]
        output_path = f"{base}_thumb.jpg"

    cv2.imwrite(output_path, frame)
    return output_path


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python video_chunker.py <video_file>")
        sys.exit(1)

    video_file = sys.argv[1]
    print(f"Chunking {video_file}...")
    chunk_paths = chunk_video(video_file)

    print(f"\nCreated {len(chunk_paths)} chunks. Extracting thumbnails...")
    for path in chunk_paths:
        thumb = extract_thumbnail(path)
        print(f"  Thumbnail: {thumb}")

    print("Done.")
