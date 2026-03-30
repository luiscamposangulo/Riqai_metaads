# Riqai Metaads — Agente AI Media Buyer

Agente autónomo que gestiona campañas publicitarias en Meta Ads (Facebook/Instagram) mediante lenguaje natural, especializado en el sector inmobiliario.

## ¿Qué hace?

- Consulta métricas de campañas activas (CPL, CTR, frecuencia)
- Analiza rendimiento por anuncio, conjunto de anuncios y campaña
- Crea nuevas campañas y ad sets con un solo comando
- Pausa, activa y ajusta presupuestos automáticamente
- Adapta copy según ciudad o proyecto inmobiliario
- Genera reportes de gasto en tiempo real

## Stack

- **IA:** Claude Code (agente principal)
- **API:** Meta Graph API v21+
- **Scripts:** Python / Node.js
- **Auth:** Meta User Access Token (larga duración)

## Estructura

```
Riqai_metaads/
├── .claude/          → Configuración del agente (CLAUDE.md, permisos)
├── docs/decisions/   → Decisiones de arquitectura (ADRs)
├── src/              → Scripts y código fuente
├── tasks/            → Planificación y seguimiento
├── tools/            → Utilidades y helpers
└── README.md
```

## Setup

1. Crear App en developers.facebook.com (tipo: Business)
2. Configurar permisos: `ads_management`, `ads_read`, `manage_pages`
3. Generar token en Graph API Explorer
4. Copiar `.env.example` a `.env` y completar credenciales
5. Ejecutar scripts desde `src/`
