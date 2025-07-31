import os
import hashlib
import shutil
import logging
import asyncio
import subprocess
from pathlib import Path

import aiohttp
from aiogram import Router
from aiogram.types import Message

from config.settings import (
    ALLOWED_EXTENSIONS,
    BASE_USERS_DIR,
    TELEGRAM_VIDEOS_DIR,
    TELEGRAM_DOCS_DIR,
)
from src.telegram_bot.handlers.commands import get_main_menu

from src.telegram_bot.db import (
    create_user,
    get_user,
    set_free_video,
    update_minutes_balance,
)
from src.telegram_bot.texts import (
    TEXT_UNSUPPORTED_FORMAT,
    TEXT_UNSUPPORTED_VIDEO,
)
from src.services.translator.file_translator import FileTranslator
from src.utils.languages import InputLanguage, OutputLanguage
from src.telegram_bot.user_state import user_db, files_db

router_files = Router()

LANG_MAP_INPUT = {
    "en": InputLanguage.ENGLISH,
    "ru": InputLanguage.RUSSIAN,
    "zh": InputLanguage.CHINESE,
    "ko": InputLanguage.KOREAN,
    "ar": InputLanguage.ARABIC,
    "fr": InputLanguage.FRENCH,
    "it": InputLanguage.ITALIAN,
    "es": InputLanguage.SPANISH,
    "de": InputLanguage.GERMAN,
    "ja": InputLanguage.JAPANESE,
}
LANG_MAP_OUTPUT = {
    "ru": OutputLanguage.RUSSIAN,
    "en": OutputLanguage.ENGLISH,
    "kk": OutputLanguage.KAZAKH,
}


def create_user_folders(user_id: int):
    user_folder = os.path.join(BASE_USERS_DIR, str(user_id))
    waiting_folder = os.path.join(user_folder, "waiting_for_translation")
    translated_folder = os.path.join(user_folder, "translated_video")
    os.makedirs(waiting_folder, exist_ok=True)
    os.makedirs(translated_folder, exist_ok=True)
    return user_folder, waiting_folder, translated_folder


def get_user_waiting_folder(user_id: int) -> str:
    return os.path.join(BASE_USERS_DIR, str(user_id), "waiting_for_translation")


def get_user_translated_folder(user_id: int) -> str:
    return os.path.join(BASE_USERS_DIR, str(user_id), "translated_video")


def get_video_duration_seconds(filepath: str) -> int:
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_entries",
            "format=duration",
            filepath,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        import json

        data = json.loads(result.stdout)
        duration_float = float(data["format"]["duration"])
        return int(duration_float)
    except:
        return 0


def round_video_minutes(total_seconds: int) -> int:
    base_minutes = total_seconds // 60
    remainder = total_seconds % 60
    if remainder >= 30:
        base_minutes += 1
    return base_minutes


def check_and_reserve_video_minutes(user_id: int, needed_minutes: int):
    row = get_user(user_id)
    if row is None:
        create_user(user_id)
        row = get_user(user_id)
    db_id, db_userid, minutes_balance, free_video, video_balance, banned = row
    if banned == 1:
        return False, minutes_balance, needed_minutes
    if free_video == 1:
        set_free_video(user_id, 0)
        return (True, minutes_balance, needed_minutes)
    if needed_minutes <= minutes_balance:
        new_balance = minutes_balance - needed_minutes
        update_minutes_balance(user_id, new_balance)
        return (True, new_balance, needed_minutes)
    else:
        return (False, minutes_balance, needed_minutes)


async def download_file_with_fallback(
        bot, file_info, desired_path: str, fallback_dir: str
) -> str:
    try:
        await bot.download_file(file_info.file_path, destination=desired_path)
        return desired_path
    except aiohttp.ClientResponseError as e:
        if e.status == 404:
            file_url = str(e.request_info.url)
            local_path = file_url.split("file/", 1)[-1]
            local_path = local_path.replace("%5C", "/").replace("\\", "/").strip()
            if local_path.startswith("C:/"):
                local_path = local_path[3:]
            local_filename = os.path.basename(local_path)
            fallback_path = os.path.join(fallback_dir, local_filename)
            if os.path.exists(fallback_path):
                if os.path.exists(desired_path):
                    try:
                        os.remove(desired_path)
                    except:
                        pass
                return fallback_path
            else:
                logging.error(f"Файл не найден по fallback-пути: {fallback_path}")
                return ""
        else:
            logging.error(f"Ошибка при скачивании файла: {e}")
            return ""


def move_file(source_path: str, target_folder: str) -> str:
    real_name = os.path.basename(source_path)
    moved_path = os.path.join(target_folder, real_name)
    shutil.move(source_path, moved_path)
    return real_name


def register_file(
        final_filename: str, file_type: str, user_id: int, full_path: str, msg_id: int
):
    file_id_short = hashlib.md5(full_path.encode()).hexdigest()[:8]
    files_db[file_id_short] = {
        "path": full_path,
        "type": file_type,
        "filename": final_filename,
        "user_id": user_id,
        "status": "pending",
        "message_id": msg_id,
    }


