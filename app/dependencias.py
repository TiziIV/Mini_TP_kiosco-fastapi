"""Dependencias compartidas (R2): inyección de sesión asincrónica y repositorio."""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.datos import CatalogoRepositorio, Notificador


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


async def get_repo(session: AsyncSession = Depends(get_db)) -> CatalogoRepositorio:
    return CatalogoRepositorio(session)


async def get_notificador(request: Request) -> Notificador:
    return request.app.state.notificador
