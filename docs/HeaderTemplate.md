<!--
HeaderTemplate.md
========================


Descripción:
------------
Plantillas canónicas de encabezado y de banner de fin de archivo para
cada formato del proyecto, agrupadas por sintaxis de comentario. Copia
el bloque de la familia que corresponde al archivo, llena Descripción y
Consideraciones, deja Metadatos sin tocar y empieza el Historial con
Creación.


Consideraciones:
------------
- Agrupadas por familia de comentario, no por extensión: un formato
  nuevo casi siempre es una fila más en la tabla de cobertura, no una
  plantilla nueva
- La lista de formatos que no pueden llevar encabezado es deliberada
- Los anchos de banner son exactos: cada línea mide 80 columnas
- Sin secciones License ni Warning; el hook rechaza los encabezados que
  las traigan, igual que las etiquetas en inglés


Metadatos:
----------
* Autor: zxxz6 (Bryan Violante Arriaga)
* Versión: 1.1.0


Historial:
------------
Autor       Fecha           Descripción
zxxz6       25/09/2026      Traducido al español, banner FIN DE
zxxz6       25/09/2026      Eliminadas las secciones License y Warning
zxxz6       25/09/2026      Creación, adaptado de la plantilla del proyecto


-->

# Plantillas de encabezado y banner

Todo archivo abre con un encabezado y cierra con un banner de fin de archivo. Las reglas de mantenimiento están en [`../CLAUDE.md`](../CLAUDE.md) §4, §5 y §6, y las hace cumplir [`../.claude/hooks/CheckFileHeader.py`](../.claude/hooks/CheckFileHeader.py).

Ambos son idénticos en todos los formatos; solo cambia la sintaxis del comentario. Elige abajo la familia que corresponde al archivo.

---

## Cobertura

