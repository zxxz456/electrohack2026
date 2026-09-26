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
zxxz6       25/09/2026      Instalación con PyTorch CUDA 12.8 para usar la GPU
zxxz6       25/09/2026      Creación


-->

# Proyecto para ElectroHack2026

Integrantes:
- Dr. Saul Pomares Hernandez
- Sarah
- Bryan Violante

Simulación de un corredor con intersecciones semaforizadas (Puebla, Mexico), donde cada semáforo es controlado por un agente de RL (en principio es solo simulacion pero se plantea que sean solares). Los agentes comparten unos pocos bytes de estado con sus vecinos inmediatos (cola, fase activa, tiempo en la fase y siguiente fase prevista) en un mensaje del tamaño de LoRa, y la coordinación del corredor emerge de esa anticipación local, sin controlador central.

El sistema optimiza tres cosas a la vez: flujo vehicular, energía y emisiones del corredor, y tiempo de cruce peatonal.

Este proyecto no propone un algoritmo nuevo, pero se combinan diferentes aspectos de otros trabajos:

- **Comunicación mínima.** Un mensaje de 5 bytes por vecino en cada paso de decisión, en lugar de embeddings aprendidos. Cabe en un radio SX1276 con consumo despreciable.
- **Energía y emisiones como objetivos de primera clase**, a partir de los modelos HBEFA y de vehículo eléctrico de SUMO.
- **Peatones en la recompensa**, con límites de seguridad aplicados fuera del agente.

## Controladores comparados
Cuando cambia de fase cada semaforo? Son las distintas formas de medir cuanto mejora cada enfoque

| # | Controlador | Propósito |
|---|---|---|
| 1 | Tiempo fijo | Línea base: cómo operan hoy los semáforos |
| 2 | Max-pressure | Regla sin aprendizaje con garantías de estabilidad; plan B |
| 3 | DQN, solo observación local | Aísla cuánto aporta la coordinación |
| 4 | DQN con estado de vecinos | Controlador principal |
| 5 | Jev (TypeSafe AI) | Opcional, sujeto a acceso a la API |


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

## Estructura del repositorio

```
networks/        entradas de SUMO por corredor; generated/ se reconstruye
configs/         escenarios y experimentos en YAML (aquí vive la ablación)
src/corridor/
  common/        límites de tiempos, unidades, topes de normalización, semillas
  network/       importación de OSM, netconvert, generación de demanda
  link/          mensaje entre vecinos: esquema, cuantización, pérdida
  env/           entorno Gymnasium: observación, máscara de acciones, recompensa
  controllers/   tiempo fijo, max-pressure, DQN, Jev
  training/      entrenamiento DQN independiente por intersección
  evaluation/    ejecución de escenarios, métricas, energía, figuras
  solar/         irradiancia, dimensionamiento del nodo, costeo
scripts/         puntos de entrada de línea de comandos, sin lógica
tests/           pytest, con la misma estructura que src/corridor/
data/            entradas crudas: extracto OSM, PVGIS, cotizaciones
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
