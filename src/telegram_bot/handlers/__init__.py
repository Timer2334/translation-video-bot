from aiogram import Router
from .commands import router_commands
from .callbacks import router_callbacks
from .file_handlers import router_files


def register_all_handlers(main_router: Router):
    main_router.include_router(router_commands)
    main_router.include_router(router_callbacks)
    main_router.include_router(router_files)
