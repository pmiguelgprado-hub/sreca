"""SRECA dashboard — thin Streamlit view over the pure data layer (sreca.dashboard.data).

Launch:  cd ~/AIOS/projects/sreca && .venv/bin/streamlit run sreca/dashboard/app.py
Populate the DB first:  .venv/bin/python -m sreca.main data/local/sreca.sqlite

All read/shape logic lives in data.py (unit-tested); this file only renders. Importing it
does nothing (render runs only under `streamlit run`), so it stays import-safe in tests.
"""
from __future__ import annotations

import os

DEFAULT_DB = os.environ.get("SRECA_DB", "data/local/sreca.sqlite")


def render(db_path: str = DEFAULT_DB) -> None:
    import plotly.graph_objects as go
    import streamlit as st

    from sreca.dashboard.data import community_kpis, load_dashboard_data

    st.set_page_config(page_title="SRECA", page_icon="☀️", layout="wide")
    st.title("☀️ SRECA — Comunidad Energética Local")

    d = load_dashboard_data(db_path)
    if d is None:
        st.warning(
            f"No hay datos en `{db_path}`. Genera un run:\n\n"
            "`.venv/bin/python -m sreca.main data/local/sreca.sqlite`"
        )
        return

    st.caption(
        f"Concejo: **{d.concejo}** · run `{d.run_id}` · modo `{d.coefficient_mode}` · "
        "resumen sobre día-tipo medio anual; perfil legal mensual ex-ante abajo"
    )

    # KPI row — headline community metrics
    k = community_kpis(d)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tasa autoconsumo colectivo", f"{k.self_consumption_rate * 100:.0f} %")
    c2.metric("Cobertura demanda", f"{k.demand_coverage * 100:.0f} %")
    c3.metric("Generación FV", f"{k.generation_kwh:.1f} kWh")
    c4.metric("Ahorro comunidad", f"{k.savings_eur:.2f} €")
    st.divider()

    hours = list(range(24))

    # Generation day-type + demand per participant
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hours, y=d.gen, name="Generación FV", fill="tozeroy",
                             line=dict(color="#f5a623")))
    for pid, series in d.demand.items():
        fig.add_trace(go.Scatter(x=hours, y=series, name=f"Demanda {pid}", mode="lines"))
    fig.update_layout(xaxis_title="Hora", yaxis_title="kWh", height=420,
                      legend=dict(orientation="h"))
    st.plotly_chart(fig, width="stretch")

    # Savings per household
    st.subheader("Ahorro por hogar (día-tipo)")
    rows = [
        {
            "Participante": pid,
            "Autoconsumido (kWh)": round(s["self_consumed_kwh"], 2),
            "Excedente (kWh)": round(s["excess_kwh"], 2),
            "Ahorro (€)": round(s["eur_saved"], 2),
        }
        for pid, s in d.savings.items()
    ]
    st.dataframe(rows, width="stretch")

    # Route B — la sinergia: desplazar cargas flexibles a la ventana solar
    st.subheader("Sinergia: desplazar cargas flexibles a la ventana solar")
    if d.load_shift:
        st.caption("Recomendación (Route B). Dimensionado de cargas = PLACEHOLDER, pendiente datos reales de la granja.")
        st.dataframe(
            [{"Carga flexible": name, "Horas recomendadas (sol)": ", ".join(f"{h:02d}h" for h in hours)}
             for name, hours in d.load_shift.items()],
            width="stretch",
        )
    else:
        st.caption("Sin cargas flexibles configuradas para este concejo.")

    # Route A legal artefact — monthly ex-ante coefficient profile (spec §4, revisable ≥4 meses)
    if d.ex_ante_schedule:
        st.subheader("Perfil ex-ante mensual de coeficientes de reparto (artefacto legal §4)")
        st.caption("Coeficientes β_i,h presentados a la distribuidora. Revisable ≥4 meses (TED/1247/2021).")
        months = {1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
                  7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"}
        sel = st.selectbox("Mes", sorted(d.ex_ante_schedule),
                           format_func=lambda m: months.get(m, str(m)))
        by_pid = d.ex_ante_schedule[sel]
        fig_b = go.Figure()
        for pid, betas in by_pid.items():
            fig_b.add_trace(go.Scatter(x=list(range(24)), y=betas, name=pid, mode="lines"))
        fig_b.update_layout(xaxis_title="Hora", yaxis_title="β (cuota de reparto)",
                            height=360, legend=dict(orientation="h"),
                            yaxis=dict(range=[0, 1]))
        st.plotly_chart(fig_b, width="stretch")


if __name__ == "__main__":
    render()
