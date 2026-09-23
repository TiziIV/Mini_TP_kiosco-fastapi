"""Comparación directa (R14): la MISMA tarea escrita de forma secuencial
vs concurrente con TaskGroup para evidenciar la diferencia en tiempos reales.

Ambas versiones consultan siempre los mismos 3 productos, así la duración
esperada es fija: ~900 ms (secuencial) vs ~300 ms (concurrente).
"""

import asyncio
import time

from fastapi import APIRouter, Depends

from app.datos import CatalogoRepositorio
from app.dependencias import get_repo
from app.modelos import ComparacionRespuesta, ProductoRespuesta

router = APIRouter()

CANTIDAD_CONSULTAS = 3
DEMORA_CONSULTA_S = 0.3


def _disponibilidad(producto: ProductoRespuesta) -> dict:
    disponible = producto.habilitado and (producto.stock - producto.stock_reservado) > 0
    return {
        "producto_id": producto.id,
        "nombre": producto.nombre,
        "disponible": disponible,
    }


def _consultar_disponibilidad_sync(producto: ProductoRespuesta) -> dict:
    """Versión sincrónica: bloquea el hilo con time.sleep."""
    time.sleep(DEMORA_CONSULTA_S)
    return _disponibilidad(producto)


async def _consultar_disponibilidad_async(producto: ProductoRespuesta) -> dict:
    """Versión asincrónica: cede el control con await asyncio.sleep."""
    await asyncio.sleep(DEMORA_CONSULTA_S)
    return _disponibilidad(producto)


@router.get("/sincrono", response_model=ComparacionRespuesta)
async def comparar_sincrono(repo: CatalogoRepositorio = Depends(get_repo)):
    """GET /comparacion/sincrono -- consultas secuenciales bloqueantes (~900 ms)."""
    # Se lee el catálogo por su interfaz (async) y recién después se empieza a medir.
    productos, _ = await repo.listar(offset=0, limit=CANTIDAD_CONSULTAS)

    inicio = time.perf_counter()
    resultados = [_consultar_disponibilidad_sync(p) for p in productos]
    duracion_ms = (time.perf_counter() - inicio) * 1000

    return {
        "resultados": resultados,
        "duracion_ms": round(duracion_ms),
        "explicacion": "Cada consulta bloqueó el bucle de eventos de forma secuencial.",
    }


@router.get("/asincrono", response_model=ComparacionRespuesta)
async def comparar_asincrono(repo: CatalogoRepositorio = Depends(get_repo)):
    """GET /comparacion/asincrono -- consultas concurrentes con TaskGroup (~300 ms)."""
    productos, _ = await repo.listar(offset=0, limit=CANTIDAD_CONSULTAS)

    inicio = time.perf_counter()
    async with asyncio.TaskGroup() as grupo:
        tareas = [grupo.create_task(_consultar_disponibilidad_async(p)) for p in productos]

    resultados = [t.result() for t in tareas]
    duracion_ms = (time.perf_counter() - inicio) * 1000

    return {
        "resultados": resultados,
        "duracion_ms": round(duracion_ms),
        "explicacion": "Las consultas corrieron de forma concurrente con TaskGroup solapando los tiempos de espera.",
    }
