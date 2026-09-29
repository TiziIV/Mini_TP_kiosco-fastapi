import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import httpx
from app.main import app
from app.database import async_session, ProductoModel, init_db
from sqlalchemy import delete


async def test_kiosco_api():
    print("Iniciando pruebas de integración...")
    
    # Run init_db and clean
    await init_db()
    async with async_session() as session:
        await session.execute(delete(ProductoModel))
        await session.commit()
    
    # Re-init to seed default products
    await init_db()

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Test listar productos (should seed 3 initial products)
            response = await ac.get("/productos")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            productos = response.json()
            assert len(productos) == 3, f"Expected 3 products, got {len(productos)}"
            assert response.headers.get("X-Total-Count") == "3"
            assert productos[0]["nombre"] == "Alfajor Guaymallén"
            print("[OK] Listar productos")

            # 2. Test obtener producto por ID
            response = await ac.get("/productos/1")
            assert response.status_code == 200
            assert response.json()["nombre"] == "Alfajor Guaymallén"
            print("[OK] Obtener producto por ID")

            # 3. Test obtener producto inexistente (404)
            response = await ac.get("/productos/999")
            assert response.status_code == 404
            assert response.json()["error"]["codigo"] == "PRODUCTO_INEXISTENTE"
            print("[OK] Obtener producto inexistente (404)")

            # 4. Test crear producto (201 Created)
            nuevo_prod = {
                "nombre": "Chocolate Águila",
                "precio": 1200.50,
                "stock": 15,
                "stock_reservado": 0,
                "habilitado": True,
                "categoria": "Golosinas"
            }
            response = await ac.post("/productos", json=nuevo_prod)
            assert response.status_code == 201
            creado = response.json()
            assert creado["nombre"] == "Chocolate Águila"
            print("[OK] Crear producto (201)")

            # 5. Test actualizar producto (PATCH)
            prod_id = creado["id"]
            patch_data = {"precio": 1300.00}
            response = await ac.patch(f"/productos/{prod_id}", json=patch_data)
            assert response.status_code == 200
            assert response.json()["precio"] == "1300.00"
            print("[OK] Actualizar producto (PATCH)")

            # 6. Test comprar producto exitoso
            # Producto 2 (Gaseosa 500ml): stock 10, stock_reservado 2 -> disponible neto 8
            response = await ac.post("/productos/2/comprar", json={"cantidad": 3})
            assert response.status_code == 200
            assert response.json()["stock"] == 7
            print("[OK] Comprar producto exitoso")

            # 7. Test comprar producto con stock insuficiente (409)
            response = await ac.post("/productos/2/comprar", json={"cantidad": 100})
            assert response.status_code == 409
            assert response.json()["error"]["codigo"] == "STOCK_INSUFICIENTE"
            print("[OK] Comprar producto stock insuficiente (409)")

            # 8. Test endpoints de comparación
            response = await ac.get("/comparacion/sincrono")
            assert response.status_code == 200
            assert "resultados" in response.json()
            print("[OK] Comparación síncrona")

            response = await ac.get("/comparacion/asincrono")
            assert response.status_code == 200
            assert "resultados" in response.json()
            print("[OK] Comparación asíncrona")

    print("¡Todas las pruebas de integración pasaron exitosamente!")


if __name__ == "__main__":
    asyncio.run(test_kiosco_api())
