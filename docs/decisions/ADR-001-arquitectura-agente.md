# ADR-001 — Arquitectura del Agente Media Buyer

**Fecha:** 2026-03-25
**Estado:** Aceptado

---

## Contexto

Se necesita un sistema que permita gestionar campañas de Meta Ads para inmobiliarias mediante lenguaje natural, sin entrar al Ads Manager de Facebook. El agente debe poder leer métricas, crear campañas y ejecutar cambios operativos de forma autónoma.

## Decisión

### Interfaz
- Claude Code como cerebro del agente (terminal de comandos)
- Interacción en lenguaje natural desde la terminal

### Backend
- Scripts en **Python** para consumir la Meta Graph API
- Autenticación mediante User Access Token de larga duración
- Variables de entorno para todas las credenciales (`.env`)

### Flujo de datos
1. Usuario da instrucción en lenguaje natural
2. Claude interpreta y llama al script correspondiente en `src/`
3. Script consulta o escribe en Meta Graph API
4. Respuesta JSON es analizada por Claude
5. Claude presenta resultado y sugiere siguiente acción

### Estructura de scripts
- `src/campaigns/` — lectura y creación de campañas
- `src/adsets/` — gestión de conjuntos de anuncios
- `src/ads/` — gestión de anuncios individuales
- `src/reports/` — generación de reportes y métricas

## Alternativas consideradas

| Alternativa | Razón de rechazo |
|-------------|-----------------|
| SDK oficial de Python de Meta | Usar Graph API directamente da más control y flexibilidad |
| Node.js como lenguaje principal | Python tiene mejor ecosistema para análisis de datos |
| Dashboard web | Fuera del alcance del MVP; la terminal es suficiente |

## Consecuencias

- El agente depende de un token válido (requiere renovación periódica)
- Las acciones son irreversibles en Meta (pausar/eliminar campañas)
- Siempre se debe validar antes de ejecutar cambios en cuentas reales
