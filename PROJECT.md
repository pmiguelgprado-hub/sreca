---
type: project
status: active
tags: [sreca, energia, autoconsumo, comunidad-energetica, beca, asturias]
created: 2026-06-19
updated: 2026-06-20
related: [docs/2026-06-19-sreca-mvp-design.md, docs/2026-06-19-legal-verification-2026.md]
---

# SRECA — PROJECT

Documento de proyecto. El código vive en este repositorio.

## Qué es

Cerebro software de una **Comunidad Energética Local** (piloto Teverga): autoconsumo colectivo
FV 15 kWp + analítica predictiva (Open-Meteo + curvas de carga) que optimiza el perfil ex-ante
de coeficientes de reparto y desplaza cargas flexibles a la ventana solar. Sin baterías.
Stack coste-licencia **0 €** (Python/Streamlit/Open-Meteo/SQLite). Propuesta para la
**convocatoria de innovación (máster) de la Fundación Caja Rural de Asturias**: desarrollar un
proyecto que ayude a la Asturias rural (cierre 31 de julio de 2026).

## Estado

| | |
|---|---|
| Fase | 0 — diseño aprobado + scaffolding |
| Hecho | Investigación + memoria de beca (sesión previa); verificación legal 2026; spec MVP; repo + skeleton + config Teverga |
| Siguiente | Implementación TDD del MVP (slice vertical fino) |
| Dinero/despliegue | N/A (proyecto de estudiante, multi-sesión) |

## Decisiones resueltas (2026-06-19)

1. **Legal 2026 (Open Decision #1)** → optimizador **ex-ante** (ley vigente TED/1247/2021,
   modificación ≥4 meses); ex-post dinámico = forward stub gated al RD pendiente. 5 km
   proximidad + figura "gestor de autoconsumo" (RDL 7/2026). Ver `docs/2026-06-19-legal-verification-2026.md`.
2. **Piloto** Teverga + config por-concejo. 3. Curvas **sintéticas** parametrizables.
   4. **Reglas** (ML v2 gated). 5. PV **simulado** desde Open-Meteo. 6. Hosting **Streamlit Cloud**
   (disparador RGPD → local). 7. MVP = slice vertical fino.

## Verificaciones de fidelidad hechas

- **Teoría energética (MUII)**: yield 1.114 kWh/kWp, PR 76,5 %, modelo FV físico (POA→NOCT→γ).
- **Norma 2026**: fórmula de autoconsumo = reparto horario por CUPS RD 244/2019; corrección de
  cadencia de coeficientes (≥4 meses, no diario).
- **Sinergia corregida** (no revertir): ordeño fuera de campana solar; IA desplaza cargas
  flexibles. Encoded como invariante con test guard.

## Docs

- Spec de diseño MVP: `docs/2026-06-19-sreca-mvp-design.md`
- Verificación legal 2026: `docs/2026-06-19-legal-verification-2026.md`
- Fuentes de datos oficiales (INE en fuente, PVPC 2026, encaje Caja Rural): `docs/2026-06-22-official-data-sources.md`
- Memoria de beca e investigación de partida: documento interno (no incluido en el repo).
