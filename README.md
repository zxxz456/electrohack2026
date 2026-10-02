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

Las opciones de construcción están en `networks/puebla/Corridor.netccfg`: semáforos de tiempo fijo, banquetas y cruces peatonales.

### Semáforos

OpenStreetMap solo trae 8 semáforos en esta zona. Los demás salen del [inventario de semáforos del municipio](data/signals/). `scripts/MatchSignals.py` agrupa los postes del inventario por intersección, empareja cada una con el cruce de SUMO más cercano (a menos de 30 m) y escribe `networks/puebla/Signals.csv`. `BuildNetwork.sh` lee ese archivo y declara en `netconvert` los que OSM no tiene.

| | Intersecciones |
|---|---|
| Del inventario dentro del área elegida | 36 |
| Del inventario fuera del área, en tramos que la red conserva y con cruce completo | 1 (22 Sur x Juan Pablo II) |
| Ya tenían semáforo en OSM | 5 |
| Agregadas desde el inventario | 32 |
| **Semáforos en la red** (incluye 3 de OSM que no están en el inventario) | **40** |

La red se extiende un poco más allá del área elegida porque `netconvert` conserva completas las calles que cruzan el borde. En esos tramos solo se agregan semáforos en cruces a los que llegan autos por al menos dos calles: en la orilla la calle transversal suele quedar fuera de la descarga, y un semáforo sin tráfico con qué cruzarse solo agregaría demora artificial. Por eso quedan fuera 6 intersecciones del inventario en la orilla.

`BuildNetwork.sh` termina verificando que la red tenga todos los semáforos de `Signals.csv`, y se detiene con error si falta alguno. Los IDs de los cruces dependen de la versión de `netconvert`, por eso SUMO está fijo en 1.27.1 en `pyproject.toml`; con otra versión la verificación falla en lugar de perder semáforos sin avisar.

`Signals.csv` está versionado, así que no hace falta regenerarlo. Solo se vuelve a correr si cambia el inventario o el extracto de OSM:

```bash
python scripts/MatchSignals.py
scripts/BuildNetwork.sh
```

Otros cambios a la red (semáforos que no estén en el inventario, vueltas prohibidas, cruces) se declaran en `Corridor.netccfg` o en archivos de parche dentro de `networks/puebla/`, nunca editando `generated/` con netedit, porque la siguiente construcción los borra.

## Estructura del repositorio

```
networks/        entradas de SUMO por corredor; generated/ se reconstruye
configs/         escenarios y experimentos en YAML (aquí vive la ablación)
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
report/          reporte y diapositivas del concurso
```

## Documentación

- [docs/HeaderTemplate.md](docs/HeaderTemplate.md): el encabezado y el banner final que lleva cada archivo.

## Cómo contribuir

Todo se escribe en español: documentación, comentarios, docstrings y mensajes de commit. Los identificadores del código y los nombres de archivo van en inglés. Cada archivo lleva un encabezado con una pila de Historial (username de 5 letras) y cierra con un banner de 80 columnas. Las líneas de código miden como máximo 80 columnas

Pruebas: `pytest`. Lint: `ruff check src tests`.

<!--
################################ FIN DE README.MD ##############################
################################################################################
-->
