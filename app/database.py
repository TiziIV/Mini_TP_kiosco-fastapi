"""Configuración de base de datos SQLAlchemy asincrónica con asyncpg y modelo Producto."""

import os
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Numeric, Integer, Boolean, select, text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/kiosco_db"
)

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


class ProductoModel(Base):
    __tablename__ = "productos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_reservado: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    habilitado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    categoria: Mapped[str | None] = mapped_column(String, nullable=True, default=None)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        result = await session.execute(select(ProductoModel))
        existing = result.scalars().first()
        if not existing:
            productos_iniciales = [
                ProductoModel(
                    id=1,
                    nombre="Alfajor Guaymallén",
                    precio=Decimal("650.00"),
                    stock=25,
                    stock_reservado=0,
                    habilitado=True,
                    categoria="Golosinas",
                ),
                ProductoModel(
                    id=2,
                    nombre="Gaseosa 500ml",
                    precio=Decimal("1800.00"),
                    stock=10,
                    stock_reservado=2,
                    habilitado=True,
                    categoria="Bebidas",
                ),
                ProductoModel(
                    id=3,
                    nombre="Chicle Menta",
                    precio=Decimal("300.00"),
                    stock=0,
                    stock_reservado=0,
                    habilitado=False,
                    categoria="Golosinas",
                ),
            ]
            session.add_all(productos_iniciales)
            await session.commit()
            
            # Ajustar la secuencia del ID para evitar conflictos con los IDs iniciales 1, 2, 3
            await session.execute(text("SELECT setval(pg_get_serial_sequence('productos', 'id'), 3, true);"))
            await session.commit()
