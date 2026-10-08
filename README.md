<!--
README.md
========================


Descripción:
------------
Punto de entrada para quien abre el repositorio: qué es el proyecto,
cómo se instala, cómo está organizado el código y dónde viven las
reglas y el diseño.


Consideraciones:
------------
- Mantenerlo corto; el razonamiento de diseño va en PLAN.md y las reglas
  en CLAUDE.md
- Actualizar la tabla de Avance conforme se cierra cada paso
- Los comandos listados aquí deben funcionar; no documentar CLIs que
  todavía no existen


Metadatos:
----------
* Autor: zxxz6 (Bryan Violante Arriaga)
* Versión: 1.0.0


Historial:
------------
Autor       Fecha           Descripción
zxxz6       08/10/2026      Zona de estudio, demanda y 45 semáforos
zxxz6       05/10/2026      Correcciones de campo y semáforos conjuntos
zxxz6       01/10/2026      Cuatro controladores, sin max-pressure ni Jev
zxxz6       01/10/2026      Sin implementación física: solo simulación
zxxz6       26/09/2026      Cruces fuera del área y tabla de semáforos
zxxz6       26/09/2026      Semáforos del inventario municipal
zxxz6       26/09/2026      Sección de la red vial de CU BUAP
zxxz6       25/09/2026      Instalación con PyTorch CUDA 12.8 para usar la GPU
zxxz6       25/09/2026      Creación


-->

# Proyecto para ElectroHack2026

Integrantes:
- Dr. Saul Pomares Hernandez
- Sarah
- Bryan Violante
- Helen Alondra Pillado Hernández

Simulación de un corredor con intersecciones semaforizadas (Puebla, Mexico), donde cada semáforo es controlado por un agente de RL. El proyecto es solo de simulación. Los agentes comparten unos pocos bytes de estado con sus vecinos inmediatos (cola, fase activa, tiempo en la fase y siguiente fase prevista) en un mensaje mínimo, y la coordinación del corredor emerge de esa anticipación local, sin controlador central.

El sistema optimiza tres cosas a la vez: flujo vehicular, energía y emisiones del corredor, y tiempo de cruce peatonal.

Este proyecto no propone un algoritmo nuevo, pero se combinan diferentes aspectos de otros trabajos:

- **Comunicación mínima.** Un mensaje de 5 bytes por vecino en cada paso de decisión, en lugar de embeddings aprendidos.
- **Energía y emisiones como objetivos de primera clase**, a partir de los modelos HBEFA y de vehículo eléctrico de SUMO.
- **Peatones en la recompensa**, con límites de seguridad aplicados fuera del agente.

## Controladores comparados
Cuando cambia de fase cada semaforo? Son las distintas formas de medir cuanto mejora cada enfoque

| # | Controlador | Propósito |
|---|---|---|
| 1 | Tiempo fijo | Línea base: cómo operan hoy los semáforos |
| 2 | DQN, solo observación local | Aísla cuánto aporta la coordinación |
| 3 | DQN con vecinos directos | Mensaje crudo de los vecinos inmediatos |
| 4 | DQN con onda causal difusa | Controlador principal: estado de varios saltos ponderado por su fuerza de onda |


## Instalación

Requiere Linux y Python 3.10 o superior. El entrenamiento usa GPU NVIDIA con CUDA; sin GPU corre en CPU, más lento. SUMO viene como wheel de pip, así que no hace falta ningún paquete del sistema.

```bash
cd electrohack26/

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

# PyTorch con CUDA 12.8 primero. Es el mínimo para GPUs Blackwell
# (RTX 50xx, sm_120); con un wheel anterior torch ve la GPU pero falla
pip install torch --index-url https://download.pytorch.org/whl/cu128

# El proyecto, SUMO, sumo-rl, Stable-Baselines3 y herramientas de desarrollo
pip install -e ".[dev]"

# sumo-rl no importa sin SUMO_HOME
echo 'export SUMO_HOME="$(python -c "import sumo; print(sumo.SUMO_HOME)")"' \
    >> .venv/bin/activate
deactivate && source .venv/bin/activate
```

Verificación:

```bash
sumo --version
python -c "import sumo_rl, stable_baselines3; print('ok')"

# Debe imprimir True, el nombre de la GPU y (12, 0) en una RTX 50xx
python -c "import torch; print(torch.cuda.is_available(), \
    torch.cuda.get_device_name(0), torch.cuda.get_device_capability(0)); \
    print((torch.ones(2, device='cuda') * 2).sum().item())"
```

Si `sumo-gui` falla por librerías gráficas faltantes, instala SUMO desde `ppa:sumo/stable` y apunta `SUMO_HOME` a `/usr/share/sumo`. Para entrenar no se necesita la interfaz gráfica.

## Red vial

