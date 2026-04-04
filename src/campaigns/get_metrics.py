"""
Obtiene métricas (insights) de campañas de Meta Ads.
Muestra impresiones, clics, leads, gasto, CPL y CTR.

Uso:
    # Todas las campañas, últimos 7 días
    python src/campaigns/get_metrics.py

    # Últimos 30 días
    python src/campaigns/get_metrics.py --periodo 30d

    # Rango de fechas personalizado
    python src/campaigns/get_metrics.py --desde 2026-03-01 --hasta 2026-03-31

    # Una campaña específica
    python src/campaigns/get_metrics.py --id 120201234567890
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID")
BASE_URL = "https://graph.facebook.com/v21.0"

CAMPOS_INSIGHTS = "impressions,clicks,spend,actions,ctr,cpc,cpp,reach,frequency"


def obtener_moneda_cuenta():
    """Consulta la moneda configurada en la cuenta publicitaria."""
    SIMBOLOS = {
        "USD": "$", "PEN": "S/", "MXN": "MX$", "COP": "COP$",
        "ARS": "AR$", "CLP": "CLP$", "EUR": "€", "BRL": "R$",
    }
    url = f"{BASE_URL}/{AD_ACCOUNT_ID}"
    params = {"access_token": ACCESS_TOKEN, "fields": "currency"}
    data = requests.get(url, params=params).json()
    codigo = data.get("currency", "USD")
    return SIMBOLOS.get(codigo, codigo)


def calcular_fechas(periodo=None, desde=None, hasta=None):
    """
    Calcula el rango de fechas para la consulta.

    Returns:
        Tuple (fecha_inicio, fecha_fin) en formato 'YYYY-MM-DD'.
    """
    hoy = datetime.today().date()

    if desde and hasta:
        return desde, hasta

    dias = int(periodo.replace("d", "")) if periodo else 7
    inicio = hoy - timedelta(days=dias)
    return str(inicio), str(hoy)


def extraer_resultados(actions):
    """
    Extrae el número de resultados principales según el objetivo de la campaña.
    Cubre distintos tipos: formulario de leads, mensajería, etc.
    """
    if not actions:
        return 0, "sin resultados"

    # Orden de prioridad explícito: Meta usa estos como resultado oficial según el objetivo
    PRIORIDAD = [
        ("lead", "Leads"),
        ("onsite_conversion.lead_grouped", "Leads"),
        ("onsite_conversion.messaging_conversation_started_7d", "Conversaciones iniciadas"),
        ("onsite_conversion.total_messaging_connection", "Mensajes"),
        ("onsite_conversion.messaging_first_reply", "Primeras respuestas"),
    ]

    acciones_por_tipo = {a.get("action_type"): a.get("value", 0) for a in actions}

    for tipo, etiqueta in PRIORIDAD:
        if tipo in acciones_por_tipo:
            return int(acciones_por_tipo[tipo]), etiqueta

    return 0, "sin resultados"


def obtener_insights_campania(campaign_id, fecha_inicio, fecha_fin):
    """
    Obtiene los insights de una campaña en un rango de fechas.

    Returns:
        Dict con métricas o None si hubo error.
    """
    url = f"{BASE_URL}/{campaign_id}/insights"
    params = {
        "access_token": ACCESS_TOKEN,
        "fields": CAMPOS_INSIGHTS,
        "time_range": f'{{"since":"{fecha_inicio}","until":"{fecha_fin}"}}',
        "level": "campaign",
    }
    response = requests.get(url, params=params)
    data = response.json()

    if "error" in data:
        return {"error": data["error"]["message"]}

    resultados = data.get("data", [])
    return resultados[0] if resultados else None


def obtener_campanias_activas():
    """Obtiene lista de campañas con ID y nombre para iterar."""
    url = f"{BASE_URL}/{AD_ACCOUNT_ID}/campaigns"
    params = {
        "access_token": ACCESS_TOKEN,
        "fields": "id,name,status",
        "effective_status": '["ACTIVE","PAUSED"]',
        "limit": 100,
    }
    todas = []
    while url:
        data = requests.get(url, params=params).json()
        if "error" in data:
            print(f"❌ Error al obtener campañas: {data['error']['message']}")
            return None
        todas.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")
        params = {}
    return todas


def imprimir_metricas(nombre, estado, metricas, simbolo):
    """Imprime las métricas de una campaña en formato legible."""
    estado_icon = "🟢" if estado == "ACTIVE" else "⏸️ "

    if metricas is None:
        print(f"{estado_icon} {nombre}")
        print(f"   ⚠️  Sin datos en el período seleccionado.")
        print("-" * 65)
        return

    if "error" in metricas:
        print(f"{estado_icon} {nombre}")
        print(f"   ❌ Error: {metricas['error']}")
        print("-" * 65)
        return

    gasto = float(metricas.get("spend", 0))
    impresiones = int(metricas.get("impressions", 0))
    clics = int(metricas.get("clicks", 0))
    alcance = int(metricas.get("reach", 0))
    frecuencia = float(metricas.get("frequency", 0))
    ctr = float(metricas.get("ctr", 0))
    cpc = float(metricas.get("cpc", 0))
    resultados, etiqueta = extraer_resultados(metricas.get("actions"))
    cpr = (gasto / resultados) if resultados > 0 else 0

    print(f"{estado_icon} {nombre}")
    print(f"   Gasto:        {simbolo} {gasto:.2f}")
    print(f"   Impresiones:  {impresiones:,}")
    print(f"   Alcance:      {alcance:,}")
    print(f"   Frecuencia:   {frecuencia:.2f}")
    print(f"   Clics:        {clics:,}")
    print(f"   CTR:          {ctr:.2f}%")
    print(f"   CPC:          {simbolo} {cpc:.2f}")
    print(f"   {etiqueta}:{' ' * (13 - len(etiqueta))}{resultados:,}")
    print(f"   Costo/result: {simbolo} {cpr:.2f}" if resultados > 0 else "   Costo/result: Sin resultados aún")
    print("-" * 65)


def main():
    parser = argparse.ArgumentParser(description="Métricas de campañas de Meta Ads")
    parser.add_argument("--id", help="ID de una campaña específica")
    parser.add_argument("--periodo", default="7d", help="Período: 7d, 14d, 30d (default: 7d)")
    parser.add_argument("--desde", help="Fecha inicio en formato YYYY-MM-DD")
    parser.add_argument("--hasta", help="Fecha fin en formato YYYY-MM-DD")
    args = parser.parse_args()

    if not ACCESS_TOKEN or not AD_ACCOUNT_ID:
        print("❌ Faltan credenciales en .env")
        sys.exit(1)

    # Validar que si usa fechas custom, ambas estén presentes
    if bool(args.desde) != bool(args.hasta):
        print("❌ Debes indicar --desde y --hasta juntos.")
        sys.exit(1)

    fecha_inicio, fecha_fin = calcular_fechas(args.periodo, args.desde, args.hasta)
    simbolo = obtener_moneda_cuenta()

    print(f"📊 Métricas del {fecha_inicio} al {fecha_fin}\n")
    print("=" * 65)

    if args.id:
        # Métrica de una campaña específica
        metricas = obtener_insights_campania(args.id, fecha_inicio, fecha_fin)
        imprimir_metricas(f"Campaña {args.id}", "ACTIVE", metricas, simbolo)
    else:
        # Métricas de todas las campañas activas/pausadas
        campanias = obtener_campanias_activas()
        if campanias is None:
            sys.exit(1)

        for c in campanias:
            metricas = obtener_insights_campania(c["id"], fecha_inicio, fecha_fin)
            imprimir_metricas(c["name"], c["status"], metricas, simbolo)


if __name__ == "__main__":
    main()
