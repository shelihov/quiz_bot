from handlers.admin import admin_router
from handlers.user import user_router

def register_handlers(dp):
    dp.include_router(admin_router)
    dp.include_router(user_router)
