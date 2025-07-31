import asyncio
import logging


async def merge_video_audio(
        video_path: str,
        audio_path: str,
        merged_video_path: str
):
    logging.info("Starting video and audio merging")
    process = await asyncio.create_subprocess_exec(
        "ffmpeg", "-i", video_path, "-i", audio_path,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "copy", merged_video_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        logging.error(f"FFmpeg failed with error:\n{stderr.decode().strip()}")
        raise

    logging.info("Video and audio merged successfully")
