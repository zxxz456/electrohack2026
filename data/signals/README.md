<!--
README.md
========================


Descripción:
------------
Ficha de fuente del inventario de semáforos del municipio de Puebla:
de dónde sale cada archivo, bajo qué licencia, qué campos trae y cómo
citarlo. El proyecto lo usa para declarar en SUMO los semáforos que
OpenStreetMap no tiene mapeados.


Consideraciones:
------------
- Los archivos son copias sin modificar de la fuente; los SHA-256 de
  abajo permiten verificarlo. Cualquier limpieza se hace en código, no
  editando estos archivos
- Si el portal publica una versión nueva, se agrega como archivo nuevo
  con su año; no se reemplaza la anterior


Metadatos:
----------
* Autor: zxxz6 (Bryan Violante Arriaga)
* Versión: 1.0.0


Historial:
------------
Autor       Fecha           Descripción
zxxz6       26/09/2026      Creación


-->

# Inventario de semáforos de Puebla

Fuente: **Inventario de Semáforos SEMOVINFRA (histórico)**, portal de datos abiertos del Gobierno Municipal de Puebla, levantado por la Secretaría de Movilidad e Infraestructura (SEMOVINFRA).

- Dataset: https://datos.pueblacapital.gob.mx/dataset/inventario-de-sem%C3%A1foros
- Licencia: **Licencia Libre Uso MX**. Permite usar, redistribuir y adaptar los datos citando la fuente.
- Descargado: 26/09/2026

## Archivos

| Archivo | Recurso del portal | Nombre original | Registros | SHA-256 |
|---|---|---|---|---|
| `SignalInventory2021.geojson` | [Inventario de Semáforos (Mapa) 2021](https://datos.pueblacapital.gob.mx/dataset/inventario-de-sem%C3%A1foros/resource/c159c621-78fb-4aac-8433-347bd0eea14d) | `inventario_semaforico_2021.geojson` | 3,283 | `cf3676eca6f223ac...` |
| `SignalInventory2020.csv` | [Inventario de Semáforos (Tabla) Enero 2020](https://datos.pueblacapital.gob.mx/dataset/inventario-de-sem%C3%A1foros/resource/0aae90d6-57cc-43ff-9d6e-3f6a6bf784a9) | `Inventario_semaforos 2020.csv` | 3,054 | `f5e4daf82931e309...` |

El inventario 2021 es la versión principal: es la más reciente, trae colonia y fecha de levantamiento (15/12/2020) y tiene 229 registros más. La tabla 2020 se conserva para comparar qué cambió entre levantamientos.

## Qué representa cada registro

Cada registro es **un poste o soporte de semáforo**, no una intersección. Una intersección típica tiene entre 2 y 14 registros. Para obtener intersecciones hay que agrupar los postes cercanos y emparejarlos con los cruces de la red de SUMO.

El inventario **no incluye planes de tiempos** (ciclo, repartos de verde, desfases). Los programas de tiempo fijo de la simulación se estiman aparte.

## Campos

| Campo 2021 | Campo 2020 | Contenido |
|---|---|---|
| `geometry` | `X`, `Y` | Posición del poste en longitud y latitud (WGS84) |
| `X`, `Y` | — | Posición en UTM zona 14 norte, metros |
| `CALLE_1`, `CALLE_2`, `CALLE_3` | `Calle_1`, `Calle_2`, `Calle_3` | Calles del cruce. Valsequillo aparece con su nombre oficial, Carlos Camacho Espíritu, y Río Papagayo como 24 Sur |
| `TIPO` | `Tipo` | Soporte: pedestal, látigo, doble látigo, P-300, MG-10, destellador... |
| `CONTROL` | `Control` | Modelo del controlador (C-26, C-208, C-216, C-3000...) |
| `CAB_VEHICU` | `Cab_Vehicu` | Cabezas vehiculares en el poste |
| `CAB_PEATON` | `Cab_Peaton` | Cabezas peatonales en el poste. Distinto de cero indica fase peatonal |
| `CAB_REPETI` | `Cab_Repeti` | Cabezas repetidoras |
| `CUADRANTES` | `Cuadrantes` | Cuadrante de la ciudad |
| `COLONIA` | — | Colonia |
| `FECHA` | — | Fecha de levantamiento |

## Cómo citarlo

> Gobierno Municipal de Puebla, Secretaría de Movilidad e Infraestructura. *Inventario de Semáforos SEMOVINFRA (histórico)*, versión 2021. Portal de Datos Abiertos de Puebla Capital. https://datos.pueblacapital.gob.mx/dataset/inventario-de-sem%C3%A1foros. Licencia Libre Uso MX. Consultado el 26/09/2026.

<!--
################################ FIN DE README.MD ##############################
################################################################################
-->
