"""SRECA — Streamlit Community Cloud entry point.

This is the default main-file name Streamlit Cloud looks for, and living at the repo root it
makes `import sreca` work out of the box. Run locally with:

    streamlit run streamlit_app.py

The dashboard auto-seeds the SQLite DB on first load if it is empty, so a fresh clone renders
with no manual step.
"""
from sreca.dashboard.app import render

render()
