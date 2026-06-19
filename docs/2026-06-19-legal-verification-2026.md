---
type: analysis
status: verified
tags: [sreca, legal, autoconsumo, regulacion, 2026]
created: 2026-06-19
updated: 2026-06-19
related: [[PROJECT]], [[2026-06-19-sreca-design]]
---

# SRECA — Verificación del marco legal vigente (junio 2026)

Resuelve la **Open Decision #1** del handoff `~/AIOS/docs/handoffs/2026-06-19-sreca-design.md`
(PRIORITARIO: re-verificar marco legal 2026 antes de diseñar el optimizador).
Fuentes primarias: BOE + MITECO. La memoria de beca se redactó con el mapa legal de
**oct-2025** (audiencia pública); este doc lo actualiza a la realidad de **junio 2026**.

## Resumen ejecutivo

Entre oct-2025 y jun-2026 hubo cambio normativo real. Dos vías:

1. **RDL 7/2026, de 20 de marzo** (BOE-A-2026-6544) — omnibus "crisis Oriente Medio",
   convalidado por el Congreso el 26-mar-2026. **YA EN VIGOR.** Incluyó un paquete de
   medidas de autoconsumo.
2. **Proyecto de Real Decreto de modificación del autoconsumo y almacenamiento
   distribuido** — el RD dedicado (sucesor de la audiencia pública de oct-2025). **SIGUE
   EN TRAMITACIÓN** (proyecto, no aprobado). Previsión: presentación H2-2026 ("este
   verano", energias-renovables 14-abr-2026). Contiene los **coeficientes dinámicos
   ex-post**.

## Tabla de estado (lo que importa para el diseño)

| Elemento | Estado jun-2026 | Norma | Impacto en SRECA |
|---|---|---|---|
| Coeficientes de reparto **variables horarios ex-ante** | **EN VIGOR** | Orden TED/1247/2021 (BOE-A-2021-18706) | **Es la ley vigente → es el target del optimizador MVP** |
| Proximidad **5 km** (antes 2 km / 500 m) | **EN VIGOR** | RDL 7/2026 | Disuelve la debilidad del Bloque 1.1 (aldeas dispersas de Teverga ahora agrupables sin clusterizar) |
| Figura **"Gestor de autoconsumo"** (Ley Sector Eléctrico) | **EN VIGOR** | RDL 7/2026 | SRECA = la herramienta software que usa el gestor. Hook narrativo para la beca |
| **Almacenamiento distribuido = instalación de generación** (baterías compartidas) | **EN VIGOR** | RDL 7/2026 | Refuerza el caso "batería en fase 2" |
| Compatibilidad de modalidades de autoconsumo | **EN VIGOR** | RDL 7/2026 | Más flexibilidad de diseño de la CEL |
| 10 % capacidad liberada en nudos saturados para estas instalaciones | **EN VIGOR** | RDL 7/2026 | Acceso a red más fácil |
| Nuevas competencias municipales en promoción de CEs | **EN VIGOR** | RDL 7/2026 | Vía de colaboración con el Ayto. de Teverga |
| **Coeficientes dinámicos ex-post** | **PENDIENTE** (proyecto de RD) | Proyecto RD autoconsumo (MITECO) | NO target MVP. Modo forward-compatible |
| Modificación **mensual** de coeficientes (hoy: ≥4 meses entre cambios) | **PENDIENTE** (en el proyecto de RD) | Proyecto RD autoconsumo | Simplificación futura |
| **Cadencia de modificación del perfil de coeficientes** | **≥4 meses** entre modificaciones (EN VIGOR) | Orden TED/1247/2021 (Anexo I) | **CRÍTICO de diseño** — ver abajo. NO se pueden cambiar coeficientes a diario hoy |

## Hallazgo crítico de cadencia (verificación MUII-energía 2026-06-19)

Bajo la **Orden TED/1247/2021** los 8.760 coeficientes horarios se definen **ex-ante en una
única presentación anual** (pueden codificar variación estacional/mensual/horaria completa),
pero el perfil presentado **solo se puede modificar con periodicidad mínima de 4 meses**
(excepción: ventana de adaptación de los primeros 4 meses para quien lo implementa por 1ª vez).

**Consecuencia (corrige el encuadre del optimizador):** SRECA **no puede cambiar a diario los
coeficientes presentados** bajo la ley vigente. Lo legalmente entregable y valioso HOY es:

1. **Perfil ex-ante anual óptimo** (8.760 betas, representable como día-tipo×mes × 24 h):
   el optimizador lo calcula desde previsiones/históricos típicos. Es el producto que la CEL
   presenta a la distribuidora (revisable ≥4 meses). Modo `ex_ante`.
2. **Recomendación de desplazamiento de cargas flexibles** (tanque frío, ACS limpieza →
   ventana solar): **siempre legal, sin cambio de coeficientes** (comportamiento tras
   contador). Es la palanca operativa día-a-día inmediata. Modo siempre activo.
3. El **recálculo día-siguiente / dinámico de coeficientes** es modo **forward** (`ex_post_dynamic`),
   gated al RD dedicado pendiente (o a la futura modificación mensual).

Esto evita un overclaim que un evaluador técnico cazaría (misma clase de error que la sinergia
del ordeño y el ex-ante/ex-post). La memoria de beca dice "calcula con un día de antelación los
coeficientes" → matizar a: calcula día-a-día las **recomendaciones de desplazamiento**; el
**perfil de coeficientes** es el plan ex-ante anual optimizado.

Fuente: Orden TED/1247/2021 (BOE-A-2021-18706), Anexo I — periodicidad mínima de modificación
de 4 meses.

## Consecuencia de ingeniería (decisión de diseño)

**El optimizador MVP calcula coeficientes de reparto variables horarios EX-ANTE
(día-siguiente)** — es el régimen legal vigente en junio 2026 (Orden TED/1247/2021).

Se introduce una abstracción `coefficient_mode` con dos valores:
- `ex_ante_day_ahead` (MVP, ley vigente) — coeficientes 24h calculados con previsión D-1.
- `ex_post_dynamic` (forward-compatible, **gated**) — se activa cuando el RD dedicado
  entre en vigor. No se construye lógica ex-post real hasta entonces; solo el punto de
  extensión.

Esto hace el diseño robusto a la incertidumbre residual: que el RD dedicado se apruebe en
julio o en diciembre **no cambia el MVP**.

## Deltas para la memoria de beca (flag a Pablo — NO reescribir este sesión)

La memoria de beca (`~/.claude/plans/estoy-pensando-en-ideas-stateful-cascade.md`) tiene
afirmaciones legales que conviene actualizar antes de la entrega:

1. **Proximidad 2 km → 5 km** (Bloque 1.1, Resumen). RDL 7/2026 amplió a 5 km. Esto
   *fortalece* el argumento de aldeas dispersas (ya no hay que clusterizar tanto).
2. **Añadir figura "gestor de autoconsumo"** (RDL 7/2026): SRECA es la herramienta del
   gestor. Encaja con el rol de FAEN/OTC como gestor de las CELs.
3. **"alineado con hacia dónde va la regulación"** → ahora más fuerte y verificable: el
   proyecto de RD con coef. dinámicos ex-post está en tramitación; SRECA queda *listo*
   para activarlos el día que entren en vigor (`coefficient_mode=ex_post_dynamic`).
4. **Almacenamiento distribuido reconocido como generación** (RDL 7/2026) refuerza el
   argumento de "batería en fase 2".
5. Mantener la corrección de sinergia (ordeño fuera de campana solar) — no afectada por
   el cambio legal.

## Fuentes (jun-2026)

- BOE-A-2026-6544 — Real Decreto-ley 7/2026, de 20 de marzo (preámbulo: 5 km, gestor de
  autoconsumo, almacenamiento distribuido como generación, compatibilidad de modalidades,
  10 % capacidad, competencias municipales). Verificado vía BOE.
- BOE-A-2021-18706 — Orden TED/1247/2021 (coeficientes variables horarios ex-ante).
- MITECO — Proyecto de Real Decreto de modificación del autoconsumo y almacenamiento
  distribuido (en tramitación; coeficientes dinámicos ex-post; modificación mensual).
- energias-renovables.com (14-abr-2026) — el RD dedicado "podría presentarse este verano".
- IDAE — CE IMPLEMENTA: 6 convocatorias cerradas, 262 CEs creadas (159 en municipios de
  reto demográfico, 7 en transición justa). 2ª convocatoria OTC (10 M€, vía RDL 7/2026,
  objetivo CID 35: energías limpias en municipios <5.000 hab → encaje Teverga).

> Nota: los resúmenes de buscador mezclaban RDL 7/2026 con el proyecto de RD dedicado.
> La distinción confirmada con el preámbulo del BOE es: **ex-post NO está en RDL 7/2026**;
> sigue en el proyecto de RD pendiente.
