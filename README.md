# El Niño - OPS

Repositorio para el monitoreo mensual del fenómeno de El Niño y sus implicaciones para la salud pública en la Región de las Américas.

## Estructura

- `app.py`: punto de entrada de Streamlit y mapa regional interactivo en Folium.
- `dashboard.py`: interfaz, filtros, indicadores, gráficos y detalle por país.
- `data/base_maestra_elnino.csv`: base longitudinal maestra; una fila por país y SitRep.
- `data/geografia/paises_americas.gpkg`: geografía regional usada por el tablero y el mapa estático.
- `scripts/preparar_geografia.py`: reconstruye el GeoPackage a partir de Natural Earth 1:50m.
- `scripts/mapa_sitrep.py`: genera el PNG y PDF canónicos del mapa SitRep.
- `assets/ops_oms.png`: logo institucional usado por los productos.
- `outputs/mapas/`: productos estáticos generados.
- `.github/workflows/validar_dashboard.yml`: única validación automática del tablero.
- `.github/workflows/generar_mapa.yml`: genera y versiona los productos estáticos.
- `.streamlit/config.toml`: configuración visual de Streamlit.
- `requirements.txt`: dependencias de Python.

## Base maestra

La base mantiene una sola tabla. Para cada actualización mensual se agregan nuevas filas y se conservan los SitRep anteriores. La llave temporal es `sitrep_id`; dentro de cada SitRep debe existir una sola fila por `iso3`.

Las variables `icono_agua`, `icono_inundaciones`, `icono_incendios`, `icono_alimentos`, `icono_arbovirosis`, `icono_respiratorio` e `icono_servicios` usan valores 0/1 y alimentan directamente los pictogramas del mapa y las visualizaciones del tablero.

## Dashboard

El tablero se alimenta directamente de la base maestra y del GeoPackage. No requiere archivos intermedios ni scripts de parcheo.

Para ejecutarlo localmente:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Para Streamlit Community Cloud, usar la rama `main` y `app.py` como archivo principal.

## Actualización mensual

1. Agregar las filas del nuevo SitRep a `data/base_maestra_elnino.csv`.
2. Actualizar `sitrep_numero`, `sitrep_id`, fechas, prioridad, declaratoria, atribución, textos, cifras e indicadores `icono_*`.
3. Hacer commit y push.

El workflow **Generar mapa SitRep** crea el PNG y PDF del corte vigente. El workflow **Validar dashboard** revisa sintaxis, mapa, filtros, reruns y la versión desplegada.

## Geografía

La geografía regional proviene de Natural Earth Admin 0 Countries, escala 1:50m, en EPSG:4326. La unión con la base se realiza mediante `iso3` ↔ `ISO_CC`.
