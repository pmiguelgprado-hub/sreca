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

    from sreca.dashboard.data import load_dashboard_data

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
        "día-tipo medio anual (proxy MVP — perfil mensual ex-ante pendiente de cablear)"
    )

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
    st.metric("Ahorro total comunidad (€/día-tipo)",
              round(sum(s["eur_saved"] for s in d.savings.values()), 2))

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


if __name__ == "__main__":
    render()
