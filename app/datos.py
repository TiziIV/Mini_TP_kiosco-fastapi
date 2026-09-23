"""Repositorio en memoria del kiosco y notificador."""

import asyncio
from decimal import Decimal
from typing import Optional

from app.errores import (
    ErrorDominio,
    ProductoInexistente,
    ProductoNoHabilitado,
    StockInsuficiente,
    StockReservadoExcedido,
)
from app.modelos import ProductoActualizar, ProductoCrear, ProductoRespuesta


class CatalogoRepositorio:
    """Gestiona los productos en memoria. Se instancia en el lifespan (R4)
    y se inyecta por Depends() (R2).
    """

    def __init__(self) -> None:
        self._candado = asyncio.Lock()
        self._contador_id = 3
        # Catálogo inicial con Decimal (R6)
        self._productos: dict[int, dict] = {
            1: {
                "id": 1,
                "nombre": "Alfajor Guaymallén",
                "precio": Decimal("650.00"),
                "stock": 25,
                "stock_reservado": 0,
                "habilitado": True,
                "categoria": "Golosinas",
            },
            2: {
                "id": 2,
                "nombre": "Gaseosa 500ml",
                "precio": Decimal("1800.00"),
                "stock": 10,
                "stock_reservado": 2,
                "habilitado": True,
                "categoria": "Bebidas",
            },
            3: {
                "id": 3,
                "nombre": "Chicle Menta",
                "precio": Decimal("300.00"),
                "stock": 0,
                "stock_reservado": 0,
                "habilitado": False,
                "categoria": "Golosinas",
            },
        }

    # R1: Métodos declarados con async def y simulación de consulta
    async def listar(self, offset: int, limit: int) -> tuple[list[ProductoRespuesta], int]:
        await asyncio.sleep(0.05)
        total = len(self._productos)
        items = list(self._productos.values())[offset : offset + limit]
        return [ProductoRespuesta(**p) for p in items], total

    async def obtener(self, producto_id: int) -> ProductoRespuesta:
        await asyncio.sleep(0.05)
        producto = self._productos.get(producto_id)
        if not producto:
            raise ProductoInexistente(producto_id)
        return ProductoRespuesta(**producto)

    async def crear(self, datos: ProductoCrear) -> ProductoRespuesta:
        await asyncio.sleep(0.05)
        async with self._candado:
            self._contador_id += 1
            nuevo_id = self._contador_id
            nuevo_dict = {"id": nuevo_id, **datos.model_dump()}
            self._productos[nuevo_id] = nuevo_dict
            return ProductoRespuesta(**nuevo_dict)

    # R10: Distingue campo no enviado de enviado como null explícito
    async def actualizar(self, producto_id: int, datos: ProductoActualizar) -> ProductoRespuesta:
        await asyncio.sleep(0.05)
        async with self._candado:
            if producto_id not in self._productos:
                raise ProductoInexistente(producto_id)

            prod = self._productos[producto_id]
            # exclude_unset=True: solo los campos que el cliente envió (incluido
            # un null explícito en "categoria"); los no enviados no se tocan.
            valores_enviados = datos.model_dump(exclude_unset=True)

            # Se arma el producto resultante en una copia y se valida ANTES de
            # tocar el catálogo, así un PATCH inválido nunca deja datos a medias.
            candidato = {**prod, **valores_enviados}
            if candidato["stock_reservado"] > candidato["stock"]:
                raise StockReservadoExcedido(candidato["stock_reservado"], candidato["stock"])
            respuesta = ProductoRespuesta(**candidato)

            self._productos[producto_id] = candidato
            return respuesta

    # R11 y R12: Verificaciones concurrentes y descuento protegido bajo Lock
    async def comprar(self, producto_id: int, cantidad: int) -> ProductoRespuesta:
        await asyncio.sleep(0.05)
        if producto_id not in self._productos:
            raise ProductoInexistente(producto_id)

        async with self._candado:
            prod = self._productos[producto_id]

            async def check_habilitado():
                await asyncio.sleep(0.02)
                if not prod["habilitado"]:
                    raise ProductoNoHabilitado(producto_id)

            async def check_stock():
                await asyncio.sleep(0.02)
                disponible = prod["stock"] - prod["stock_reservado"]
                if disponible < cantidad:
                    raise StockInsuficiente(disponible, cantidad)

            # R11: TaskGroup desempaquetando la excepción de dominio
            try:
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(check_habilitado())
                    tg.create_task(check_stock())
            except* ErrorDominio as eg:
                # Relanzamos el primer error de dominio que falló
                raise eg.exceptions[0]

            # R12: Resta protegida bajo el candado
            prod["stock"] -= cantidad
            return ProductoRespuesta(**prod)


class Notificador:
    def __init__(self) -> None:
        self.enviados = 0

    async def enviar(self, mensaje: str) -> None:
        await asyncio.sleep(0.1)
        self.enviados += 1
        print(f"[notificador-kiosco] {mensaje} (total enviados: {self.enviados})")