"""Excepciones de dominio y formato de error normado (R9)."""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class ErrorDominio(HTTPException):
    """Base para errores normados del dominio."""
    def __init__(self, codigo: str, mensaje: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=mensaje)
        self.codigo = codigo
        self.mensaje = mensaje
        self.status_code = status_code


class ProductoInexistente(ErrorDominio):
    def __init__(self, producto_id: int):
        super().__init__(
            codigo="PRODUCTO_INEXISTENTE",
            mensaje=f"No se encontró el producto con ID {producto_id}.",
            status_code=404,
        )


class StockInsuficiente(ErrorDominio):
    def __init__(self, disponible: int, solicitado: int):
        super().__init__(
            codigo="STOCK_INSUFICIENTE",
            mensaje=f"Stock insuficiente. Disponible neto: {disponible}, solicitado: {solicitado}.",
            status_code=409,
        )


class ProductoNoHabilitado(ErrorDominio):
    def __init__(self, producto_id: int):
        super().__init__(
            codigo="PRODUCTO_NO_HABILITADO",
            mensaje=f"El producto con ID {producto_id} no está habilitado para la venta.",
            status_code=409,
        )


class StockReservadoExcedido(ErrorDominio):
    def __init__(self, reservado: int, stock: int):
        super().__init__(
            codigo="STOCK_RESERVADO_EXCEDIDO",
            mensaje=f"El stock reservado ({reservado}) no puede superar al stock ({stock}).",
            status_code=422,
        )


async def manejador_error_dominio(request: Request, exc: ErrorDominio) -> JSONResponse:
    """R9: Responde con formato propio y estable en lugar del {'detail': '...'} por defecto."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "codigo": exc.codigo,
                "mensaje": exc.mensaje,
            }
        },
    )