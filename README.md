# El Niño - OPS

Repositorio para el monitoreo mensual del fenómeno de El Niño y sus implicaciones para la salud pública en la Región de las Américas.

## Estructura

- `app.py`: punto de entrada de Streamlit y mapa regional interactivo en Folium.
- `dashboard.py`: interfaz, filtros, indicadores, gráficos y detalle por país.
- `data/base_maestra_elnino.csv`: base longitudinal maestra; una fila por país y SitRep.
- `data/geografia/paises_americas.gpkg`: geografía regional usada por el tablero y el mapa estático.
- `scripts/preparar_geografia.py`: reconstruye el GeoPackage a partir de Natural Earth 1:50m.
- `scripts/mapa_sitrep.py`: genera el mapa SitRep en PDF y PNG, en español e inglés.
- `assets/ops_oms.png`: logo OPS/OMS utilizado por el mapa estático en español.
- `assets/PAHO_eng.png`: logo PAHO/WHO en inglés usado por los mapas PDF y PNG en inglés (imagen institucional publicada en UN Road Safety Fund).
- `outputs/mapas/`: productos estáticos generados.
- `.github/workflows/validar_dashboard.yml`: única validación automática del tablero.
- `.github/workflows/generar_mapa.yml`: genera y versiona los productos estáticos.
- `.streamlit/config.toml`: configuración visual de Streamlit.
- `requirements.txt`: dependencias de Python.

## Base maestra

La base mantiene una sola tabla. Para cada actualización mensual se agregan nuevas filas y se conservan los SitRep anteriores. La llave temporal es `sitrep_id`; dentro de cada SitRep debe existir una sola fila por `iso3`.

Las variables `icono_agua`, `icono_inundaciones`, `icono_incendios`, `icono_alimentos`, `icono_arbovirosis`, `icono_respiratorio`, `icono_servicios` e `icono_servicios_potencial` usan valores 0/1 y alimentan los pictogramas del mapa y las visualizaciones del tablero.

**Regla de servicios de salud (SitRep 2 y posteriores):** cualquier marca en la columna de **Afectación o presión observada** de la Tabla 1 (●, ▲ u otra) activa `icono_servicios`; cualquier marca en **Impacto potencial**, incluida ◇ de preparación, activa `icono_servicios_potencial`. La base conserva **ambas** marcas; solo al dibujar los mapas interactivo y estático se da prioridad al pictograma de **afectación** cuando ambas están marcadas. Si ninguna columna tiene marca, no se dibuja ningún pictograma de servicios.

En SitRep 3, los campos `tabla1_orden`, `tabla1_pais`, `tabla1_declaratoria`, `tabla1_otras_afectaciones`, `tabla1_servicios_observado` y `tabla1_servicios_potencial` transcriben la Tabla 1 del borrador Word sin deducciones a partir de los resúmenes narrativos. Los campos `simbolo_*` conservan las marcas de amenazas y efectos sanitarios. La sección *Síntesis regional* muestra por defecto la vista completa y mantiene el orden de países y subregiones del documento, agrupando Canadá y Estados Unidos en una fila cuando ambos están incluidos. Los SitRep anteriores no se modifican.

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

El workflow **Generar mapa SitRep** genera automáticamente cuatro productos del corte vigente (PNG y PDF en español e inglés), los valida y los guarda en `outputs/mapas/`.
Los archivos en español conservan los nombres históricos; los de inglés añaden `_EN` al final del nombre (por ejemplo, `..._2026-10-16_EN.png` y `..._2026-10-16_EN.pdf`).
El workflow **Validar dashboard** revisa sintaxis, mapa, filtros, reruns y la versión desplegada.

Para generar ambos idiomas localmente:

```bash
python scripts/mapa_sitrep.py --lang es
python scripts/mapa_sitrep.py --lang en
```

## Geografía

La geografía regional proviene de Natural Earth Admin 0 Countries, escala 1:50m, en EPSG:4326. La unión con la base se realiza mediante `iso3` ↔ `ISO_CC`. El GeoPackage se reconstruye con `python scripts/preparar_geografia.py` solo cuando sea necesario actualizar la geografía; el workflow mensual usa el archivo ya versionado.
