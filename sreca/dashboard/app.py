"""SRECA cockpit, an interactive Streamlit analytics tool over the pure backbone.

Launch (from the repo root):  streamlit run streamlit_app.py

This is a working instrument, not a slideshow: the sidebar controls (plant size, prices,
per-household consumption, an uploaded CSV of real curves) recompute every figure live through
sreca.dashboard.analytics (pure, DB-free). Importing this module only defines helpers; the
render runs under `streamlit run`, so the heavy UI imports stay inside render().
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

# `streamlit run` puts the script's directory on sys.path, not the repo root, so an absolute
# `import sreca` fails. Make the package importable however the app is launched.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ---- Palette: light cool-technical cockpit. Blue = structure/data, amber = solar (meaningful),
#      neutrals tinted cool. Defined once, reused across every Plotly figure. ------------------
INK = "#1B2733"      # deep slate text (tinted, never pure black)
MUTED = "#5A6B7B"
LINE = "#E2E8F0"     # cool hairline
BLUE = "#2563EB"     # primary structural / "to grid"
AMBER = "#E08A1E"    # solar generation / self-consumed (the one meaningful accent)
TEAL = "#2F8F6B"     # social priority (equity) only
GREY = "#94A3B8"     # grid import (bought)
DEMAND_COLORS = ["#3E6E9C", "#C2683B", "#7A6FA0", "#4F7A5B"]

_MONTHS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

_DISPLAY_FIX = {"lactea": "láctea", "frio": "frío", "ordeno": "ordeño", "acs": "ACS"}


def _pretty(name: str) -> str:
    """Humanise an id for display (config-agnostic, no per-concejo hardcode)."""
    out = []
    for i, w in enumerate(name.replace("_", " ").strip().split()):
        out.append(_DISPLAY_FIX.get(w.lower(), w.capitalize() if i == 0 else w.lower()))
    return " ".join(out)


def _es(n: float, dec: int = 0) -> str:
    """Spanish number formatting: thousands '.', decimals ','."""
    s = f"{n:,.{dec}f}"
    return s.replace(",", "·").replace(".", ",").replace("·", ".")


@lru_cache(maxsize=64)
def _compute(concejo_stem, kwp, retail, comp, daily_items, demand_items):
    """Live recompute, memoised by primitive inputs (the 8760h chain is the heavy part).

    Rebuilds the overridden config and the bundle from scratch; all args are hashable so a
    repeated slider position is free. Returns a CockpitBundle.
    """
    import pandas as pd

    from sreca.concejo import load_concejo
    from sreca.dashboard.analytics import apply_overrides, cockpit_bundle
    from sreca.datasets import climatology_path

    cfg = apply_overrides(
        load_concejo(concejo_stem),
        kwp=kwp,
        retail_eur_kwh=retail,
        compensation_eur_kwh=comp,
        daily_kwh=dict(daily_items) or None,
    )
    clim = pd.read_csv(climatology_path(concejo_stem))
    override = {pid: list(c) for pid, c in demand_items} if demand_items else None
    return cockpit_bundle(cfg, clim, demand_override=override)


_CSS = """
<style>
  .block-container { max-width: 1280px; padding-top: 2.2rem; padding-bottom: 3rem; }
  [data-testid="stSidebar"] { background: #EEF2F7; border-right: 1px solid #E2E8F0; }
  .ck-brand { font-weight: 800; font-size: 1.15rem; letter-spacing: -0.01em; color: #1B2733; }
  .ck-brand span { color: #E08A1E; }
  .ck-head { display: flex; align-items: baseline; gap: 0.7rem; flex-wrap: wrap;
             border-bottom: 1px solid #E2E8F0; padding-bottom: 0.7rem; margin-bottom: 1.1rem; }
  .ck-head h1 { font-size: 1.45rem; font-weight: 800; margin: 0; color: #1B2733;
                letter-spacing: -0.01em; }
  .ck-head .mission { color: #5A6B7B; font-size: 0.95rem; }
  .ck-badge { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
              padding: 0.18rem 0.5rem; border-radius: 5px; border: 1px solid #E2E8F0; color: #2563EB;
              background: #fff; }
  .ck-badge.amber { color: #B26A12; border-color: #F0DEC4; background: #FCF6EC; }
  /* KPI readouts: monospaced tabular figures for an instrument feel */
  [data-testid="stMetricValue"] { font-family: "SF Mono", ui-monospace, Menlo, monospace;
       font-size: 1.2rem; font-weight: 700; color: #1B2733; letter-spacing: -0.03em;
       white-space: nowrap; overflow: visible; text-overflow: clip; }
  [data-testid="stMetricLabel"] { overflow: visible; }
  [data-testid="stMetricLabel"] p { font-size: 0.72rem; color: #5A6B7B; font-weight: 600;
       white-space: nowrap; overflow: visible; text-overflow: clip; }
  [data-testid="stMetricDelta"] { font-size: 0.78rem; }
  [data-testid="stMetric"] { background: #fff; border: 1px solid #E2E8F0; border-radius: 10px;
       padding: 0.7rem 0.9rem; }
  .kpi-row { display: flex; gap: 0.55rem; margin: 0.2rem 0 0.6rem; }
  .kpi { flex: 1; min-width: 0; background: #fff; border: 1px solid #E2E8F0; border-radius: 10px;
         padding: 0.6rem 0.8rem; }
  .kpi-l { font-size: 0.71rem; color: #5A6B7B; font-weight: 600; white-space: nowrap;
           text-overflow: ellipsis; overflow: hidden; }
  .kpi-v { font-family: "SF Mono", ui-monospace, Menlo, monospace; font-size: 1.3rem;
           font-weight: 700; color: #1B2733; letter-spacing: -0.03em; white-space: nowrap; }
  .kpi-u { font-size: 0.68rem; color: #8593A1; margin-left: 0.25rem; font-family: system-ui; }
  .kpi-d { font-size: 0.73rem; font-weight: 600; white-space: nowrap; }
  .kpi-d.up { color: #2F8F6B; } .kpi-d.down { color: #C2683B; }
  .stTabs [data-baseweb="tab-list"] { gap: 0.3rem; }
  .stTabs [data-baseweb="tab"] { font-weight: 600; font-size: 0.92rem; }
  .ck-note { color: #8593A1; font-size: 0.82rem; line-height: 1.5; }
  thead tr th { font-size: 0.82rem !important; }
  td, th { font-variant-numeric: tabular-nums; }
</style>
"""


def _signed(value: float, dec: int = 0, suffix: str = "") -> str:
    sign = "+" if value >= 0 else "−"
    return f'{sign}{_es(abs(value), dec)}{suffix}'


def _kpi(label: str, value: str, unit: str, delta: str | None = None, tip: str = "") -> str:
    d = ""
    if delta is not None:
        cls = "down" if delta.startswith("−") else "up"
        d = f'<div class="kpi-d {cls}">{delta}</div>'
    return (f'<div class="kpi" title="{tip}"><div class="kpi-l">{label}</div>'
            f'<div class="kpi-v">{value}<span class="kpi-u">{unit}</span></div>{d}</div>')


def _layout(go, **extra):
    base = dict(
        height=340,
        margin=dict(l=8, r=8, t=28, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=INK, family="system-ui, -apple-system, Segoe UI, sans-serif", size=12),
        legend=dict(orientation="h", y=-0.2, font=dict(size=11)),
        xaxis=dict(gridcolor=LINE, zeroline=False),
        yaxis=dict(gridcolor=LINE, zeroline=False),
        title=dict(font=dict(size=13, color=INK), x=0.01, xanchor="left"),
    )
    base.update(extra)
    return base


def render(concejo: str = "teverga") -> None:
    import pandas as pd
    import plotly.graph_objects as go
    import streamlit as st

    from sreca.concejo import available_concejos, load_concejo
    from sreca.dashboard.analytics import demand_from_csv
    from sreca.dashboard.data import territory_context
    from sreca.forecast.demand import daily_demand

    st.set_page_config(page_title="SRECA · Cockpit energético", page_icon="☀️", layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)

    stems = available_concejos() or [concejo]
    display_to_stem = {load_concejo(s).concejo: s for s in stems}
    displays = sorted(display_to_stem)

    # ---- Sidebar: the control panel (slicers + scenario knobs + data upload) ----------------
    with st.sidebar:
        st.markdown('<div class="ck-brand">SRE<span>CA</span></div>', unsafe_allow_html=True)
        st.caption("Cockpit de la comunidad energética")
        default_display = next((d for d in displays if display_to_stem[d] == concejo), displays[0])
        chosen = st.selectbox("Concejo", displays, index=displays.index(default_display))
        stem = display_to_stem[chosen]
        base = load_concejo(stem)

        st.markdown("**Escenario**")
        kwp = st.slider("Potencia instalada (kWp)", 5.0, 50.0, float(base.pv.kwp), 1.0,
                        help="Tamaño de la instalación solar compartida.")
        retail = st.slider("Precio minorista (€/kWh)", 0.10, 0.35, float(base.prices.retail_eur_kwh),
                           0.01, help="Coste evitado por cada kWh autoconsumido (PVPC 2026 ≈ 0,16-0,22).")
        comp = st.slider("Compensación excedentes (€/kWh)", 0.02, 0.15,
                         float(base.prices.compensation_eur_kwh), 0.005,
                         help="Precio del excedente vertido a red (PVPC 2026 ≈ 0,06-0,10).")

        with st.expander("Consumo por hogar (kWh/día)"):
            daily = {}
            for p in base.participants:
                daily[p.id] = st.number_input(_pretty(p.id), 1.0, 100.0, float(p.daily_kwh), 1.0,
                                              key=f"d_{p.id}")

        st.markdown("**Curvas de consumo reales**")
        template = pd.DataFrame({"hour": range(24)})
        for p in base.participants:
            template[p.id] = [round(x, 3) for x in daily_demand(p.profile, p.daily_kwh)]
        st.download_button("Descargar plantilla CSV", template.to_csv(index=False),
                           "curvas_consumo.csv", "text/csv", use_container_width=True)
        up = st.file_uploader("Subir CSV de curvas", type=["csv"],
                              help="Columna 'hour' (0..23) + una columna por hogar, en kWh.")
        demand_items, upload_state = None, None
        if up is not None:
            try:
                override = demand_from_csv(pd.read_csv(up))
                demand_items = tuple(sorted((pid, tuple(map(float, c))) for pid, c in override.items()))
                upload_state = ("ok", list(override))
            except Exception as exc:  # noqa: BLE001 - surface any parse error to the user
                upload_state = ("err", str(exc))
        st.markdown('<p class="ck-note">Las curvas subidas se usan solo en esta sesión, no se '
                    "guardan (privacidad por diseño).</p>", unsafe_allow_html=True)

    # ---- Recompute: base scenario (for deltas) + current scenario ---------------------------
    base_daily = tuple(sorted((p.id, float(p.daily_kwh)) for p in base.participants))
    cur_daily = tuple(sorted((k, float(v)) for k, v in daily.items()))
    b0 = _compute(stem, float(base.pv.kwp), float(base.prices.retail_eur_kwh),
                  float(base.prices.compensation_eur_kwh), base_daily, None)
    b = _compute(stem, float(kwp), float(retail), float(comp), cur_daily, demand_items)
    changed = (float(kwp), float(retail), float(comp), cur_daily, demand_items) != (
        float(base.pv.kwp), float(base.prices.retail_eur_kwh),
        float(base.prices.compensation_eur_kwh), base_daily, None)

    if upload_state and upload_state[0] == "ok":
        st.sidebar.success("Curvas cargadas: " + ", ".join(_pretty(x) for x in upload_state[1]))
    elif upload_state and upload_state[0] == "err":
        st.sidebar.error(upload_state[1])

    # ---- Header: one compact mission line + status badges -----------------------------------
    st.markdown(
        f"""<div class="ck-head">
          <h1>Cockpit energético · {chosen}</h1>
          <span class="mission">Energía solar comunitaria para la Asturias rural</span>
          <span class="ck-badge">Reparto {b.coefficient_mode.replace('_', '-')}</span>
          <span class="ck-badge amber">Datos sintéticos</span>
        </div>""",
        unsafe_allow_html=True,
    )

    a, a0 = b.annual, b0.annual
    sc = (a.self_consumption_rate - a0.self_consumption_rate) * 100
    cov = (a.demand_coverage - a0.demand_coverage) * 100
    cards = [
        _kpi("Generación", _es(a.gen_kwh), "kWh/año",
             _signed(a.gen_kwh - a0.gen_kwh) if changed else None,
             "Producción solar anual (año meteorológico tipo PVGIS, 8.760 h)."),
        _kpi("Autoconsumo", f"{a.self_consumption_rate * 100:.0f}", "%",
             _signed(sc, suffix=" pp") if changed else None,
             "Parte de la generación consumida por la comunidad. Σ min(gen, demanda), honesto."),
        _kpi("Demanda cubierta", f"{a.demand_coverage * 100:.0f}", "%",
             _signed(cov, suffix=" pp") if changed else None,
             "Parte de la demanda total cubierta con energía solar."),
        _kpi("Ahorro", _es(a.community_eur), "€/año",
             _signed(a.community_eur - a0.community_eur) if changed else None,
             "Autoconsumo al precio minorista evitado + excedente a compensación."),
        _kpi("Excedente", _es(a.excess_kwh), "kWh",
             tip="Energía solar exportada a la red (no autoconsumida)."),
        _kpi("Potencia", _es(kwp), "kWp",
             _signed(kwp - base.pv.kwp) if kwp != base.pv.kwp else None,
             "Tamaño de la instalación (ajustable en el panel)."),
    ]
    st.markdown(f'<div class="kpi-row">{"".join(cards)}</div>', unsafe_allow_html=True)

    tab_res, tab_prod, tab_rep, tab_dat = st.tabs(
        ["Resumen", "Producción", "Reparto y cargas", "Datos y supuestos"])

    # ===== Resumen: energy balance + day-type curve ==========================================
    with tab_res:
        c1, c2 = st.columns([5, 6])
        with c1:
            bal = b.balance
            fig = go.Figure()
            fig.add_trace(go.Bar(y=["Generación"], x=[bal.self_consumed_kwh], orientation="h",
                                 name="Autoconsumida", marker_color=AMBER))
            fig.add_trace(go.Bar(y=["Generación"], x=[bal.exported_kwh], orientation="h",
                                 name="Vertida a red", marker_color=BLUE))
            fig.add_trace(go.Bar(y=["Demanda"], x=[bal.self_consumed_kwh], orientation="h",
                                 name="Cubierta con sol", marker_color=AMBER, showlegend=False))
            fig.add_trace(go.Bar(y=["Demanda"], x=[bal.grid_import_kwh], orientation="h",
                                 name="Importada de red", marker_color=GREY))
            fig.update_layout(**_layout(go, barmode="stack", height=270,
                                        title="Balance energético anual (kWh)",
                                        legend=dict(orientation="h", y=-0.12, font=dict(size=11))))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        with c2:
            fig_m = go.Figure(go.Bar(x=_MONTHS, y=[b.monthly[m] for m in range(1, 13)],
                                     marker_color=AMBER))
            fig_m.update_layout(**_layout(go, height=260, title="Generación por mes (kWh)",
                                          yaxis_title="kWh"))
            st.plotly_chart(fig_m, use_container_width=True, config={"displayModeBar": False})

        hours = list(range(24))
        fig_d = go.Figure()
        fig_d.add_trace(go.Scatter(x=hours, y=b.gen_daytype, name="Generación solar", fill="tozeroy",
                                   line=dict(color=AMBER, width=2), fillcolor="rgba(224,138,30,0.16)"))
        for i, (pid, series) in enumerate(b.demand_daytype.items()):
            fig_d.add_trace(go.Scatter(x=hours, y=series, name=_pretty(pid), mode="lines",
                                       line=dict(color=DEMAND_COLORS[i % len(DEMAND_COLORS)], width=2)))
        fig_d.update_layout(**_layout(go, title="Día medio · sol frente a consumo",
                                      xaxis_title="Hora", yaxis_title="kWh"))
        st.plotly_chart(fig_d, use_container_width=True, config={"displayModeBar": False})
        st.markdown('<p class="ck-note">El ordeño de la granja (madrugada y tarde) cae fuera de las '
                    "horas de sol: la sinergia es sumar consumos diversos y desplazar lo flexible, "
                    "no casar ordeño con sol.</p>", unsafe_allow_html=True)

    # ===== Producción: the signature hour×month heatmap ======================================
    with tab_prod:
        hm = b.heatmap
        fig_h = go.Figure(go.Heatmap(
            z=hm.values, x=[f"{h:02d}h" for h in hm.columns], y=_MONTHS,
            colorscale=[[0, "#F4F6FA"], [0.5, "#F4C36B"], [1, AMBER]],
            colorbar=dict(title="kWh", thickness=12)))
        fig_h.update_layout(**_layout(go, height=420, title="Intensidad de generación · hora × mes",
                                      xaxis_title="Hora del día"))
        st.plotly_chart(fig_h, use_container_width=True, config={"displayModeBar": False})
        st.markdown('<p class="ck-note">Cada celda es la generación media de esa hora en ese mes. '
                    "La franja ámbar central muestra cuándo el sistema realmente produce: ahí es "
                    "donde el reparto y el desplazamiento de cargas tienen efecto.</p>",
                    unsafe_allow_html=True)

    # ===== Reparto y cargas: fairness + load-shift ===========================================
    with tab_rep:
        c1, c2 = st.columns([6, 5])
        with c1:
            hours = list(range(24))
            fig_b = go.Figure()
            for i, (pid, betas) in enumerate(b.beta_daytype.items()):
                fig_b.add_trace(go.Scatter(x=hours, y=betas, name=_pretty(pid), mode="lines",
                                           stackgroup="one",
                                           line=dict(color=DEMAND_COLORS[i % len(DEMAND_COLORS)],
                                                     width=0.5)))
            fig_b.update_layout(**_layout(go, title="Reparto del sol por hora (β, suma 1)",
                                          xaxis_title="Hora", yaxis=dict(range=[0, 1], gridcolor=LINE)))
            st.plotly_chart(fig_b, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<p class="ck-note">Al amanecer y al atardecer el sol no llega para todos: '
                        "el reparto prioriza a los hogares vulnerables (misión social).</p>",
                        unsafe_allow_html=True)
        with c2:
            parts = b.annual.participants
            order = sorted(parts, key=lambda p: parts[p].eur_saved)
            fig_s = go.Figure(go.Bar(
                y=[_pretty(p) for p in order], x=[parts[p].eur_saved for p in order],
                orientation="h", marker_color=TEAL,
                text=[f"{_es(parts[p].eur_saved)} €" for p in order], textposition="auto"))
            fig_s.update_layout(**_layout(go, title="Ahorro anual por hogar (€)",
                                          xaxis_title="€/año"))
            st.plotly_chart(fig_s, use_container_width=True, config={"displayModeBar": False})

        if b.load_shift:
            st.markdown("**Desplazar cargas flexibles a la ventana solar** (recomendación tras contador)")
            st.dataframe(
                [{"Carga flexible": _pretty(n),
                  "Horas de sol recomendadas": ", ".join(f"{h:02d}h" for h in hrs)}
                 for n, hrs in b.load_shift.items()],
                use_container_width=True, hide_index=True)

    # ===== Datos y supuestos: the honesty panel (prose lives here, tooltips elsewhere) =======
    with tab_dat:
        t = territory_context(base)
        c1, c2, c3 = st.columns(3)
        if t.population:
            c1.metric("Población", f"{_es(t.population)}",
                      help=f"INE {t.population_year}. Municipio de reto demográfico (<5.000 hab).")
        if t.density_hab_km2:
            c2.metric("Densidad", f"{t.density_hab_km2:.1f} hab/km²", help="España vaciada.")
        c3.metric("Coste licencias", "0 €", help="Python · Streamlit · Open-Meteo · PVGIS · SQLite.")
        st.markdown(
            """
- **Datos de consumo sintéticos** e ilustrativos hasta cargar curvas reales de los vecinos
  (sube tu CSV en la barra lateral). El dimensionado de cargas flexibles de la granja es provisional.
- **Generación** simulada con modelo físico calibrado contra PVGIS (año meteorológico tipo, 8.760 h);
  las cifras anuales no extrapolan un día medio (evita el sesgo de Jensen).
- **Precios PVPC 2026** conservadores (minorista ≈ 0,20 €/kWh, excedente ≈ 0,06 €/kWh); ajustables arriba.
- **Marco legal**: coeficientes de reparto **ex-ante** (Orden TED/1247/2021, revisión ≥ 4 meses);
  el reparto dinámico diario aún no es legal. Proximidad 5 km y figura de gestor de autoconsumo
  (RDL 7/2026).
- **Fuentes**: PVGIS (JRC), INE (padrón 2025, verificado en fuente), REE/ESIOS (PVPC), BOE.
  Ver `docs/2026-06-22-official-data-sources.md`.
""")
        st.markdown('<p class="ck-note">Propuesta para la convocatoria de innovación (máster) de la '
                    "Fundación Caja Rural de Asturias: un proyecto para ayudar a la Asturias rural "
                    "(cierre 31 de julio de 2026).</p>", unsafe_allow_html=True)


if __name__ == "__main__":
    render()
