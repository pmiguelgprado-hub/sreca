---
type: reference
status: verified
tags: [sreca, datos, oficiales, ine, pvpc, caja-rural, demografia]
created: 2026-06-22
related: [PROJECT.md, config/concejos/teverga.yaml, config/concejos/somiedo.yaml]
---

# SRECA — Fuentes de datos oficiales (verificación 2026-06-22)

Registra la procedencia de las cifras públicas que alimentan la app, verificadas **en
fuente** (no en resúmenes de buscador). Misma ética de fidelidad que el resto del proyecto:
no se inventa un dato público y se documenta de dónde sale.

## 1. Demografía — INE, Padrón Municipal (cifras oficiales a 1-ene)

Verificado **directamente contra la fuente** (API tempus3 del INE, tabla 2886
`Población por municipios y sexo`), no contra terceros. Los resúmenes de buscador discrepaban
(asturias.com daba 1.565 / 1.083; eran cifras antiguas), así que se fue al origen:

```
GET https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/2886?nult=2&det=2
```

| Concejo | Población 2025 | Población 2024 | Δ interanual | Superficie | Densidad |
|---|---|---|---|---|---|
| **Teverga** | **1.495** | 1.539 | −2,9 % | 168,71 km² | ≈ 8,9 hab/km² |
| **Somiedo** | **1.031** | 1.065 | −3,2 % | 291,38 km² | ≈ 3,5 hab/km² |

Contexto de despoblación (refuerza la tesis, no entra en la app como serie): Somiedo registraba
5.558 hab en 1940 → −70 % en 85 años; es el 2.º concejo de menor densidad de Asturias. Ambos
concejos están **muy por debajo de 5.000 hab** → banda de *municipios de reto demográfico* que
es justo el objetivo de CE IMPLEMENTA (IDAE) y del "impulso demográfico" de Caja Rural.

- `population` / `population_year` / `area_km2` viven en cada YAML de concejo. La **densidad se
  deriva** (`ConcejoConfig.density_hab_km2 = población / superficie`); nunca se duplica el dato.
- Somiedo tenía la población deliberadamente en blanco ("no se inventa un dato público") hasta
  esta verificación en fuente; ahora se rellena con la cifra oficial.

## 2. Precios de electricidad — PVPC 2026 (conservadores, anti-overclaim)

| Parámetro | Valor en config | Realidad jun-2026 | Por qué este valor |
|---|---|---|---|
| `retail_eur_kwh` | 0,20 | PVPC ~0,16–0,22 €/kWh | coste evitado del kWh autoconsumido; punto medio del rango |
| `compensation_eur_kwh` | 0,06 | excedente PVPC ~0,06–0,10 €/kWh | extremo **conservador** para no inflar el ahorro |

- Compensación de excedentes = mecanismo simplificado del **RD 244/2019**; desde 2026 la PVPC
  se factura en tramos **cuarto-horarios** (96 precios/día), de modo que el precio del excedente
  varía hora a hora (el 20-jun-2026 la media diaria fue ~0,065 €/kWh; el 22-jun ~0,099 €/kWh).
- **No se fija una "media anual" inventada** desde una página diaria: sería falsa precisión.
  Se elige el extremo conservador del rango observado. Esto es coherente con el aviso
  anti-overclaim de la spec §6 (la demanda esperada rinde por debajo de la realizada): el
  proyecto prefiere subestimar el ahorro a inflarlo.
- Fuente del rango: REE/ESIOS (precio horario PVPC y excedentes), observado vía tarifasgasluz
  (jun-2026). Los precios son **parametrizables por concejo**; cualquier CEL fija los suyos.

## 3. Fundación Caja Rural de Asturias — qué busca (contexto de la beca)

De `fundacioncajaruraldeasturias.com/innovacion-y-talento` y sus convocatorias públicas
(jun-2026):

- **Becas de Excelencia** (programa "Innovación y talento"): 100×1.000 € (grado/máster),
  40×1.000 € (FP superior), 8×5.000 € (máster en España), 2×10.000 € (máster en el mundo).
  Criterio declarado: **"premiar la excelencia"** → son becas de **mérito académico**.
- **Premio Talento en la Ingeniería**: desarrollado **con la Escuela Politécnica de Ingeniería
  de Gijón (EPI)** — la facultad de Pablo. Reconoce trayectoria/proyección profesional en
  ingeniería vinculada a Asturias.
- **"Imagina tu empresa en Asturias"**: programa empresarial; incluye **"impulso demográfico"**
  entre sus objetivos (una beca empresarial de 6.000 € cerraba el 22-jun-2026).
- Línea editorial repetida: *"proyectos que conectan tecnología, sostenibilidad y territorio"*,
  *"vocación innovadora, compromiso con su entorno, potencial de impacto"*. SRECA encaja de
  lleno: tecnología (cerebro software 0 €) + sostenibilidad (FV) + territorio (concejo rural) +
  impacto (reto demográfico + pobreza energética).

> **Punto de orientación para Pablo (no bloquea el desarrollo):** las *Becas de Excelencia*
> leídas como están son premios de **mérito académico**, no convocatorias de *presentación de
> proyecto*. Los programas con encaje de proyecto son los empresariales ("Imagina tu empresa")
> y el Premio Talento (trayectoria profesional, no estudiante). Conviene confirmar a qué
> convocatoria concreta se presenta SRECA antes de calibrar la narrativa de la memoria. El
> trabajo de app/datos vale bajo cualquier lectura.

## 4. Decisión — perfiles de demanda REE diferidos a fase 2

Las curvas de consumo siguen siendo **sintéticas** (marcadas como ilustrativas en la app). REE
publica perfiles de consumo residencial **oficiales, gratuitos y agregados** (no disparan RGPD)
que podrían parametrizar esas curvas. **Decisión:** se difiere a fase 2.

- *Por qué no ahora:* esta pasada es de pulido con datos oficiales puntuales (demografía,
  precios); sustituir el modelo de demanda por perfiles REE es un cambio de modelo (re-calibrar
  los perfiles `residencial_mayor_diurno` / `ganadero_lacteo`, nuevos tests de forma de curva),
  no un cambio de dato. La demanda ya está honestamente etiquetada como sintética.
- *Por qué merece la pena después:* es una palanca legítima de "datos oficiales" que reduce el
  carácter sintético sin tocar RGPD. Candidato claro de fase 2 junto al ML de demanda (que sí
  está gated por datos reales de los vecinos).
