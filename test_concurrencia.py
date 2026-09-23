"""Script de prueba de concurrencia real (R11 y R12).

Dispara varias compras del MISMO producto al mismo tiempo con asyncio.gather
y verifica que el stock final sea consistente (ninguna compra pisó a otra).

Requisito: el servidor tiene que estar corriendo (uvicorn app.main:app).
Para que el resultado coincida con el del README conviene reiniciarlo antes,
porque el catálogo vive en memoria y el stock se conserva entre corridas.
"""

import asyncio

import httpx

BASE_URL = "http://127.0.0.1:8000/productos"
PRODUCTO_ID = 2
CANTIDAD_POR_COMPRA = 3
CANTIDAD_DE_CLIENTES = 5


async def realizar_compra(cliente_num: int, client: httpx.AsyncClient) -> bool:
    print(f"[Cliente {cliente_num}] Enviando compra de {CANTIDAD_POR_COMPRA} unidades...")
    try:
        response = await client.post(
            f"{BASE_URL}/{PRODUCTO_ID}/comprar", json={"cantidad": CANTIDAD_POR_COMPRA}
        )
    except Exception as e:
        print(f"❌ [Cliente {cliente_num}] Excepción en cliente: {e}")
        return False

    if response.status_code == 200:
        print(f"✅ [Cliente {cliente_num}] COMPRA EXITOSA - Stock restante: {response.json()['stock']}")
        return True

    try:
        error_body = response.json()
    except Exception:
        error_body = response.text
    print(f"❌ [Cliente {cliente_num}] RECHAZADA ({response.status_code}): {error_body}")
    return False


async def main():
    print("=== INICIANDO PRUEBA DE CONCURRENCIA ===")
    async with httpx.AsyncClient(timeout=10.0) as client:
        antes = (await client.get(f"{BASE_URL}/{PRODUCTO_ID}")).json()
        disponible = antes["stock"] - antes["stock_reservado"]
        print(
            f"Producto {PRODUCTO_ID} antes: stock={antes['stock']}, "
            f"reservado={antes['stock_reservado']}, disponible neto={disponible}"
        )
        print(f"Simulando {CANTIDAD_DE_CLIENTES} compras concurrentes de {CANTIDAD_POR_COMPRA} unidades...")

        resultados = await asyncio.gather(
            *(realizar_compra(i, client) for i in range(1, CANTIDAD_DE_CLIENTES + 1))
        )

        despues = (await client.get(f"{BASE_URL}/{PRODUCTO_ID}")).json()

    exitosas = sum(resultados)
    esperadas = min(CANTIDAD_DE_CLIENTES, disponible // CANTIDAD_POR_COMPRA)
    stock_esperado = antes["stock"] - esperadas * CANTIDAD_POR_COMPRA

    print("\n=== VERIFICACIÓN ===")
    print(f"Compras exitosas: {exitosas} (esperadas: {esperadas})")
    print(f"Stock final: {despues['stock']} (esperado: {stock_esperado})")
    ok = exitosas == esperadas and despues["stock"] == stock_esperado
    print("RESULTADO: OK, sin condiciones de carrera" if ok else "RESULTADO: FALLÓ, hay inconsistencia")
    print("=== PRUEBA FINALIZADA ===")


if __name__ == "__main__":
    asyncio.run(main())
