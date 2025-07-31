import asyncio
import logging
import os
from pathlib import Path


async def async_delete_file(file_path: str | Path):
    try:
        await asyncio.to_thread(os.remove, file_path)
        logging.info(f"File '{file_path}' deleted successfully.")
    except FileNotFoundError:
        logging.error(f"File '{file_path}' not found.")
    except PermissionError:
        logging.error(f"Permission denied: cannot delete file '{file_path}'.")
    except Exception as e:
        logging.error(f"An error occurred while deleting '{file_path}': {e}")
