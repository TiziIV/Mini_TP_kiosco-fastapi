# Mini TP — Kiosco: Catálogo con compras asincrónicas
**Programación III · TUP, UTN FRM**

Implementación de un catálogo para un kiosco que integra los fundamentos de FastAPI y ASGI (Capítulo 1), validaciones y contratos con Pydantic (Capítulo 2), y ejecución asincrónica con corrutinas, candados y tareas en segundo plano (Capítulo 3).

---

## 1. Cómo correrlo

**Requisito:** Python 3.11 o superior (se usan `asyncio.TaskGroup` y `except*`, que no existen en versiones anteriores).

1. Posicionarse en la carpeta raíz del proyecto:
   ```bash
   cd proyecto-tienda
   ```

2. Instalar las dependencias necesarias:
   ```bash
   pip install -r requirements.txt
   ```

3. Iniciar el servidor de desarrollo:
   ```bash
   uvicorn app.main:app --reload
   ```

4. Abrir la documentación interactiva en el navegador:
   - **Swagger UI**: `http://127.0.0.1:8000/docs`
   - **ReDoc**: `http://127.0.0.1:8000/redoc`

---

## 2. Cumplimiento de requisitos

El proyecto sigue una arquitectura modular y limpia respetando las consignas de la cátedra:

* **Capítulo 1 (Fundamentos y ASGI)**:
  - **R1**: Todos los handlers y métodos del repositorio están declarados con `async def` y simulan I/O mediante `await asyncio.sleep(0.05)`.
  - **R2**: El catálogo se inyecta en cada handler mediante dependencias de FastAPI (`Depends(get_repo)`, definida en `app/dependencias.py`).
  - **R3**: Cada endpoint, incluidos los de comparación, declara su `response_model` para documentar los esquemas reales en `/docs`.
  - **R4**: La instancia de `CatalogoRepositorio` y del `Notificador` se crean una única vez dentro del ciclo de vida (`lifespan`) de la aplicación en `app/main.py`.

* **Capítulo 2 (Contratos Pydantic)**:
  - **R5**: Se definen modelos diferenciados para la entidad: `ProductoCrear`, `ProductoActualizar` y `ProductoRespuesta`.
  - **R6**: El campo `precio` está tipado estrictamente con `Decimal` (mayor a 0), sin utilizar tipos de punto flotante (`float`).
  - **R7**: Se aplican validaciones de campo simple con `Field` y validación de modelo (`@model_validator`) que garantiza que `stock_reservado <= stock`.
  - **R8**: El listado (`GET /productos`) soporta paginación (`offset`, `limit`) y comunica la cantidad total de productos en memoria a través del header HTTP `X-Total-Count`.
  - **R9**: Los errores de dominio (`ProductoInexistente`, `StockInsuficiente`, `ProductoNoHabilitado`) responden bajo un esquema JSON propio y normado (`{"error": {"codigo": ..., "mensaje": ...}}`). También se normó el caso de un PATCH que deja `stock_reservado > stock` (`STOCK_RESERVADO_EXCEDIDO`, 422).
  - **R10**: La operación `PATCH /productos/{id}` discrimina campos no enviados de aquellos enviados explícitamente con valor `null` usando `exclude_unset=True`. Solo `categoria` admite `null`; en los demás campos un `null` explícito se rechaza con 422. El producto resultante se valida antes de guardarse, por lo que un PATCH inválido nunca modifica el catálogo.

* **Capítulo 3 (Ejecución Asincrónica)**:
  - **R11**: En la compra de un producto, la comprobación de habilitación y la comprobación de stock disponible corren concurrentemente usando `asyncio.TaskGroup`.
  - **R12**: La reducción de stock queda protegida bajo un candado asincrónico (`asyncio.Lock()`), impidiendo condiciones de carrera ante múltiples compras simultáneas.
  - **R13**: El envío de confirmación de la compra se despacha en segundo plano haciendo uso de `BackgroundTasks` de FastAPI.
  - **R14**: En `app/comparacion.py` se exponen los endpoints `/comparacion/sincrono` y `/comparacion/asincrono` (ambos con `response_model`), que consultan siempre 3 productos a través del repositorio y demuestran la diferencia de tiempos de respuesta reales entre un flujo secuencial bloqueante y uno concurrente.

