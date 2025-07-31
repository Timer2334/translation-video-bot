import logging
import os

from config.settings import AUDIO_PATH, OUTPUT_PATH, TOKEN_FOR_YANDEX, VIDEO_PATH
from src.services.translator.async_delete_file import async_delete_file
from src.services.translator.download_and_save_file import download_and_save_file
from src.services.translator.get_audio_download_link import get_audio_download_link
from src.services.translator.merge_video_audio import merge_video_audio
from src.services.translator.yandex_disk_service import YandexDiskService
from src.utils.languages import InputLanguage, OutputLanguage
from src.services.translator.base_translator import BaseTranslator


class FileTranslator(BaseTranslator):

    async def run(
            self,
            video_path: str,
            audio_name: str,
            output_name: str,
            input_lang: InputLanguage,
            output_lang: OutputLanguage
    ):
        yandex_disk_service = YandexDiskService(TOKEN_FOR_YANDEX)
        try:
            public_url = await yandex_disk_service.upload_and_get_public_url(
                video_path,
                os.path.basename(video_path)
            )
            download_link = await get_audio_download_link(
                input_lang,
                output_lang,
                public_url
            )
            await download_and_save_file(
                download_link,
                AUDIO_PATH / audio_name
            )
            await merge_video_audio(
                video_path,
                AUDIO_PATH / audio_name,
                OUTPUT_PATH / output_name
            )
            logging.info("Video has been translated successfully :)")
        except Exception as e:
            logging.error("Error during file translation process")
            logging.exception(e)
        finally:
            await yandex_disk_service.delete_file_permanently(os.path.basename(video_path))
            await async_delete_file(video_path)
            await async_delete_file(AUDIO_PATH / audio_name)
            logging.info("File translation process finished")
