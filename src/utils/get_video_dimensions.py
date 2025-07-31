import asyncio
import json
import logging
from pathlib import Path


async def get_video_dimensions(filepath: str | Path) -> tuple[int, int]:
    process = await asyncio.create_subprocess_exec(
        "ffprobe",
        "-v", "error",
        "-show_entries", "stream=width,height",
        "-of", "json",
        filepath,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"ffprobe error: {stderr.strip()}")

    data = json.loads(stdout)
    streams = data.get("streams", [])
    if not streams:
        raise ValueError("No video streams found")

    width = streams[0].get("width")
    height = streams[0].get("height")

    logging.info(f"Extracted video resolution from file {Path(filepath).name}: width={width}, height={height}")

    return width, height