async def run_file_translator_async(
        user_id: int, waiting_path: str, final_filename: str
):
    loop = asyncio.get_event_loop()
    translated_filepath = os.path.join(
        get_user_translated_folder(user_id), f"translated_{final_filename}"
    )
    input_lang_enum = LANG_MAP_INPUT.get(
        user_db[user_id].get("source_lang", "en"), InputLanguage.ENGLISH
    )
    output_lang_enum = LANG_MAP_OUTPUT.get(
        user_db[user_id].get("target_lang", "ru"), OutputLanguage.RUSSIAN
    )
    translator = FileTranslator()

    await translator.run(
        audio_name=Path(waiting_path).with_suffix(".mp3").name,
        output_name=translated_filepath,
        input_lang=input_lang_enum,
        output_lang=output_lang_enum,
        video_path=waiting_path,
    )


@router_files.message(lambda msg: msg.document is not None)
async def handle_document(message: Message):
    from .commands import get_main_menu

    doc = message.document
    original_filename = doc.file_name or "document_unknown.mkv"
    ext = os.path.splitext(original_filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        await message.answer(TEXT_UNSUPPORTED_FORMAT)
        return
    user_id = message.from_user.id
    create_user_folders(user_id)
    file_info = await message.bot.get_file(doc.file_id, request_timeout=120)
    waiting_folder = get_user_waiting_folder(user_id)
    desired_path = os.path.join(waiting_folder, original_filename)
    final_path = await download_file_with_fallback(
        bot=message.bot,
        file_info=file_info,
        desired_path=desired_path,
        fallback_dir=TELEGRAM_DOCS_DIR,
    )
    final_filename = os.path.basename(final_path)
    total_seconds = get_video_duration_seconds(final_path)
    needed_minutes = round_video_minutes(total_seconds)
    success, current_balance, needed = check_and_reserve_video_minutes(
        user_id, needed_minutes
    )
    if not success:
        try:
            os.remove(final_path)
        except:
            pass
        lacking = needed - current_balance
        await message.answer(
            f"Недостаточно минут для перевода:\nУ вас <b>{current_balance}</b> мин., требуется <b>{needed}</b>, не хватает <b>{lacking}</b>.\nВозвращаю вас в меню...",
            reply_markup=get_main_menu(user_id),
            parse_mode="HTML",
        )
        return
    if not os.path.samefile(os.path.dirname(final_path), waiting_folder):
        final_filename = move_file(final_path, waiting_folder)
    sent_msg = await message.bot.send_sticker(message.from_user.id,
                                              sticker="CAACAgIAAxkBAAEOU5xoAq8dBGy8_HyBzwVyA40SZG6OFAACY2gAAmIXgEtQVGm3WF7MiTYE")
    register_file(
        final_filename,
        "document",
        user_id,
        os.path.join(waiting_folder, final_filename),
        sent_msg.message_id,
    )
    await asyncio.create_task(
        run_file_translator_async(
            user_id=user_id,
            waiting_path=os.path.join(waiting_folder, final_filename),
            final_filename=final_filename,
        )
    )


@router_files.message(lambda msg: msg.video is not None)
async def handle_video(message: Message):
    video = message.video
    original_filename = video.file_name or f"{video.file_unique_id}.mp4"
    ext = os.path.splitext(original_filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        await message.answer(TEXT_UNSUPPORTED_VIDEO)
        return
    user_id = message.from_user.id
    create_user_folders(user_id)
    file_info = await message.bot.get_file(video.file_id, request_timeout=120)
    waiting_folder = get_user_waiting_folder(user_id)
    desired_path = os.path.join(waiting_folder, original_filename)
    final_path = await download_file_with_fallback(
        bot=message.bot,
        file_info=file_info,
        desired_path=desired_path,
        fallback_dir=TELEGRAM_VIDEOS_DIR,
    )
    if not final_path or not os.path.exists(final_path):
        await message.answer("Не удалось скачать видео. Попробуйте ещё раз.")
        return
    final_filename = os.path.basename(final_path)
    total_seconds = get_video_duration_seconds(final_path)
    needed_minutes = round_video_minutes(total_seconds)
    success, current_balance, needed = check_and_reserve_video_minutes(
        user_id, needed_minutes
    )
    if not success:
        try:
            os.remove(final_path)
        except:
            pass
        lacking = needed - current_balance
        await message.answer(
            f"Недостаточно минут для перевода:\nУ вас <b>{current_balance}</b> мин., требуется <b>{needed}</b>, не хватает <b>{lacking}</b>.\nВозвращаю вас в меню...",
            reply_markup=get_main_menu(user_id),
            parse_mode="HTML",
        )
        return
    if not os.path.samefile(os.path.dirname(final_path), waiting_folder):
        final_filename = move_file(final_path, waiting_folder)
    sent_msg = await message.bot.send_sticker(message.from_user.id,
                                              sticker="CAACAgIAAxkBAAEOU5xoAq8dBGy8_HyBzwVyA40SZG6OFAACY2gAAmIXgEtQVGm3WF7MiTYE")
    register_file(
        final_filename,
        "video",
        user_id,
        os.path.join(waiting_folder, final_filename),
        sent_msg.message_id,
    )
    await asyncio.create_task(
        run_file_translator_async(
            user_id=user_id,
            waiting_path=os.path.join(waiting_folder, final_filename),
            final_filename=final_filename,
        )
    )