La simulación usa la zona alrededor de CU BUAP. El extracto de OpenStreetMap está congelado en `networks/puebla/Corridor.osm.xml.gz`, así todos trabajan sobre el mismo mapa aunque OSM cambie. La red de SUMO no se versiona: se construye a partir de ese extracto con un comando.

```bash
source .venv/bin/activate
scripts/BuildNetwork.sh
sumo-gui -c networks/puebla/Corridor.sumocfg
```

Hay que volver a correr `BuildNetwork.sh` después de cada pull que traiga cambios en `networks/`. El mismo script recorta la [zona de estudio](#zona-de-estudio-y-demanda) de San Claudio.

La construcción tiene dos pasadas. La primera convierte el extracto de OSM con las opciones de `networks/puebla/Corridor.netccfg` (semáforos de tiempo fijo, banquetas y cruces peatonales) y agrega los semáforos del inventario municipal. La segunda aplica sobre esa red las [correcciones de campo](#correcciones-de-campo).

netconvert adivina las banquetas según la velocidad del tramo. Con su límite por defecto (50 km/h), Valsequillo y San Claudio quedaban sin banqueta, y por lo tanto sin cruces peatonales: solo 20 de 45 nodos con semáforo tenían cruce. El límite está subido a 30 m/s para que todo cruce semaforizado tenga paso peatonal, como en la calle.

Hay otras tres cosas que netconvert hace por defecto y que aquí se apagaron porque trababan la simulación: vueltas en U en casi cualquier cruce, cruces de "cede a la derecha" (San Claudio le cedía el paso a cada calle lateral) y la unión de los cuatro semáforos de 14 Sur y Circunvalación en un solo programa con ciclo de 222 s. El porqué de cada una está en el encabezado de `Corridor.netccfg`.

### Semáforos

OpenStreetMap solo trae 8 semáforos en esta zona. Los demás salen del [inventario de semáforos del municipio](data/signals/). `scripts/MatchSignals.py` agrupa los postes del inventario por intersección, empareja cada una con el cruce de SUMO más cercano (a menos de 30 m) y escribe `networks/puebla/Signals.csv`. `BuildNetwork.sh` lee ese archivo y declara en `netconvert` los que OSM no tiene.

| | Intersecciones |
|---|---|
| Del inventario dentro del área elegida | 36 |
| Del inventario fuera del área, en tramos que la red conserva y con cruce completo | 1 (22 Sur x Juan Pablo II) |
| Ya tenían semáforo en OSM | 5 |
| Agregadas desde el inventario | 32 |
| Semáforos de OSM y del inventario (incluye 3 de OSM que no están en el inventario) | 40 |
| Agregados por observación en campo (`ManualSignals.csv`) | 4 |
| Unidos en un semáforo conjunto (Facultad de Derecho: 3 de OSM en 1) | -2 |
| Separados (14 Sur y Circunvalación: 1 de netconvert en 4) | +3 |
| **Semáforos en la red** | **45** |

Un semáforo conjunto controla varios nodos con un solo programa. En 24 Sur y San Claudio el inventario ubica el semáforo en un nodo que solo controla el sentido norte; ese nodo y el cruce principal forman `san_claudio_24_sur`, así que el conteo no cambia. En Facultad de Derecho, OSM pone un semáforo en cada una de las tres calzadas; en la red operan como uno, `san_claudio_derecho`.

La red se extiende un poco más allá del área elegida porque `netconvert` conserva completas las calles que cruzan el borde. En esos tramos solo se agregan semáforos en cruces a los que llegan autos por al menos dos calles: en la orilla la calle transversal suele quedar fuera de la descarga, y un semáforo sin tráfico con qué cruzarse solo agregaría demora artificial. Por eso quedan fuera 6 intersecciones del inventario en la orilla.

`BuildNetwork.sh` termina verificando que la red tenga todos los semáforos de `Signals.csv` y de `ManualSignals.csv`, y se detiene con error si falta alguno. Los IDs de los cruces dependen de la versión de `netconvert`, por eso SUMO está fijo en 1.27.1 en `pyproject.toml`; con otra versión la verificación falla en lugar de perder semáforos sin avisar.

`Signals.csv` está versionado, así que no hace falta regenerarlo. Solo se vuelve a correr si cambia el inventario o el extracto de OSM:

```bash
python scripts/MatchSignals.py
scripts/BuildNetwork.sh
```

### Correcciones de campo

OSM y el inventario de 2021 no coinciden del todo con la calle. Lo que se observa en campo se declara en archivos de parche dentro de `networks/puebla/`, que `BuildNetwork.sh` aplica en la segunda pasada. Nunca se edita `generated/` con netedit, porque la siguiente construcción borra esos cambios. El encabezado de cada archivo explica por qué existe cada corrección.

| Corrección | Dónde se declara |
|---|---|
| Semáforo que falta | `ManualSignals.csv`, una fila por nodo |
| Varios nodos que operan como un solo semáforo | `ManualSignals.csv`, el mismo valor en la columna `tl_id` |
| Cruce peatonal que falta | `ManualCrossings.con.xml`, con el nodo y los tramos que atraviesa |
| Nodo o tramo que OSM no tiene, p. ej. un andador en el camellón | `ManualEdges.edg.xml` |
| Tramo o unión de nodos que OSM trae mal | `Corridor.netccfg`, con `remove-edges.explicit` y `junctions.join-exclude` |

Para agregar un semáforo:

1. Ubica la intersección en `sumo-gui`. Al dar clic derecho sobre el nodo, el menú muestra su ID (`junction:<id>`). La esquina inferior derecha muestra las coordenadas de la red bajo el cursor.
2. Agrega una fila a `networks/puebla/ManualSignals.csv` con `node_id`, `tl_id` (vacío si el semáforo opera solo), el nombre del cruce y una nota de dónde salió el dato.
3. Si el cruce peatonal no aparece, decláralo en `ManualCrossings.con.xml`. En la segunda pasada netconvert ya no adivina cruces.
4. Corre `scripts/BuildNetwork.sh`. La verificación final confirma que el semáforo quedó en la red.

Un nodo creado con un corte (`split`) en `ManualEdges.edg.xml` no puede formar parte de un semáforo conjunto, porque netconvert lee los nodos antes que los tramos.

## Zona de estudio y demanda

Los agentes controlan por ahora los 6 semáforos de San Claudio, de 14 Sur a 24 Sur ([configs/corridors/SanClaudio.yaml](configs/corridors/SanClaudio.yaml)). El resto sigue con tiempo fijo.

Los experimentos no corren sobre toda la red sino sobre un recorte de 170 m alrededor del corredor. En la red completa, el tráfico que sale de San Claudio hacia Circunvalación satura esos cruces y la cola regresa hasta el corredor; sin aforos no hay forma de calibrar eso, y ensuciaba cualquier comparación. El recorte lo hace `BuildNetwork.sh` y verifica que los 6 semáforos queden idénticos a los de la red completa.

La demanda sale de un YAML por escenario en `configs/scenarios/` (hora pico y flujo asimétrico) y se genera con semilla fija:

```bash
python scripts/GenerateDemand.py
D=networks/puebla/generated/demand/PeakHour/seed_1000
sumo-gui -c networks/puebla/Corridor.sumocfg \
    -n networks/puebla/generated/areas/SanClaudio.net.xml.gz \
    -r $D/Background.rou.xml,$D/Corridor.rou.xml,$D/Pedestrians.rou.xml
```

Cada escenario fija cuántos autos por hora entran a cada acceso del corredor, y `routeSampler` (de SUMO) elige rutas reales que cumplan esos conteos. Las tasas son supuestas: 100 autos por hora por carril en San Claudio, que es lo más que aguanta el tiempo fijo sin trabarse. Es poco para la avenida real; el modelo pierde capacidad en 18 Sur y 22 Sur, donde las vueltas a la izquierda esperan hueco en el mismo carril que los que siguen derecho. Si conseguimos aforos, van en la sección `measured` del escenario y reemplazan lo supuesto.

## Estructura del repositorio

```
networks/        entradas de SUMO por corredor; generated/ se reconstruye
configs/         corredores, escenarios y experimentos en YAML
src/corridor/
  common/        límites de tiempos, unidades, topes de normalización, semillas
  network/       importación de OSM, netconvert, generación de demanda
  link/          mensaje entre vecinos: esquema, cuantización, pérdida
  env/           entorno Gymnasium: observación, máscara de acciones, recompensa
  controllers/   tiempo fijo y variantes de DQN
  training/      entrenamiento DQN independiente por intersección
  evaluation/    ejecución de escenarios, métricas, energía, figuras
scripts/         puntos de entrada de línea de comandos, sin lógica
tests/           pytest, con la misma estructura que src/corridor/
data/            entradas crudas: extracto OSM, inventario de semáforos
results/         corridas, modelos, logs, figuras (no versionado)
report/          reporte y presentaciones
```

## Documentación

- [docs/HeaderTemplate.md](docs/HeaderTemplate.md): el encabezado y el banner final que lleva cada archivo.

## Cómo contribuir

Todo se escribe en español: documentación, comentarios, docstrings y mensajes de commit. Los identificadores del código y los nombres de archivo van en inglés. Cada archivo lleva un encabezado con una pila de Historial (username de 5 letras) y cierra con un banner de 80 columnas. Las líneas de código miden como máximo 80 columnas.

Pruebas: `pytest`. Lint: `ruff check src tests scripts`.

<!--
################################ FIN DE README.MD ##############################
################################################################################
-->
