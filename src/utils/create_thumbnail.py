import asyncio
import logging
from pathlib import Path


async def create_thumbnail(filepath: str | Path, output_path: str | Path) -> None:
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-i", filepath,
        "-frames:v", "1",
        "-vf", "scale=320:320:force_original_aspect_ratio=decrease",
        output_path,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE
    )

    _, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{stderr.decode().strip()}")

    logging.info(f"Thumbnail successfully created with filename: {Path(output_path).name}")
