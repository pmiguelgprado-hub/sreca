"""SRECA dashboard, thin Streamlit view over the pure data layer (sreca.dashboard.data).

Launch:  cd ~/AIOS/projects/sreca && .venv/bin/streamlit run streamlit_app.py
(The DB auto-seeds on first load if empty, so a fresh clone renders with no manual step.)

All read/shape logic lives in data.py (unit-tested); this file only renders. Importing it
does nothing (render runs only under `streamlit run`), so it stays import-safe in tests.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# `streamlit run` puts the script's directory on sys.path, not the repo root, so an
# absolute `import sreca` fails. Make the package importable however the app is launched.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

DEFAULT_DB = os.environ.get("SRECA_DB", str(_ROOT / "data" / "local" / "sreca.sqlite"))
DEFAULT_CONCEJO = os.environ.get("SRECA_CONCEJO", "teverga")

# Palette: warm paper, deep ink, amber sun, sage community. Defined once, reused in Plotly.
INK = "#2C2A26"
MUTED = "#8A8378"
AMBER = "#D98A2B"
SAGE = "#4F7A5B"
DEMAND_COLORS = ["#2E6E8E", "#B0623A", "#7A6FA0"]  # distinct, harmonious demand lines

_CSS = """
<style>
  .block-container { max-width: 1080px; padding-top: 3.4rem; padding-bottom: 4rem; }
  .sreca-hero { border-bottom: 1px solid #E4DCCB; padding-bottom: 1.1rem; margin-bottom: 1.6rem; }
  .sreca-hero h1 { font-size: 2.7rem; font-weight: 800; letter-spacing: -0.02em;
                   margin: 0; color: #2C2A26; }
  .sreca-hero .kicker { color: #D98A2B; font-weight: 700; text-transform: uppercase;
                        letter-spacing: 0.12em; font-size: 0.78rem; }
  .sreca-hero .tagline { color: #5C564C; font-size: 1.12rem; margin-top: 0.45rem;
                         max-width: 60ch; line-height: 1.5; }
  .sreca-facts { display: flex; gap: 2.4rem; flex-wrap: wrap; margin: 0.4rem 0 0.2rem; }
  .sreca-facts .f { } .sreca-facts .n { font-size: 1.5rem; font-weight: 800; color: #4F7A5B; }
  .sreca-facts .l { font-size: 0.82rem; color: #5C564C; max-width: 24ch; }
  h2.sreca-sec { font-size: 1.4rem; font-weight: 750; margin: 2.2rem 0 0.2rem;
                 color: #2C2A26; }
  .sreca-note { color: #8A8378; font-size: 0.84rem; }
  [data-testid="stMetricValue"] { font-size: 2.0rem; font-weight: 800; }
  [data-testid="stMetricLabel"] p { font-size: 0.86rem; color: #5C564C; }
  .sreca-foot { color: #8A8378; font-size: 0.8rem; line-height: 1.6;
                border-top: 1px solid #E4DCCB; margin-top: 2.6rem; padding-top: 1rem; }
  .step { background: #FCF9F3; border: 1px solid #ECE3D2; border-radius: 12px;
          padding: 1rem 1.1rem; height: 100%; }
  .step .s { color: #D98A2B; font-weight: 800; font-size: 0.8rem; letter-spacing: 0.08em; }
  .step h4 { margin: 0.2rem 0 0.4rem; font-size: 1.05rem; color: #2C2A26; }
  .step p { margin: 0; color: #5C564C; font-size: 0.92rem; line-height: 1.5; }
</style>
"""


def _ensure_seeded(db_path: str, concejos: list[str]) -> None:
    """Auto-seed each concejo on a fresh clone so the app renders with no manual step (cloud-ready)."""
    from sreca import main
    from sreca.concejo import load_concejo
    from sreca.store import db

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = db.connect(db_path)
    for stem in concejos:
        display = load_concejo(stem).concejo
        if db.latest_run_id(conn, display) is None:
            main.run_rebalance(stem, db_path)


# Spanish orthography fixups for display ids (token-level, config-agnostic, not per-concejo).
_DISPLAY_FIX = {"lactea": "láctea", "frio": "frío", "ordeno": "ordeño", "acs": "ACS"}


def _pretty(name: str) -> str:
    """Humanise an id for display (config-agnostic, no per-concejo hardcode, invariant §9.4)."""
    words = name.replace("_", " ").strip().split()
    out = []
    for i, w in enumerate(words):
        if w.lower() in _DISPLAY_FIX:
            out.append(_DISPLAY_FIX[w.lower()])
        else:
            out.append(w.capitalize() if i == 0 else w.lower())
    return " ".join(out)


def _plotly_layout(**extra):
    base = dict(
        height=420,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=INK, family="sans-serif"),
        legend=dict(orientation="h", y=-0.18, font=dict(size=12)),
        xaxis=dict(gridcolor="#ECE3D2", zeroline=False),
        yaxis=dict(gridcolor="#ECE3D2", zeroline=False),
    )
    base.update(extra)
    return base


def render(db_path: str = DEFAULT_DB, concejo: str = DEFAULT_CONCEJO) -> None:
    import plotly.graph_objects as go
    import streamlit as st

    from sreca.concejo import available_concejos, load_concejo
    from sreca.dashboard.data import load_dashboard_data

    st.set_page_config(page_title="SRECA, Comunidad Energética Local", page_icon="☀️",
                       layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)

    stems = available_concejos() or [concejo]
    _ensure_seeded(db_path, stems)

    # Concejo picker (replicability is real: same software, each concejo's own config + climate).
    display_to_stem = {load_concejo(s).concejo: s for s in stems}
    displays = sorted(display_to_stem)
    default_display = next((d for d in displays if display_to_stem[d] == concejo), displays[0])
    chosen = st.sidebar.selectbox("Concejo", displays, index=displays.index(default_display))
    stem = display_to_stem[chosen]
    cfg = load_concejo(stem)
    st.sidebar.caption("Mismo cerebro, otro concejo: solo cambian la configuración y los "
                       "datos de recurso solar (PVGIS).")

    d = load_dashboard_data(db_path, concejo=chosen)
    if d is None:
        st.error("No se pudo generar el run inicial. Revisa la configuración del concejo.")
        return

    # ---- Hero ---------------------------------------------------------------
    st.markdown(
        f"""
        <div class="sreca-hero">
          <div class="kicker">Comunidad Energética Local · {d.concejo}, Asturias</div>
          <h1>SRECA</h1>
          <div class="tagline">Energía solar compartida y repartida con criterio social,
          para que la Asturias rural produzca su propia electricidad y frene la despoblación.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- Problem framing ----------------------------------------------------
    st.markdown(
        "En la Asturias rural conviven el sol y el abandono. Una instalación solar compartida "
        "de **15 kWp** puede dar electricidad barata y local a varios vecinos a la vez. El reto "
        "no es generar: es repartir bien esa energía y consumirla cuando hay sol. De eso se "
        "ocupa SRECA."
    )
    facts = []
    if cfg.population:
        pop = f"{cfg.population:,}".replace(",", ".")
        yr = f" (INE {cfg.population_year})" if cfg.population_year else ""
        facts.append(f'<div class="f"><div class="n">{pop}</div>'
                     f'<div class="l">habitantes en {cfg.concejo}{yr}</div></div>')
    facts.append('<div class="f"><div class="n">15,9 %</div><div class="l">hogares asturianos en '
                 'riesgo de pobreza energética (AROPE 2025)</div></div>')
    facts.append('<div class="f"><div class="n">0 €</div><div class="l">en licencias de software '
                 '(Python, Streamlit, Open-Meteo, PVGIS)</div></div>')
    st.markdown(f'<div class="sreca-facts">{"".join(facts)}</div>', unsafe_allow_html=True)

    # ---- Annual headline (honest, 8760h chain) ------------------------------
    st.markdown('<h2 class="sreca-sec">Lo que consigue la comunidad en un año</h2>',
                unsafe_allow_html=True)
    a = d.annual
    if a is not None:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Generación solar", f"{a.gen_kwh:,.0f} kWh".replace(",", "."))
        c2.metric("Autoconsumo colectivo", f"{a.self_consumption_rate * 100:.0f} %")
        c3.metric("Demanda cubierta con sol", f"{a.demand_coverage * 100:.0f} %")
        c4.metric("Ahorro de la comunidad", f"{a.community_eur:,.0f} €/año".replace(",", "."))
        st.markdown(
            '<p class="sreca-note">Cifras anuales sobre un año meteorológico tipo (PVGIS TMY), '
            "calculadas hora a hora (8.760 h), no extrapolando un día medio. Curvas de consumo "
            "sintéticas e ilustrativas hasta disponer de datos reales de los vecinos.</p>",
            unsafe_allow_html=True,
        )

    # ---- How the brain works ------------------------------------------------
    st.markdown('<h2 class="sreca-sec">Cómo funciona el cerebro</h2>', unsafe_allow_html=True)
    s1, s2, s3 = st.columns(3)
    s1.markdown(
        '<div class="step"><div class="s">01 · PREDICE</div><h4>El sol y el consumo</h4>'
        "<p>Modelo físico calibrado con PVGIS para la generación solar, y curvas de consumo "
        "por perfil de vecino, hora a hora.</p></div>", unsafe_allow_html=True)
    s2.markdown(
        '<div class="step"><div class="s">02 · REPARTE</div><h4>Con criterio social</h4>'
        "<p>Calcula el perfil de coeficientes que maximiza el autoconsumo colectivo y, cuando "
        "el sol no llega para todos, atiende primero a los hogares vulnerables.</p></div>",
        unsafe_allow_html=True)
    s3.markdown(
        '<div class="step"><div class="s">03 · DESPLAZA</div><h4>Las cargas flexibles</h4>'
        "<p>Recomienda mover el enfriado de la leche y el agua caliente de limpieza a las horas "
        "de sol. El ordeño no se toca: ocurre de noche y sigue en la red.</p></div>",
        unsafe_allow_html=True)

    # ---- Day-type curve -----------------------------------------------------
    st.markdown('<h2 class="sreca-sec">Un día medio: cuándo hay sol y cuándo se consume</h2>',
                unsafe_allow_html=True)
    hours = list(range(24))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hours, y=d.gen, name="Generación solar", fill="tozeroy",
                             line=dict(color=AMBER, width=2),
                             fillcolor="rgba(217,138,43,0.18)"))
    for i, (pid, series) in enumerate(d.demand.items()):
        fig.add_trace(go.Scatter(x=hours, y=series, name=f"Consumo {_pretty(pid)}", mode="lines",
                                 line=dict(color=DEMAND_COLORS[i % len(DEMAND_COLORS)], width=2)))
    fig.update_layout(**_plotly_layout(xaxis_title="Hora del día", yaxis_title="kWh"))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.markdown(
        '<p class="sreca-note">La campana ámbar es el sol. El consumo de la granja láctea sube '
        "al amanecer y al atardecer (el ordeño), fuera de las horas de sol: por eso la sinergia "
        "no es casar el ordeño con el sol, sino sumar consumos diversos y desplazar lo flexible.</p>",
        unsafe_allow_html=True,
    )

    # ---- Savings per household (annual) -------------------------------------
    st.markdown('<h2 class="sreca-sec">Ahorro anual estimado por hogar</h2>',
                unsafe_allow_html=True)
    src = a.participants if a is not None else None
    if src is not None:
        rows = [
            {
                "Hogar": _pretty(pid),
                "Autoconsumido (kWh/año)": round(s.self_consumed_kwh),
                "Vertido a red (kWh/año)": round(s.excess_kwh),
                "Ahorro (€/año)": round(s.eur_saved),
            }
            for pid, s in src.items()
        ]
        st.dataframe(rows, width="stretch", hide_index=True)
        st.markdown(
            '<p class="sreca-note">Autoconsumido valorado al precio minorista evitado; el vertido '
            "a red, a la compensación simplificada (más baja). Con datos reales el ahorro será "
            "algo menor que con curvas sintéticas (la demanda esperada no coincide con la real).</p>",
            unsafe_allow_html=True,
        )

    # ---- Route B: load shift (synergy) --------------------------------------
    st.markdown('<h2 class="sreca-sec">Desplazar las cargas flexibles al sol</h2>',
                unsafe_allow_html=True)
    if d.load_shift:
        st.dataframe(
            [{"Carga flexible": _pretty(name),
              "Horas de sol recomendadas": ", ".join(f"{h:02d}h" for h in hrs)}
             for name, hrs in d.load_shift.items()],
            width="stretch", hide_index=True,
        )
        st.markdown(
            '<p class="sreca-note">Recomendación posterior al contador, siempre legal. El '
            "dimensionado de estas cargas es provisional, pendiente de datos reales de la "
            "granja.</p>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<p class="sreca-note">Sin cargas flexibles configuradas para este concejo.</p>',
                    unsafe_allow_html=True)

    # ---- Route A legal artefact: monthly ex-ante coefficient profile --------
    if d.ex_ante_schedule:
        st.markdown('<h2 class="sreca-sec">El perfil legal de reparto (mes a mes)</h2>',
                    unsafe_allow_html=True)
        st.markdown(
            "La normativa vigente en 2026 (Orden TED/1247/2021) permite un perfil de "
            "coeficientes **fijo por horas**, revisable cada cuatro meses o más. SRECA calcula "
            "ese perfil óptimo, el que se presenta a la distribuidora. El reparto dinámico al "
            "día siguiente todavía no es legal: queda como extensión futura."
        )
        months = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
                  7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre",
                  12: "Diciembre"}
        sel = st.selectbox("Mes", sorted(d.ex_ante_schedule),
                           format_func=lambda m: months.get(m, str(m)), index=5)
        by_pid = d.ex_ante_schedule[sel]
        fig_b = go.Figure()
        for i, (pid, betas) in enumerate(by_pid.items()):
            fig_b.add_trace(go.Scatter(x=list(range(24)), y=betas, name=_pretty(pid), mode="lines",
                                       line=dict(color=DEMAND_COLORS[i % len(DEMAND_COLORS)],
                                                 width=2)))
        fig_b.update_layout(**_plotly_layout(
            xaxis_title="Hora del día", yaxis_title="Coeficiente de reparto β",
            yaxis=dict(range=[0, 1], gridcolor="#ECE3D2", zeroline=False), height=360))
        st.plotly_chart(fig_b, width="stretch", config={"displayModeBar": False})
        st.markdown(
            '<p class="sreca-note">Al amanecer y al atardecer apenas hay sol para todos: en esas '
            "horas el reparto da prioridad a los hogares más vulnerables (misión social), por eso "
            "su coeficiente sube. Dentro de un mismo grupo de renta el reparto es proporcional al "
            "consumo, no arbitrario.</p>",
            unsafe_allow_html=True,
        )

    # ---- Footer -------------------------------------------------------------
    st.markdown(
        f"""
        <div class="sreca-foot">
          <b>SRECA</b> · Propuesta para la Beca de Excelencia de la Fundación Caja Rural de
          Asturias. Concejo piloto: {d.concejo}. Replicable a otros concejos asturianos con su
          propia configuración y sus datos de recurso solar (PVGIS, gratis).<br>
          Fuentes: recurso solar PVGIS (JRC, año tipo), demografía INE 2025, pobreza energética
          AROPE 2025, marco legal RDL 7/2026 y Orden TED/1247/2021.
          Datos de consumo sintéticos, ilustrativos. Stack de coste 0 € en licencias.
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    render()