| Familia | Aplica a | Plantilla |
|---|---|---|
| Docstring de Python | `.py` | [ver](#1--python) |
| Comentario hash | `.yml` `.yaml` `.toml` `.sh` `.gitignore` `Makefile` `Dockerfile` | [ver](#2--comentario-hash) |
| Comentario de markup | `.md` `.html` `.xml` y entradas de SUMO: `.sumocfg` `.netccfg` `.rou.xml` `.add.xml` | [ver](#3--comentario-de-markup) |

Banners de fin de archivo para todas las familias: [ver](#4--banner-de-fin-de-archivo).

**Archivos generados por frameworks, conservan su nombre y están exentos:** `__init__.py`, `conftest.py`, `setup.py`.

**Archivos que generan las herramientas de SUMO, exentos:** `*.net.xml` y `*.poly.xml` (los reescriben `netconvert` y `polyconvert` en cada reconstrucción) y todo lo que esté bajo `generated/`, `data/` o `results/`. Un encabezado puesto a mano ahí se perdería en la siguiente corrida.

**Formatos que no pueden llevar encabezado**, porque no tienen sintaxis de comentario: `.json`, `.csv`, `.ipynb`, extractos `.osm`, binarios (`.png`, `.pdf`, `.zip`, modelos entrenados).

---

## 1 · Python

```python
"""
FileName.py
========================


Descripción:
------------
Qué hace este módulo y por qué existe. Dos o tres líneas.
Si el módulo conecta dos sistemas (SUMO y Gymnasium, por ejemplo),
dilo explícitamente.


Consideraciones:
------------
- Mantener juntos los métodos relacionados (con comentarios de sección)
- Usar nombres claros y consistentes
- Notas sobre patrones internos u orden de los métodos


Metadatos:
----------
* Autor: zxxz6 (Bryan Violante Arriaga)
* Versión: 1.0.0


Historial:
------------
Autor       Fecha           Descripción
zxxz6       25/09/2026      Creación


"""
```

Si el archivo tiene shebang, este se queda en la línea 1 y el docstring va después.

---

## 2 · Comentario hash

Cubre **YAML** (`.yml`, `.yaml`), **TOML** (`.toml`), **scripts de shell** (`.sh`), **`.gitignore`**, **Makefile** y **Dockerfile**.

```yaml
# PeakHour.yaml
# ========================
#
#
# Descripción:
# ------------
# Qué define esta configuración y por qué existe.
#
#
# Consideraciones:
# ------------
# - Qué corridas la consumen y con qué debe mantenerse sincronizada
#
#
# Metadatos:
# ----------
# * Autor: zxxz6 (Bryan Violante Arriaga)
# * Versión: 1.0.0
#
#
# Historial:
# ------------
# Autor       Fecha           Descripción
# zxxz6       25/09/2026      Creación
#

scenario: peak_hour
```

En **scripts de shell** el shebang se queda en la línea 1 y el encabezado va después:

```bash
#!/usr/bin/env bash
#
# RunBaselines.sh
# ========================
#
# ... mismas secciones ...
#
```

---

## 3 · Comentario de markup

Cubre **Markdown** (`.md`), **HTML** (`.html`) y todo **XML** escrito a mano, que en este proyecto son las entradas de SUMO: `.sumocfg`, `.netccfg`, archivos de rutas (`.rou.xml`) y archivos adicionales (`.add.xml`: detectores, cruces peatonales, programas de semáforo). El comentario no se renderiza y SUMO lo ignora.

```markdown
<!--
FileName.md
========================


Descripción:
------------
Qué cubre este documento y para quién es.


Consideraciones:
------------
- Cómo se mantiene el documento o con qué debe estar sincronizado


Metadatos:
----------
* Autor: zxxz6 (Bryan Violante Arriaga)
* Versión: 1.0.0


Historial:
------------
Autor       Fecha           Descripción
zxxz6       25/09/2026      Creación


-->

# Título del documento
```

En **XML**, la declaración `<?xml ... ?>` se queda en la línea 1 y el comentario va después. El banner va tras el cierre del elemento raíz:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!--
Corridor.sumocfg
========================

... mismas secciones ...

-->
<configuration>
    <input>
        <net-file value="generated/Corridor.net.xml"/>
    </input>
</configuration>
<!--
########################### FIN DE CORRIDOR.SUMOCFG ############################
################################################################################
-->
```

En XML de SUMO las listas de atributos también se cortan a 80 columnas: un atributo por línea, con sangría bajo el elemento.

---

## 4 · Banner de fin de archivo

Todo archivo cierra con dos líneas: un título que nombra el archivo en mayúsculas y una línea de relleno sólido. **Ambas miden exactamente 80 columnas** y se rellenan con `#`.

El título va centrado: ` FIN DE <ARCHIVO> ` con `#` a ambos lados hasta llegar a 80 columnas.

**Python, YAML, TOML, shell, `.gitignore`, Makefile, Dockerfile**: el carácter de relleno ya es el marcador de comentario, así que la línea es sólida:

```python
############################ FIN DE CORRIDORENV.PY #############################
################################################################################
```

**Markdown, HTML, XML y entradas de SUMO**: las dos líneas van dentro de un bloque de comentario para que no se rendericen:

```markdown
<!--
################################ FIN DE PLAN.MD ################################
################################################################################
-->
```

### Cómo generarlo

Contar `#` a mano es la forma segura de terminar con 79 u 81 columnas. Mejor generarlo:

```python
W, name = 80, "CorridorEnv.py"
text = f" FIN DE {name.upper()} "
left = (W - len(text)) // 2
print("#" * left + text + "#" * (W - len(text) - left))
print("#" * W)
```

---

## Presupuesto de columnas

Toda línea mide como máximo **80 columnas**, contando sangría y comentarios. Ver [`../CLAUDE.md`](../CLAUDE.md) §7. La prosa y las tablas de Markdown son la única excepción; este mismo archivo pasa de 80 en sus tablas a propósito.

---

## Ejemplo de historial acumulado

La entrada nueva siempre va **arriba**, como en una pila. Las entradas anteriores no se reescriben.

```
Historial:
------------
Autor       Fecha           Descripción
zxxz6       03/10/2026      Agregado el bit de enlace activo al bloque de vecinos
zxxz6       28/09/2026      Cola normalizada por capacidad del carril
zxxz6       25/09/2026      Creación
```

<!--
############################ FIN DE HEADERTEMPLATE.MD ##########################
################################################################################
-->
