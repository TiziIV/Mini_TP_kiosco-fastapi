"""Esquemas Pydantic para el Kiosco (Capítulo 2: Contratos)."""

from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, model_validator

# Campos de Producto que NO admiten null. Solo "categoria" es opcional/nulable.
CAMPOS_NO_NULABLES = {"nombre", "precio", "stock", "stock_reservado", "habilitado"}


# R5 y R7: Modelo para crear productos
class ProductoCrear(BaseModel):
    nombre: str = Field(min_length=1, description="Nombre obligatorio del producto")
    # R6: El precio se modela con Decimal, mayor a 0
    precio: Decimal = Field(gt=0, decimal_places=2, description="Precio unitario mayor a 0")
    # R7: Validación sobre un solo campo con Field
    stock: int = Field(ge=0, description="Stock disponible, mayor o igual a 0")
    stock_reservado: int = Field(default=0, ge=0, description="Stock reservado, no puede superar al stock")
    habilitado: bool = Field(default=True, description="Indica si el producto está a la venta")
    categoria: Optional[str] = Field(default=None, description="Categoría opcional")

    # R7: Validación que involucra dos campos a la vez
    @model_validator(mode="after")
    def verificar_stock_reservado(self) -> "ProductoCrear":
        if self.stock_reservado > self.stock:
            raise ValueError("El stock reservado no puede ser mayor al stock total disponible.")
        return self


# R5 y R10: Modelo para actualizar parcialmente (PATCH)
class ProductoActualizar(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=1)
    precio: Optional[Decimal] = Field(default=None, gt=0, decimal_places=2)
    stock: Optional[int] = Field(default=None, ge=0)
    stock_reservado: Optional[int] = Field(default=None, ge=0)
    habilitado: Optional[bool] = None
    categoria: Optional[str] = None

    # R10: null explícito solo tiene sentido en "categoria". En los demás campos
    # se rechaza acá, antes de tocar el catálogo (si no, quedaría un producto roto).
    @model_validator(mode="after")
    def sin_null_en_campos_no_nulables(self) -> "ProductoActualizar":
        for campo in self.model_fields_set & CAMPOS_NO_NULABLES:
            if getattr(self, campo) is None:
                raise ValueError(f"'{campo}' no puede ser null (solo 'categoria' admite null).")
        return self

    # R7: validación entre dos campos. Si solo se envía uno de los dos, la
    # verificación contra el valor ya guardado la hace el repositorio.
    @model_validator(mode="after")
    def verificar_stock_reservado(self) -> "ProductoActualizar":
        if self.stock is not None and self.stock_reservado is not None:
            if self.stock_reservado > self.stock:
                raise ValueError("El stock reservado no puede ser mayor al stock total.")
        return self


# R5: Modelo para lectura (lo que responde la API)
class ProductoRespuesta(BaseModel):
    id: int
    nombre: str
    precio: Decimal
    stock: int
    stock_reservado: int
    habilitado: bool
    categoria: Optional[str] = None


# Modelo para la operación de compra puntual
class CompraCrear(BaseModel):
    cantidad: int = Field(gt=0, description="Cantidad a comprar, debe ser mayor a 0")


# R3: respuesta de /comparacion/*. "resultados" es una lista de dicts (y no de
# otro modelo) para respetar la regla de que ningún modelo tenga un campo
# tipado como otro modelo.
class ComparacionRespuesta(BaseModel):
    resultados: list[dict]
    duracion_ms: int
    explicacion: str
