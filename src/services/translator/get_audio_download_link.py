import asyncio
import json
import logging
from enum import Enum

from config.settings import TYPESCRIPT_PATH
from src.utils.languages import InputLanguage, OutputLanguage


class StateTranslation(Enum):
    SERVER_ERROR = "SERVER_ERROR"
    CLIENT_ERROR = "CLIENT_ERROR"
    LOADING = "LOADING"
    SUCCESS = "SUCCESS"


async def get_audio_download_link(
        input_lang: InputLanguage,
        output_lang: OutputLanguage,
        public_url: str
) -> str:
    """
    This function retrieves the download link for an audio file after a video translation process.

    :param input_lang: The input language of the video (InputLanguage)
    :param output_lang: The output language for the translation (OutputLanguage)
    :param public_url: The unique identifier of the video on YouTube
    :return: The URL to download the translated audio, or raises an error if the process fails
    """
    incompletion = True
    args = [
        "/root/.bun/bin/bun", "run", TYPESCRIPT_PATH,
        input_lang.value, output_lang.value, public_url
    ]

    while incompletion:
        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                try:
                    error_json = json.loads(stderr)
                    code = error_json.get("code")
                    if code == StateTranslation.SERVER_ERROR.value:
                        logging.error("Server error")
                        raise
                except (json.JSONDecodeError, KeyError):
                    raise RuntimeError(f"Unknown execution error: {stderr.strip()}")
            else:
                logging.info("Received response from server")
                data_json = json.loads(stdout)
                if not data_json["translated"]:
                    logging.info(f"{data_json['remainingTime']} seconds remaining for video url = {public_url}")
                    await asyncio.sleep(data_json["remainingTime"] + 30)
                else:
                    logging.info(f"Download link successfully retrieved: {data_json["url"]}")
                    return data_json["url"]

        except json.JSONDecodeError as e:
            raise RuntimeError("Failed to parse JSON from subprocess output") from e
