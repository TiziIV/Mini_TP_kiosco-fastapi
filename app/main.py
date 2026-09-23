"""Punto de entrada principal para el Kiosco."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.comparacion import router as comparacion_router
from app.datos import CatalogoRepositorio, Notificador
from app.errores import ErrorDominio, manejador_error_dominio
from app.productos import router as productos_router

DIR_ESTATICOS = Path(__file__).resolve().parent.parent / "static"


# R4: El repositorio y notificador se instancian una sola vez en el lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.catalogo = CatalogoRepositorio()
    app.state.notificador = Notificador()
    yield


app = FastAPI(
    title="Mini TP Kiosco - UTN FRM",
    description="Catálogo de productos y compras asincrónicas",
    version="1.0.0",
    lifespan=lifespan,
)

# R9: Manejador propio para errores del dominio
app.add_exception_handler(ErrorDominio, manejador_error_dominio)

# Routers requeridos
app.include_router(productos_router, prefix="/productos", tags=["productos"])
app.include_router(comparacion_router, prefix="/comparacion", tags=["comparacion"])

if DIR_ESTATICOS.exists():
    app.mount("/static", StaticFiles(directory=DIR_ESTATICOS), name="static")

    @app.get("/", include_in_schema=False)
    async def raiz():
        return FileResponse(DIR_ESTATICOS / "index.html")