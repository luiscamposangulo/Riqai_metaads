# Plan de Tareas — Riqai Metaads

## Estado actual
- [x] Estructura del proyecto creada
- [ ] Setup Meta App y obtención de token
- [ ] Configuración de variables de entorno
- [ ] Primer script de conexión a la API

---

## Fase 1 — Setup y Conexión (Prioridad Alta)

- [ ] Crear App en Meta for Developers
- [ ] Configurar permisos requeridos (ads_management, ads_read, manage_pages)
- [ ] Subir política de privacidad (para modo Live)
- [ ] Generar User Access Token de larga duración
- [ ] Crear `.env` con credenciales
- [ ] Verificar conexión con script de prueba (`src/test_connection.py`)

## Fase 2 — Lectura de Datos

- [ ] Script para listar campañas activas
- [ ] Script para obtener métricas por campaña (CPL, CTR, gasto)
- [ ] Script para desglose por país/ciudad
- [ ] Script para identificar mejores y peores anuncios

## Fase 3 — Escritura y Gestión

- [ ] Script para pausar/activar anuncios
- [ ] Script para modificar presupuesto diario
- [ ] Script para crear nueva campaña
- [ ] Script para crear ad sets con segmentación geográfica

## Fase 4 — Agente Completo

- [ ] Definir comandos en lenguaje natural
- [ ] Integrar análisis + acción en flujo único
- [ ] Generar reportes automáticos
- [ ] Adaptar copy por proyecto inmobiliario

---

## Backlog

- Integración con Notion para reportes
- Alertas automáticas si CPL supera umbral
- Dashboard de métricas en tiempo real
