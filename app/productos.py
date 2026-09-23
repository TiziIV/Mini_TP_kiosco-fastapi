"""Endpoints para el catálogo de productos y compras (Capítulos 1, 2 y 3)."""

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status

from app.datos import CatalogoRepositorio, Notificador
from app.dependencias import get_notificador, get_repo
from app.modelos import CompraCrear, ProductoActualizar, ProductoCrear, ProductoRespuesta

router = APIRouter()


# R1, R3, R8: Listado con paginación y total en Header (no en body)
@router.get("", response_model=list[ProductoRespuesta])
async def listar_productos(
    response: Response,
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0, le=100),
    repo: CatalogoRepositorio = Depends(get_repo),
):
    productos, total = await repo.listar(offset=offset, limit=limit)
    response.headers["X-Total-Count"] = str(total)
    return productos


# R1, R3: Obtener producto por ID
@router.get("/{producto_id}", response_model=ProductoRespuesta)
async def obtener_producto(
    producto_id: int,
    repo: CatalogoRepositorio = Depends(get_repo),
):
    return await repo.obtener(producto_id)


# R1, R3, R5: Crear producto (201 Created)
@router.post("", response_model=ProductoRespuesta, status_code=status.HTTP_201_CREATED)
async def crear_producto(
    datos: ProductoCrear,
    repo: CatalogoRepositorio = Depends(get_repo),
):
    return await repo.crear(datos)


# R1, R3, R5, R10: Actualizar producto (PATCH)
@router.patch("/{producto_id}", response_model=ProductoRespuesta)
async def actualizar_producto(
    producto_id: int,
    datos: ProductoActualizar,
    repo: CatalogoRepositorio = Depends(get_repo),
):
    return await repo.actualizar(producto_id, datos)


# R1, R3, R11, R12, R13: Comprar producto
@router.post("/{producto_id}/comprar", response_model=ProductoRespuesta)
async def comprar_producto(
    producto_id: int,
    compra: CompraCrear,
    background_tasks: BackgroundTasks,
    repo: CatalogoRepositorio = Depends(get_repo),
    notificador: Notificador = Depends(get_notificador),
):
    producto_actualizado = await repo.comprar(producto_id, compra.cantidad)
    
    # R13: Tarea en segundo plano con BackgroundTasks
    mensaje = f"Compra exitosa: {compra.cantidad} unidad(es) de '{producto_actualizado.nombre}'. Stock restante: {producto_actualizado.stock}"
    background_tasks.add_task(notificador.enviar, mensaje)
    
    return producto_actualizado