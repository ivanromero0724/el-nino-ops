# El Niño - OPS

Repositorio para el monitoreo mensual del fenómeno de El Niño y sus implicaciones para la salud pública en la Región de las Américas.

## Estructura

- `data/base_maestra_elnino.csv`: base longitudinal maestra. Cada fila representa un país/territorio en un SitRep.
- `data/geografia/paises_americas.gpkg`: GeoPackage esperado por el mapa.
- `scripts/mapa_sitrep.py`: genera el mapa de prioridad sanitaria y amenazas/impactos directamente desde la base maestra.
- `outputs/mapas/`: carpeta de salida local para los mapas generados.
- `requirements.txt`: dependencias de Python.

## Base maestra

La base mantiene una sola tabla. Para cada actualización mensual se agregan nuevas filas y se conservan los SitRep anteriores.

La llave temporal es `sitrep_id`; dentro de cada SitRep debe existir una sola fila por `iso3`.

Las variables `icono_agua`, `icono_inundaciones`, `icono_incendios`, `icono_alimentos`, `icono_arbovirosis`, `icono_respiratorio` e `icono_servicios` usan valores 0/1 y alimentan directamente los iconos del mapa.

## Actualización mensual

1. Agregar a `data/base_maestra_elnino.csv` una nueva fila por país/territorio para el nuevo SitRep, sin reemplazar registros anteriores.
2. Incrementar `sitrep_numero`, crear un nuevo `sitrep_id` y actualizar `fecha_publicacion` y `fecha_corte`.
3. Actualizar prioridad, estado de monitoreo, declaratoria, atribución, textos, cifras e indicadores `icono_*`.
4. Ejecutar:

```bash
pip install -r requirements.txt
python scripts/mapa_sitrep.py
```

Por defecto el script toma automáticamente el SitRep con el número más alto y, dentro de este, la fecha de corte más reciente. Para reproducir un corte específico puede fijarse `SITREP_ID` dentro del script.

## Geografía

El script requiere `data/geografia/paises_americas.gpkg`, con los campos `ISO_CC` y `CONTINENT`. La unión con la base se realiza mediante `iso3` ↔ `ISO_CC`.

Para el mapa regional se recomienda una versión recortada a las Américas y simplificada para mantener el repositorio liviano, conservando las partes geográficas necesarias de los países y territorios.
