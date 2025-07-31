import asyncio

from config.settings import AUDIO_PATH
from src.services.translator.download_and_save_file import download_and_save_file
from src.services.translator.get_audio_download_link import get_audio_download_link
from src.utils.languages import InputLanguage, OutputLanguage


def typeScript_test():
    asyncio.run(
        download_and_save_file(
            url=asyncio.run(get_audio_download_link(
                InputLanguage.ENGLISH,
                OutputLanguage.RUSSIAN,
                "https://yadi.sk/d/C9boP2ldT-pMNA"
            )),
            file_path=f"{AUDIO_PATH}/LJM3MehVBlU.mp3"
        )
    )


if __name__ == '__main__':
    typeScript_test()
