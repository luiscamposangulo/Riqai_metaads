"""
Identifica los mejores y peores anuncios de la cuenta según métricas clave.
Muestra CPL, CTR, gasto y leads por anuncio en un ranking ordenado.

Uso:
    # Ranking de todos los anuncios, últimos 7 días
    python src/ads/list_ads.py

    # Últimos 30 días
    python src/ads/list_ads.py --periodo 30d

    # Rango de fechas personalizado
    python src/ads/list_ads.py --desde 2026-03-01 --hasta 2026-03-31

    # Solo anuncios de un ad set específico
    python src/ads/list_ads.py --adset_id 120235973127950109

    # Solo los 5 mejores y 5 peores
    python src/ads/list_ads.py --top 5
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.utils.meta_utils import obtener_moneda_cuenta

load_dotenv()

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID")
BASE_URL = "https://graph.facebook.com/v25.0"

CAMPOS_ADS = "id,name,status,effective_status,adset_id,adset_name,campaign_id,campaign_name,creative{id,name,object_type}"
CAMPOS_INSIGHTS = "impressions,clicks,spend,actions,ctr,cpc"


def calcular_fechas(periodo=None, desde=None, hasta=None):
    """Calcula el rango de fechas para la consulta."""
    hoy = datetime.today().date()
    if desde and hasta:
        return desde, hasta
    dias = int(periodo.replace("d", "")) if periodo else 7
    return str(hoy - timedelta(days=dias)), str(hoy)


def extraer_resultados(actions):
    """Extrae el resultado principal según el objetivo de la campaña."""
    if not actions:
        return 0, "sin resultados"

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


def obtener_ads(adset_id=None):
    """
    Obtiene todos los anuncios activos/pausados de la cuenta o de un ad set.

    Returns:
        Lista de anuncios o None si hubo error.
    """
    url = f"{BASE_URL}/{AD_ACCOUNT_ID}/ads"
    params = {
        "access_token": ACCESS_TOKEN,
        "fields": CAMPOS_ADS,
        "effective_status": '["ACTIVE","PAUSED","CAMPAIGN_PAUSED","ADSET_PAUSED"]',
        "limit": 100,
    }

    if adset_id:
        params["filtering"] = f'[{{"field":"adset.id","operator":"EQUAL","value":"{adset_id}"}}]'

    todos = []
    while url:
        data = requests.get(url, params=params).json()
        if "error" in data:
            print(f"❌ Error de API: {data['error']['message']}")
            return None
        todos.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")
        params = {}

    return todos


def obtener_todos_insights(fecha_inicio, fecha_fin, adset_id=None):
    """
    Obtiene insights de todos los anuncios en una sola llamada a la API.

    Returns:
        Dict indexado por ad_id para lookup O(1), o None si hubo error.
    """
    url = f"{BASE_URL}/{AD_ACCOUNT_ID}/insights"
    params = {
        "access_token": ACCESS_TOKEN,
        "level": "ad",
        "fields": CAMPOS_INSIGHTS,
        "time_range": f'{{"since":"{fecha_inicio}","until":"{fecha_fin}"}}',
        "limit": 500,
    }

    if adset_id:
        params["filtering"] = f'[{{"field":"adset.id","operator":"EQUAL","value":"{adset_id}"}}]'

    todos = []
    while url:
        data = requests.get(url, params=params).json()
        if "error" in data:
            print(f"❌ Error al obtener insights: {data['error']['message']}")
            return None
        todos.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")
        params = {}

    return {item["ad_id"]: item for item in todos}


def construir_ranking(ads, insights_por_id):
    """
    Cruza los anuncios con su insights (ya precargados) y construye el ranking.

    Returns:
        Lista de anuncios con métricas, ordenada por CPL ascendente (mejor primero).
        Los anuncios sin leads van al final ordenados por gasto descendente.
    """
    enriquecidos = []

    for ad in ads:
        insights = insights_por_id.get(ad["id"])

        if not insights:
            continue  # Sin actividad en el período — omitir del ranking

        gasto = float(insights.get("spend", 0))
        if gasto == 0:
            continue  # Sin gasto — no aporta al ranking

        resultados, etiqueta = extraer_resultados(insights.get("actions"))
        cpr = gasto / resultados if resultados > 0 else None
        ctr = float(insights.get("ctr", 0))
        cpc = float(insights.get("cpc", 0))
        clics = int(insights.get("clicks", 0))
        impresiones = int(insights.get("impressions", 0))

        enriquecidos.append({
            "id": ad["id"],
            "nombre": ad["name"],
            "estado": ad["status"],
            "effective_status": ad.get("effective_status", ad["status"]),
            "adset": ad.get("adset_name", ad.get("adset_id", "N/A")),
            "campania": ad.get("campaign_name", ad.get("campaign_id", "N/A")),
            "tipo_creative": ad.get("creative", {}).get("object_type", "N/A"),
            "gasto": gasto,
            "resultados": resultados,
            "etiqueta": etiqueta,
            "cpr": cpr,
            "ctr": ctr,
            "cpc": cpc,
            "clics": clics,
            "impresiones": impresiones,
        })

    # Ordenar: con leads primero (por CPL asc), sin leads al final (por gasto desc)
    con_resultados = sorted([a for a in enriquecidos if a["cpr"] is not None], key=lambda x: x["cpr"])
    sin_resultados = sorted([a for a in enriquecidos if a["cpr"] is None], key=lambda x: x["gasto"], reverse=True)

    return con_resultados + sin_resultados


def imprimir_ranking(ranking, simbolo, top=None):
    """Imprime el ranking de mejores y peores anuncios."""
    if not ranking:
        print("\n⚠️  No hay anuncios con actividad en el período seleccionado.")
        return

    con_resultados = [a for a in ranking if a["cpr"] is not None]
    sin_resultados = [a for a in ranking if a["cpr"] is None]

    ESTADO_ICONS = {
        "ACTIVE": "🟢 ACTIVO",
        "PAUSED": "⏸️  PAUSADO",
        "CAMPAIGN_PAUSED": "🟡 CAMPAÑA PAUSADA",
        "ADSET_PAUSED": "🟠 AD SET PAUSADO",
    }

    def imprimir_ad(ad, posicion, etiqueta=""):
        estado_label = ESTADO_ICONS.get(ad["effective_status"], ad["effective_status"])
        print(f"\n  #{posicion} {etiqueta}{ad['nombre']}")
        print(f"      Estado:      {estado_label}")
        print(f"      ID:          {ad['id']}")
        print(f"      Ad Set:      {ad['adset']}")
        print(f"      Campaña:     {ad['campania']}")
        print(f"      Tipo:        {ad['tipo_creative']}")
        print(f"      Gasto:       {simbolo} {ad['gasto']:.2f}")
        print(f"      Impresiones: {ad['impresiones']:,}")
        print(f"      Clics:       {ad['clics']:,}  |  CTR: {ad['ctr']:.2f}%")
        print(f"      CPC:         {simbolo} {ad['cpc']:.2f}")
        if ad["resultados"] > 0:
            print(f"      {ad['etiqueta']}:{' ' * (12 - len(ad['etiqueta']))}{ad['resultados']}  |  Costo/result: {simbolo} {ad['cpr']:.2f}")
        else:
            print(f"      Resultados:  0  |  Sin resultados en el período")

    # --- MEJORES (menor costo por resultado) ---
    if con_resultados:
        limite = top if top else len(con_resultados)
        mejores = con_resultados[:limite]
        print(f"\n{'=' * 65}")
        print(f"  🏆 MEJORES ANUNCIOS por costo/resultado ({len(mejores)} de {len(con_resultados)})")
        print(f"{'=' * 65}")
        for i, ad in enumerate(mejores, 1):
            imprimir_ad(ad, i)
            print(f"  {'-' * 63}")

    # --- PEORES (mayor costo por resultado) ---
    # Solo tiene sentido mostrarlos si hay más anuncios que el límite --top
    if con_resultados and top and len(con_resultados) > top:
        limite = top
        peores = list(reversed(con_resultados))[:limite]
        print(f"\n{'=' * 65}")
        print(f"  ⚠️  PEORES ANUNCIOS por costo/resultado ({len(peores)} mostrados)")
        print(f"{'=' * 65}")
        for i, ad in enumerate(peores, 1):
            imprimir_ad(ad, i)
            print(f"  {'-' * 63}")

    # --- SIN RESULTADOS ---
    if sin_resultados:
        limite = top if top else len(sin_resultados)
        print(f"\n{'=' * 65}")
        print(f"  📭 SIN RESULTADOS en el período ({len(sin_resultados)} anuncios, ordenados por gasto)")
        print(f"{'=' * 65}")
        for i, ad in enumerate(sin_resultados[:limite], 1):
            imprimir_ad(ad, i)
            print(f"  {'-' * 63}")

    # --- RESUMEN ---
    gasto_total = sum(a["gasto"] for a in ranking)
    resultados_total = sum(a["resultados"] for a in ranking)
    cpr_promedio = gasto_total / resultados_total if resultados_total > 0 else 0

    print(f"\n{'=' * 65}")
    print(f"  📊 RESUMEN")
    print(f"     Anuncios con actividad:  {len(ranking)}")
    print(f"     Gasto total:             {simbolo} {gasto_total:.2f}")
    print(f"     Resultados totales:      {resultados_total}")
    print(f"     Costo/result promedio:   {simbolo} {cpr_promedio:.2f}" if resultados_total > 0 else "     Costo/result promedio:   Sin resultados")
    print(f"{'=' * 65}\n")


def main():
    parser = argparse.ArgumentParser(description="Ranking de mejores y peores anuncios")
    parser.add_argument("--adset_id", help="Filtrar por ad set específico")
    parser.add_argument("--periodo", default="7d", help="Período: 7d, 14d, 30d (default: 7d)")
    parser.add_argument("--desde", help="Fecha inicio YYYY-MM-DD")
    parser.add_argument("--hasta", help="Fecha fin YYYY-MM-DD")
    parser.add_argument("--top", type=int, help="Mostrar solo los N mejores y N peores")
    args = parser.parse_args()

    if not ACCESS_TOKEN or not AD_ACCOUNT_ID:
        print("❌ Faltan credenciales en .env")
        sys.exit(1)

    if bool(args.desde) != bool(args.hasta):
        print("❌ Debes indicar --desde y --hasta juntos.")
        sys.exit(1)

    fecha_inicio, fecha_fin = calcular_fechas(args.periodo, args.desde, args.hasta)
    simbolo = obtener_moneda_cuenta()

    print(f"\n📊 Ranking de anuncios — {fecha_inicio} al {fecha_fin}")
    if args.adset_id:
        print(f"   Filtrando por Ad Set: {args.adset_id}")

    ads = obtener_ads(adset_id=args.adset_id)
    if ads is None:
        sys.exit(1)

    if not ads:
        print("⚠️  No se encontraron anuncios en la cuenta.")
        sys.exit(0)

    print(f"   Anuncios encontrados: {len(ads)}")
    print(f"   Obteniendo métricas...", end="", flush=True)

    insights_por_id = obtener_todos_insights(fecha_inicio, fecha_fin, adset_id=args.adset_id)
    if insights_por_id is None:
        sys.exit(1)

    print(" listo.")

    ranking = construir_ranking(ads, insights_por_id)
    imprimir_ranking(ranking, simbolo, top=args.top)


if __name__ == "__main__":
    main()
