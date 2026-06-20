---
type: spec
status: approved
tags: [sreca, design, mvp, autoconsumo, energia]
created: 2026-06-19
updated: 2026-06-19
related: [[PROJECT]], [[2026-06-19-legal-verification-2026]], [[2026-06-19-sreca-design]]
---

# SRECA — Spec de diseño (MVP)

Diseño aprobado (brainstorming 2026-06-19) del **cerebro software de SRECA**: Comunidad
Energética Local en Teverga, autoconsumo colectivo FV 15 kWp gestionado por analítica
predictiva. Stack coste-licencia **0 €**. Multi-sesión: este spec cubre el MVP; fase 2 al final.

Fuentes que NO se duplican aquí (referenciar):
- Investigación + memoria de beca: `~/.claude/plans/estoy-pensando-en-ideas-stateful-cascade.md`
- Verificación legal 2026 (resuelve Open Decision #1): `docs/2026-06-19-legal-verification-2026.md`
- Handoff de arranque: `~/AIOS/docs/handoffs/2026-06-19-sreca-design.md`

## 1. Objetivo del MVP

**Slice vertical fino, extremo-a-extremo, mínimo en cada capa.** Demuestra el cerebro entero:
Open-Meteo → forecast FV → forecast demanda → optimizador coef. ex-ante + recomendación de
desplazamiento de carga → SQLite → dashboard Streamlit. Concejo: Teverga. Participantes:
2-3 sintéticos (≥1 mayor-diurno + ≥1 granja-láctea). NO se construye todo el sistema este corte.

## 2. Decisiones resueltas

| # | Decisión | Resolución |
|---|---|---|
| 1 | Marco legal 2026 (optimizador ex-ante vs ex-post) | **ex-ante** (ley vigente, TED/1247/2021); ex-post = forward stub. Ver doc legal |
| 2 | Localización piloto | **Teverga** (cifras verificadas) + **config por-concejo** desde día 1 |
| 3 | Curvas de carga | **Sintéticas parametrizables** (perfiles mayor-diurno + granja-láctea) |
| 4 | Predicción reglas vs ML | **Reglas/heurístico** (MVP); ML = v2 gated por datos |
| 5 | Datos PV | **Simulación física** desde irradiancia Open-Meteo + modelo tipo PVGIS |
| 6 | Hosting | **Streamlit Cloud** (datos sintéticos) ahora; **disparador RGPD** → local/Pi cuando entren curvas reales de vecinos identificables |
| 7 | Alcance MVP | El slice vertical fino de §1 |

## 3. Arquitectura (módulos, una responsabilidad cada uno)

```
sreca/
  config/
    concejos/teverga.yaml      # lat/lon, tilt, kWp, losses, participantes, proximidad 5km
  ingest/
    open_meteo.py              # DOS modos (API gratis, mockeable):
                               #   archive (climatología, histórico/TMY) → perfil ex-ante
                               #   forecast (D+1)                          → load-shift
  forecast/
    pv.py                      # irradiancia → kWh (modelo físico, §5)
    demand.py                  # curvas sintéticas parametrizables por perfil
  optimize/
    coefficients.py            # compute_coefficients() water-filling + equidad (horizonte-agnóstico)
    schedule.py                # build_ex_ante_schedule() ensambla perfil anual legal (§6)
    load_shift.py              # recommend_flexible_load_shift() cargas flexibles → ventana solar
    savings.py                 # autoconsumido @retail vs excedente @compensación → €/hogar
  store/
    db.py                      # SQLite
  dashboard/
    app.py                     # Streamlit (lee SQLite, render)
```

## 4. Flujo de datos — DOS rutas, distinta fuente de datos (crítico)

El perfil ex-ante y el load-shift usan **datos distintos** porque tienen distinto horizonte:

**Ruta A — perfil ex-ante anual (climatología, NO forecast):**
`Open-Meteo archive` (histórico/TMY, hora-del-año esperada) → `forecast/pv` (gen esperado_h)
+ `forecast/demand` (dem esperada_i,h) → `optimize/coefficients` (β_i,h, Σ_i=1, equidad)
→ `optimize/schedule.build_ex_ante_schedule()` (día-tipo×mes × 24 h) → `store/db`.
Es el perfil que se presenta a la distribuidora (revisable ≥4 meses). El MVP "1 run" =
computar un día-tipo (unidad del perfil), con input climatológico.

**Ruta B — recomendación de desplazamiento (forecast D+1):**
`Open-Meteo forecast` (D+1) → `forecast/pv` (gen previsto_h)
→ `optimize/load_shift` (desplazar cargas flexibles granja a ventana solar prevista) → `store/db`.
Siempre legal (tras contador).

`optimize/savings` (€/hogar) → `store/db` (SQLite) → `dashboard/app` (render ambas rutas).

> `forecast/pv.py` es el mismo modelo físico (§5) — cambia solo la fuente de irradiancia
> (archive vs forecast), no la transformación.

## 5. Modelo físico FV (`forecast/pv.py`) — verificado contra teoría MUII

Físicamente trazable, no caja negra:

```
1. Open-Meteo entrega componentes de irradiancia (GHI o directa/difusa, temperatura aire).
2. Transposición a plano inclinado (POA): modelo isotrópico/Hay-Davies (MVP: simple OK).
   GTI = DNI·cosθi + DHI·transposición + GHI·ρ·(1−cosβ)/2
3. Temperatura de célula (modelo NOCT):  Tcell = Tamb + GPOA·(NOCT−20)/800
4. Potencia:  P = Pstc · (GPOA/1000) · (1 + γ_Pmp·(Tcell−25)) · (1 − L_sistema)
      γ_Pmp = −0,35 %/°C (mono-Si);  L_sistema ≈ 14 % (lumped, parametrizable por concejo)
5. Energía horaria E_h = P_h · 1h.
```

Sanity de calibración (Teverga 15 kWp, PVGIS API 2026-06-20, loss=14): Σ E ≈ 17.376 kWh/año,
YF ≈ 1.158 kWh/kWp, PR ≈ 79,5 %. Test de integración compara el total anual simulado contra
el de PVGIS (±10 %). **Ruta A usa PVGIS TMY** (SARAH2 + sombreado de horizonte DEM) como fuente
climatológica (decisión 2026-06-20, ver `docs/2026-06-20-calibration-source-discrepancy.md`) →
el test mide el MODELO, no la fuente. **Corre sobre climatología (TMY), NO forecast** — el
forecast D+1 (Open-Meteo, Ruta B) no representa el año-tipo.

## 6. Optimizador (`optimize/`) — reglas, horizonte-agnóstico, doble salida

**Núcleo `compute_coefficients(gen, demand, equity)`** — water-filling exacto para el objetivo
"maximizar tasa de autoconsumo colectivo". Para cada hora h: asignar gen_h a la demanda; en
escasez (Σ demanda > gen), prioridad por **equidad** (participantes de menor renta primero —
misión social). Devuelve β_i,h con Σ_i β_i,h = 1. Horizonte-agnóstico (1 día-tipo o 8.760 h).

**Salidas legales distintas (corrección de cadencia, ver doc legal):**

| Salida | Función | Legalidad HOY | `coefficient_mode` |
|---|---|---|---|
| Perfil ex-ante anual de coeficientes | `build_ex_ante_schedule()` ensambla día-tipo×mes × 24 h | Ex-ante, revisable **≥4 meses** (TED/1247/2021) | `ex_ante` (MVP) |
| Recomendación desplazamiento cargas flexibles | `recommend_flexible_load_shift()` | **Siempre** (tras contador) | independiente del modo |
| Recálculo dinámico día-siguiente | (stub) | NO legal hoy | `ex_post_dynamic` (forward, gated) |

`coefficient_mode` ∈ {`ex_ante`, `ex_post_dynamic`}. Solo `ex_ante` tiene lógica real en el MVP;
`ex_post_dynamic` es punto de extensión sin lógica hasta que el RD dedicado entre en vigor.

**Ahorro (`savings.py`):** autoconsumido valorado a precio minorista evitado (~0,20 €/kWh);
excedente vertido valorado a precio de compensación simplificada (bajo). No confundir ambos.
**Aviso anti-overclaim**: betas ex-ante optimizadas sobre demanda *esperada* rinden por
debajo frente a la demanda *realizada* (esa brecha es justo por qué el ex-post es "mejor").
Con datos sintéticos esperada=realizada y la brecha colapsa; anotarlo para no inflar el ahorro
cuando entren datos reales.

## 7. Modelo de datos (SQLite — simple)

- `participants` (id, concejo, perfil, renta_priority, flexible_loads)
- `forecast_runs` (run_id, fecha, concejo, coefficient_mode)
- `pv_forecast` (run_id, hour, gen_kwh)
- `demand_forecast` (run_id, participant_id, hour, dem_kwh)
- `coefficients` (run_id, participant_id, hour, beta)
- `savings` (run_id, participant_id, self_consumed_kwh, excess_kwh, eur_saved)

## 8. Config por-concejo (`config/concejos/teverga.yaml`)

Todo parametrizado: lat/lon (43,16 N; 6,09 O), tilt 35°, azimut sur, 15 kWp, losses 14 %,
NOCT, γ_Pmp, precio_retail, precio_compensacion, **proximidad_max_m: 5000** (RDL 7/2026),
lista de participantes con perfil + renta_priority + cargas flexibles. Replicar a Tineo/Cangas
= añadir un YAML, sin tocar código.

## 9. Invariantes no negociables (encoded en nombres + objetivo + tests, no en comentarios)

1. **Sinergia corregida**: objetivo = tasa de autoconsumo colectivo. `load_shift` solo mueve
   cargas **flexibles** (tanque frío, ACS limpieza) **hacia** la ventana solar. Ordeño =
   no-desplazable, sigue en red. NUNCA "casar generación con picos de ordeño".
2. **0 € licencia**: solo Python / Streamlit / Open-Meteo / SQLite. Cero SaaS de pago.
3. **Fidelidad legal 2026**: coeficientes **ex-ante** (≥4 meses); el cambio diario es forward.
   Proximidad 5 km. No overclaim de dinamismo no permitido.
4. **Por-concejo**: cero hardcode de Teverga fuera de su YAML.

## 10. Testing (TDD)

Tests por módulo. Críticos:
- Conservación de energía: Σ self_consumed ≤ Σ gen y ≤ Σ demand.
- Σ_i β_i,h = 1 ∀h.
- Equidad: en escasez, menor renta recibe ≥ que mayor renta.
- **Guard de invariante de sinergia**: `load_shift` nunca toca cargas no-flexibles (p.ej.
  ordeño) — test explícito que falla si una carga marcada no-flexible se desplaza.
- `open_meteo` mockeado (sin red en tests).
- Integración: total anual FV simulado vs PVGIS (±10 %).

## 11. Fuera de alcance MVP (YAGNI) / Fase 2

- Baterías / BESS (RDL 7/2026 ya reconoce almacenamiento distribuido como generación → caso fase 2).
- ML para forecast de demanda (v2, gated por datos reales).
- `ex_post_dynamic` real (gated al RD dedicado pendiente).
- Integración API de inversor real (MVP simula desde Open-Meteo).
- Curvas de carga reales de vecinos (dispara RGPD → hosting local).
- Modelo financiero LCOE/TIR/VAN refinado (skill `pv-valuation` cuando toque).

## 12. Stack y hosting

Python + Streamlit + Open-Meteo (API gratis) + SQLite. Hosting MVP: Streamlit Community Cloud.
**Disparador RGPD**: datos reales de consumo de personas identificables → migrar a local/Pi.
