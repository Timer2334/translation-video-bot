import os
import asyncio
import logging
from pathlib import Path

from aiogram.types import FSInputFile

from config.settings import OUTPUT_PATH
from src.services.translator.async_delete_file import async_delete_file
from src.telegram_bot.handlers.file_handlers import get_user_translated_folder
from src.telegram_bot.texts import TEXT_TRANSLATED_CAPTION
from src.telegram_bot.user_state import files_db
from src.utils.create_thumbnail import create_thumbnail
from src.utils.get_video_dimensions import get_video_dimensions


async def watch_translated_folder(bot):
    logging.info("Запуск watch_translated_folder...")
    while True:
        await asyncio.sleep(5)
        for file_id_short, info in list(files_db.items()):
            if info["status"] == "pending":
                user_id = info["user_id"]
                translated_path = os.path.join(
                    get_user_translated_folder(user_id), f"translated_{info['filename']}"
                )
                if os.path.exists(translated_path):
                    old_msg_id = info.get("message_id")
                    if old_msg_id:
                        try:
                            await bot.delete_message(user_id, old_msg_id)
                        except:
                            pass
                    fs_input = FSInputFile(translated_path)
                    if info["type"] == "video":
                        thumb = OUTPUT_PATH / f"{Path(translated_path).stem}.jpg"
                        await create_thumbnail(
                            filepath=translated_path,
                            output_path=thumb
                        )
                        width, height = await get_video_dimensions(translated_path)
                        await bot.send_video(
                            chat_id=user_id,
                            video=fs_input,
                            caption=TEXT_TRANSLATED_CAPTION,
                            width=width,
                            height=height,
                            thumbnail=FSInputFile(thumb),
                            supports_streaming=True
                        )
                        await async_delete_file(thumb)
                    else:
                        await bot.send_document(
                            chat_id=user_id,
                            video=fs_input,
                            caption=TEXT_TRANSLATED_CAPTION,
                            supports_streaming=True
                        )
                    info["status"] = "translated"
                    try:
                        os.remove(translated_path)
                        pass
                    except:
                        pass
                    try:
                        os.remove(info["path"])
                        pass
                    except:
                        pass
                    files_db.pop(file_id_short, None)
