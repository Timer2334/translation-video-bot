import logging

import aiofiles
import yadisk


class YandexDiskService:
    def __init__(self, token: str):
        logging.info("YandexDiskService initialized")
        self.__token = token

    async def upload_and_get_public_url(self, file_path: str, file_name: str) -> str:
        async with yadisk.AsyncClient(token=self.__token, session="httpx") as client:
            # Загружаем файл
            try:
                async with aiofiles.open(f"{file_path}", "rb") as file:
                    logging.info(f"Starting upload of file {file_name}")
                    await client.upload(
                        file,
                        f"/{file_name}",
                        overwrite=True,
                        timeout=(10.0, 3600.0),
                        n_retries=3,
                        retry_interval=5.0
                    )
                    logging.info(f"File uploaded successfully: {file_name}")
            except FileNotFoundError:
                logging.error(f"File {file_path} not found.")
                raise

            # Публикуем файл
            await client.publish(f"/{file_name}")

            # Получаем метаинформацию и публичную ссылку
            meta = await client.get_meta(f"/{file_name}")
            return meta.public_url

    async def delete_file_permanently(self, file_name: str):
        # Безвозвратно удаляет
        logging.info(f"Deleting file from cloud storage: {file_name}")
        async with yadisk.AsyncClient(token=self.__token) as client:
            await client.remove(f"/{file_name}", permanently=True)
