# SRECA — Sistema Rural de Energía Comunitaria Asturiana

Cerebro software de una **Comunidad Energética Local** en la Asturias rural (piloto Teverga):
autoconsumo colectivo FV 15 kWp gestionado por analítica predictiva. Optimiza el reparto de la
energía solar entre vecinos y desplaza cargas flexibles a las horas de sol — sin baterías
("batería virtual" = gestión del momento de consumo).

**Stack coste-licencia 0 €:** Python + Streamlit + Open-Meteo (API gratuita) + SQLite.

## Estado

MVP funcional, presentable. Slice vertical completo extremo a extremo (PVGIS → forecast →
optimizador → SQLite → dashboard), 65 tests, dashboard verificado headless. Datos de consumo
sintéticos (ilustrativos) hasta disponer de curvas reales de los vecinos. Despliegue público
(Streamlit Cloud) pendiente de subir el repositorio a GitHub.

## Cómo funciona (MVP)

```
Open-Meteo → forecast FV (modelo físico) + forecast demanda (perfiles sintéticos)
          → optimizador (coeficientes ex-ante + recomendación desplazamiento de carga)
          → SQLite → dashboard Streamlit (producción · coeficientes · ahorro €/hogar)
```

Dos salidas legales distintas (norma vigente 2026):
- **Perfil ex-ante anual** de coeficientes de reparto (revisable ≥4 meses, Orden TED/1247/2021).
- **Recomendación de desplazamiento** de cargas flexibles de granja → ventana solar (siempre legal).

## Estructura

```
config/concejos/   # parámetros por concejo (teverga.yaml). Replicar = añadir YAML
sreca/ingest/      # cliente Open-Meteo
sreca/forecast/    # producción FV (físico) + demanda (sintética)
sreca/optimize/    # coeficientes + schedule ex-ante + load-shift + savings
sreca/store/       # SQLite
sreca/dashboard/   # Streamlit
tests/             # TDD
docs/              # spec de diseño + verificación legal 2026
```

## Docs

- Spec de diseño: `docs/2026-06-19-sreca-mvp-design.md`
- Verificación legal 2026: `docs/2026-06-19-legal-verification-2026.md`
- Memoria de beca (fuente, no duplicada): `~/.claude/plans/estoy-pensando-en-ideas-stateful-cascade.md`

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # solo runtime (app)
streamlit run streamlit_app.py         # la base de datos se autogenera al primer arranque
```

Para desarrollo y tests:

```bash
pip install -r requirements-dev.txt
playwright install chromium            # solo para la captura headless (scripts/shoot.py)
pytest
```

### Despliegue (Streamlit Community Cloud)

`streamlit_app.py` es el punto de entrada. El repositorio no incluye base de datos
(`.sqlite` está en `.gitignore` por privacidad); la app la regenera sola al cargar. Subir el
repositorio a GitHub y apuntar Streamlit Cloud a `streamlit_app.py`.

## Contexto

Propuesta para la Beca de Excelencia de la **Fundación Caja Rural de Asturias**. Proyecto de
desarrollo rural que usa la energía como herramienta. Replicable a concejos en riesgo de
despoblación (Somiedo, Ponga, Allande, Ibias, Degaña, Quirós…) a coste de copia casi nulo.
