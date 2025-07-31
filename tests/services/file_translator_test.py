import asyncio
from pathlib import Path

from src.utils.languages import InputLanguage, OutputLanguage
from src.services.translator.file_translator import FileTranslator


async def file_translator_test():
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_translator = FileTranslator()
    await file_translator.run(
        video_path="/home/timer2334/TranslationVideo/data/temp/eng.mp4",
        audio_name="xxx.mp3",
        output_name="out.mp4",
        input_lang=InputLanguage.ENGLISH,
        output_lang=OutputLanguage.RUSSIAN
    )


if __name__ == '__main__':
    asyncio.run(file_translator_test())
