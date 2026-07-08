"""Assemble the router from all handler modules."""
from router import Router
from handlers import (auth_handler, doctors_handler, appointments_handler,
                      admin_handler, ai_handler)


def build_router():
    router = Router()
    auth_handler.register(router)
    doctors_handler.register(router)
    appointments_handler.register(router)
    admin_handler.register(router)
    ai_handler.register(router)
    return router
