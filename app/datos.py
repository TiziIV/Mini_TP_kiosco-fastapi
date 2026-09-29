"""Repositorio PostgreSQL del kiosco y notificador."""

import asyncio
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import ProductoModel
from app.errores import (
    ErrorDominio,
    ProductoInexistente,
    ProductoNoHabilitado,
    StockInsuficiente,
    StockReservadoExcedido,
)
from app.modelos import ProductoActualizar, ProductoCrear, ProductoRespuesta


class CatalogoRepositorio:
    """Gestiona los productos en PostgreSQL mediante AsyncSession."""

    _candado = asyncio.Lock()

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def listar(self, offset: int, limit: int) -> tuple[list[ProductoRespuesta], int]:
        await asyncio.sleep(0.05)
        count_stmt = select(func.count()).select_from(ProductoModel)
        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = select(ProductoModel).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        productos = result.scalars().all()

        items = [
            ProductoRespuesta(
                id=p.id,
                nombre=p.nombre,
                precio=p.precio,
                stock=p.stock,
                stock_reservado=p.stock_reservado,
                habilitado=p.habilitado,
                categoria=p.categoria,
            )
            for p in productos
        ]
        return items, total

    async def obtener(self, producto_id: int) -> ProductoRespuesta:
        await asyncio.sleep(0.05)
        p = await self.session.get(ProductoModel, producto_id)
        if not p:
            raise ProductoInexistente(producto_id)
        return ProductoRespuesta(
            id=p.id,
            nombre=p.nombre,
            precio=p.precio,
            stock=p.stock,
            stock_reservado=p.stock_reservado,
            habilitado=p.habilitado,
            categoria=p.categoria,
        )

    async def crear(self, datos: ProductoCrear) -> ProductoRespuesta:
        await asyncio.sleep(0.05)
        async with self._candado:
            db_prod = ProductoModel(**datos.model_dump())
            self.session.add(db_prod)
            await self.session.commit()
            await self.session.refresh(db_prod)
            return ProductoRespuesta(
                id=db_prod.id,
                nombre=db_prod.nombre,
                precio=db_prod.precio,
                stock=db_prod.stock,
                stock_reservado=db_prod.stock_reservado,
                habilitado=db_prod.habilitado,
                categoria=db_prod.categoria,
            )

    async def actualizar(self, producto_id: int, datos: ProductoActualizar) -> ProductoRespuesta:
        await asyncio.sleep(0.05)
        async with self._candado:
            p = await self.session.get(ProductoModel, producto_id)
            if not p:
                raise ProductoInexistente(producto_id)

            valores_enviados = datos.model_dump(exclude_unset=True)

            candidato_stock = valores_enviados.get("stock", p.stock)
            candidato_reservado = valores_enviados.get("stock_reservado", p.stock_reservado)

            if candidato_reservado > candidato_stock:
                raise StockReservadoExcedido(candidato_reservado, candidato_stock)

            for key, value in valores_enviados.items():
                setattr(p, key, value)

            await self.session.commit()
            await self.session.refresh(p)

            return ProductoRespuesta(
                id=p.id,
                nombre=p.nombre,
                precio=p.precio,
                stock=p.stock,
                stock_reservado=p.stock_reservado,
                habilitado=p.habilitado,
                categoria=p.categoria,
            )

    async def comprar(self, producto_id: int, cantidad: int) -> ProductoRespuesta:
        await asyncio.sleep(0.05)
        p = await self.session.get(ProductoModel, producto_id)
        if not p:
            raise ProductoInexistente(producto_id)

        async with self._candado:
            p = await self.session.get(ProductoModel, producto_id)
            if not p:
                raise ProductoInexistente(producto_id)

            async def check_habilitado():
                await asyncio.sleep(0.02)
                if not p.habilitado:
                    raise ProductoNoHabilitado(producto_id)

            async def check_stock():
                await asyncio.sleep(0.02)
                disponible = p.stock - p.stock_reservado
                if disponible < cantidad:
                    raise StockInsuficiente(disponible, cantidad)

            try:
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(check_habilitado())
                    tg.create_task(check_stock())
            except* ErrorDominio as eg:
                raise eg.exceptions[0]

            p.stock -= cantidad
            await self.session.commit()
            await self.session.refresh(p)

            return ProductoRespuesta(
                id=p.id,
                nombre=p.nombre,
                precio=p.precio,
                stock=p.stock,
                stock_reservado=p.stock_reservado,
                habilitado=p.habilitado,
                categoria=p.categoria,
            )


class Notificador:
    def __init__(self) -> None:
        self.enviados = 0

    async def enviar(self, mensaje: str) -> None:
        await asyncio.sleep(0.1)
        self.enviados += 1
        print(f"[notificador-kiosco] {mensaje} (total enviados: {self.enviados})")
