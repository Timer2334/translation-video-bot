import logging

import aiofiles
import aiohttp


async def download_and_save_file(
        url: str,
        file_path: str
):
    """
    Asynchronously downloads a file from the specified ``URL`` and saves it locally
    under the given ``file_name``. If a file with the same name already exists,
    the operation is skipped to avoid overwriting.

    :param url: The URL from which to download the file.
    :param file_path: The name (including path) under which to save the file locally.
    :return: None
    """
    logging.info(f"Starting file download from URL: {url}")
    timeout = aiohttp.ClientTimeout(
        total=300,
        sock_connect=20,
        sock_read=60
    )
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as response:
            response.raise_for_status()
            try:
                async with aiofiles.open(file_path, 'xb') as file:
                    async for chunk in response.content.iter_chunked(64 * 1024):
                        chunk: bytes
                        await file.write(chunk)
            except FileExistsError:
                logging.warning("File already exists. Write operation was skipped.")
                raise
    logging.info("File download completed.")
