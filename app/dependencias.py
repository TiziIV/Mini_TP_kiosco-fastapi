"""Dependencias compartidas (R2): cómo los handlers reciben el repositorio y el notificador.

Las instancias se crean UNA sola vez en el lifespan (app/main.py, R4) y quedan
en app.state; acá solo se las entrega a cada handler vía Depends().
"""

from fastapi import Request

from app.datos import CatalogoRepositorio, Notificador


async def get_repo(request: Request) -> CatalogoRepositorio:
    return request.app.state.catalogo


async def get_notificador(request: Request) -> Notificador:
    return request.app.state.notificador