---

## 3. Estructura del proyecto

```text
app/
  main.py          # app, lifespan (R4), routers y manejador de errores
  dependencias.py  # get_repo / get_notificador para Depends() (R2)
  modelos.py       # modelos Pydantic (R5, R6, R7, R10)
  errores.py       # errores de dominio y formato normado (R9)
  datos.py         # repositorio en memoria y notificador (R11, R12)
  productos.py     # endpoints /productos (R8, R13)
  comparacion.py   # endpoints /comparacion (R14)
static/index.html  # página de prueba manual de los endpoints
test_concurrencia.py
```

---

## 4. Evidencia de Concurrencia Real (R11 y R12)

Para verificar el correcto comportamiento ante solicitudes concurrentes, se incluye el script de prueba `test_concurrencia.py`, el cual despacha 5 compras simultáneas de 3 unidades sobre el Producto ID 2 (Gaseosa, stock inicial 10, reservado 2, disponible neto: 8 unidades) utilizando `asyncio.gather`.

### Ejecución de la prueba:

Con el servidor corriendo (idealmente recién iniciado, porque el stock se conserva en memoria entre corridas), en otra terminal:

```bash
python test_concurrencia.py
```

Al final el script imprime un bloque de verificación que compara las compras exitosas y el stock final contra lo esperado, e informa `RESULTADO: OK` si no hubo condiciones de carrera.

### Salida obtenida en consola:

```text
=== INICIANDO PRUEBA DE CONCURRENCIA ===
Producto 2 antes: stock=10, reservado=2, disponible neto=8
Simulando 5 compras concurrentes de 3 unidades...
[Cliente 1] Enviando compra de 3 unidades...
[Cliente 2] Enviando compra de 3 unidades...
[Cliente 3] Enviando compra de 3 unidades...
[Cliente 4] Enviando compra de 3 unidades...
[Cliente 5] Enviando compra de 3 unidades...
✅ [Cliente 1] COMPRA EXITOSA - Stock restante: 7
✅ [Cliente 2] COMPRA EXITOSA - Stock restante: 4
❌ [Cliente 3] RECHAZADA (409): {'error': {'codigo': 'STOCK_INSUFICIENTE', 'mensaje': 'Stock insuficiente. Disponible neto: 2, solicitado: 3.'}}
❌ [Cliente 4] RECHAZADA (409): {'error': {'codigo': 'STOCK_INSUFICIENTE', 'mensaje': 'Stock insuficiente. Disponible neto: 2, solicitado: 3.'}}
❌ [Cliente 5] RECHAZADA (409): {'error': {'codigo': 'STOCK_INSUFICIENTE', 'mensaje': 'Stock insuficiente. Disponible neto: 2, solicitado: 3.'}}

=== VERIFICACIÓN ===
Compras exitosas: 2 (esperadas: 2)
Stock final: 4 (esperado: 4)
RESULTADO: OK, sin condiciones de carrera
=== PRUEBA FINALIZADA ===
```

### Conclusiones:
1. **Concurrencia real (R11)**: Las validaciones de cada compra se ejecutaron de manera paralela con `TaskGroup` sin bloquear al servidor.
2. **Consistencia de datos (R12)**: Gracias al candado `asyncio.Lock`, no se produjeron colisiones ni lecturas sucias: el stock pasó de 10 a 7 y luego a 4 de forma atómica.
3. **Manejo de errores normados (R9)**: Al quedar solo 2 unidades disponibles netas, los pedidos restantes fueron rechazados de inmediato con código de estado HTTP 409 y la estructura de error requerida.