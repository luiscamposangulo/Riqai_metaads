"""
Lista los Ad Sets (conjuntos de anuncios) de una campaña o de toda la cuenta.
Muestra ID, nombre, estado, presupuesto, segmentación y estrategia de puja.

Uso:
    # Todos los ad sets de la cuenta
    python src/adsets/list_adsets.py

    # Ad sets de una campaña específica
    python src/adsets/list_adsets.py --campaign_id 120201234567890

    # Filtrar por estado
    python src/adsets/list_adsets.py --status ACTIVE
    python src/adsets/list_adsets.py --campaign_id 120201234567890 --status PAUSED
"""

import os
import sys
import argparse
from pathlib import Path
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.utils.meta_utils import obtener_moneda_cuenta

load_dotenv()

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID")
BASE_URL = "https://graph.facebook.com/v25.0"

_cache_geocodificacion = {}

CAMPOS = (
    "id,name,status,daily_budget,lifetime_budget,"
    "bid_strategy,bid_amount,optimization_goal,"
    "targeting,start_time,end_time,campaign_id"
)


def obtener_adsets(campaign_id=None, filtro_estado=None):
    """
    Obtiene ad sets de una campaña o de toda la cuenta.

    Args:
        campaign_id: ID de campaña específica o None para toda la cuenta.
        filtro_estado: 'ACTIVE', 'PAUSED', 'ARCHIVED' o None para todos.

    Returns:
        Lista de ad sets o None si hubo error.
    """
    url = f"{BASE_URL}/{AD_ACCOUNT_ID}/adsets"

    params = {
        "access_token": ACCESS_TOKEN,
        "fields": CAMPOS,
        "limit": 100,
    }

    if filtro_estado:
        params["effective_status"] = f'["{filtro_estado}"]'

    # Filtrar por campaña usando filtering en lugar del edge directo
    if campaign_id:
        params["filtering"] = f'[{{"field":"campaign.id","operator":"EQUAL","value":"{campaign_id}"}}]'

    todos = []

    while url:
        response = requests.get(url, params=params)
        data = response.json()

        if "error" in data:
            print(f"❌ Error de API: {data['error']['message']}")
            print(f"   Código: {data['error']['code']}")
            return None

        todos.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")
        params = {}

    return todos


def formatear_segmentacion(targeting):
    """Extrae los datos clave de segmentación en formato legible."""
    if not targeting:
        return "N/A"

    lineas = []

    # Edades
    edad_min = targeting.get("age_min")
    edad_max = targeting.get("age_max")
    if edad_min or edad_max:
        lineas.append(f"Edad: {edad_min or '?'}-{edad_max or '?'}")

    # Géneros: 1=hombre, 2=mujer, ausente=todos
    generos = targeting.get("genders", [])
    if generos == [1]:
        lineas.append("Género: Hombres")
    elif generos == [2]:
        lineas.append("Género: Mujeres")
    else:
        lineas.append("Género: Todos")

    # Ubicaciones geográficas — maneja objetos y strings
    geo = targeting.get("geo_locations", {})
    ciudades = geo.get("cities", [])
    regiones = geo.get("regions", [])
    paises = geo.get("countries", [])

    places = geo.get("places", [])
    custom_locations = geo.get("custom_locations", [])

    def geocodificar_inverso(lat, lng):
        """Convierte coordenadas a ciudad y país usando Nominatim (OpenStreetMap)."""
        clave = (round(lat, 4), round(lng, 4))
        if clave in _cache_geocodificacion:
            return _cache_geocodificacion[clave]
        try:
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {"lat": lat, "lon": lng, "format": "json", "zoom": 10}
            headers = {"User-Agent": "Riqai-MetaAds-Agent/1.0"}
            resp = requests.get(url, params=params, headers=headers, timeout=5)
            data = resp.json()
            address = data.get("address", {})
            ciudad = (
                address.get("city")
                or address.get("town")
                or address.get("village")
                or address.get("county", "")
            )
            pais = address.get("country_code", "").upper()
            resultado = f"{ciudad}, {pais}" if ciudad else None
        except Exception:
            resultado = None
        _cache_geocodificacion[clave] = resultado
        return resultado

    def formatear_lugar(loc):
        nombre = loc.get("name", "")
        radio = loc.get("radius")
        unidad = "km" if "kilo" in loc.get("distance_unit", "") else loc.get("distance_unit", "km")
        lat = loc.get("latitude")
        lng = loc.get("longitude")

        # Si no tiene nombre pero tiene coordenadas, intentar geocodificación inversa
        if not nombre and lat and lng:
            nombre = geocodificar_inverso(lat, lng) or f"({lat:.4f}, {lng:.4f})"

        if nombre and radio:
            return f"{nombre} (+{radio} {unidad})"
        elif nombre:
            return nombre
        return "Ubicación personalizada"

    if places or custom_locations:
        todos_lugares = places + custom_locations
        nombres = [formatear_lugar(p) for p in todos_lugares[:5]]
        sufijo = f" (+{len(todos_lugares) - 5} más)" if len(todos_lugares) > 5 else ""
        lineas.append(f"Lugares: {', '.join(nombres)}{sufijo}")
    elif ciudades:
        nombres = []
        for c in ciudades[:5]:
            nombres.append(c.get("name") or c.get("key", "") if isinstance(c, dict) else str(c))
        sufijo = f" (+{len(ciudades) - 5} más)" if len(ciudades) > 5 else ""
        lineas.append(f"Ciudades: {', '.join(nombres)}{sufijo}")
    elif regiones:
        nombres = [r.get("name") or r.get("key", "") if isinstance(r, dict) else str(r) for r in regiones[:5]]
        lineas.append(f"Regiones: {', '.join(nombres)}")
    elif paises:
        nombres = [p if isinstance(p, str) else p.get("name", str(p)) for p in paises]
        lineas.append(f"Países: {', '.join(nombres)}")
    else:
        lineas.append("Ubicación: No especificada")

    # Intereses — vienen dentro de flexible_spec
    flexible_spec = targeting.get("flexible_spec", [])
    intereses = []
    for spec in flexible_spec:
        for interes in spec.get("interests", []):
            if isinstance(interes, dict):
                nombre = interes.get("name", "")
            else:
                nombre = str(interes)
            if nombre:
                intereses.append(nombre)

    if intereses:
        sufijo = f" (+{len(intereses) - 5} más)" if len(intereses) > 5 else ""
        lineas.append(f"Intereses: {', '.join(intereses[:5])}{sufijo}")

    return "\n                 ".join(lineas) if lineas else "Sin segmentación detallada"


def formatear_presupuesto(adset, simbolo):
    """Devuelve el presupuesto del ad set formateado."""
    diario = adset.get("daily_budget")
    total = adset.get("lifetime_budget")

    if diario and diario != "0":
        return f"Presupuesto diario:  {simbolo} {int(diario) / 100:.2f}"
    elif total and total != "0":
        return f"Presupuesto total:   {simbolo} {int(total) / 100:.2f}"
    else:
        return "Presupuesto: heredado de la campaña"


def imprimir_adsets(adsets, simbolo):
    """Imprime los ad sets en formato legible."""
    if not adsets:
        print("⚠️  No se encontraron ad sets con los filtros aplicados.")
        return

    print(f"\n📦 Ad Sets encontrados: {len(adsets)}")
    print("=" * 65)

    for a in adsets:
        estado_icon = "🟢" if a["status"] == "ACTIVE" else "⏸️ " if a["status"] == "PAUSED" else "🗄️ "
        print(f"{estado_icon} {a['name']}")
        print(f"   ID:              {a['id']}")
        print(f"   Estado:          {a['status']}")
        print(f"   Campaña ID:      {a.get('campaign_id', 'N/A')}")
        print(f"   {formatear_presupuesto(a, simbolo)}")
        print(f"   Objetivo:        {a.get('optimization_goal', 'N/A')}")
        print(f"   Estrategia puja: {a.get('bid_strategy', 'N/A')}")

        bid_amount = a.get("bid_amount")
        if bid_amount and bid_amount != "0":
            print(f"   Monto puja:      {simbolo} {int(bid_amount) / 100:.2f}")

        print(f"   Segmentación:    {formatear_segmentacion(a.get('targeting', {}))}")

        if a.get("start_time"):
            print(f"   Inicio:          {a['start_time'][:10]}")
        if a.get("end_time"):
            print(f"   Fin:             {a['end_time'][:10]}")

        print("-" * 65)


def main():
    parser = argparse.ArgumentParser(description="Lista ad sets de Meta Ads")
    parser.add_argument("--campaign_id", help="ID de campaña específica (opcional)")
    parser.add_argument(
        "--status",
        choices=["ACTIVE", "PAUSED", "ARCHIVED"],
        help="Filtrar por estado",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Muestra el targeting crudo del primer ad set para diagnóstico",
    )
    args = parser.parse_args()

    if not ACCESS_TOKEN or not AD_ACCOUNT_ID:
        print("❌ Faltan credenciales en .env")
        sys.exit(1)

    simbolo = obtener_moneda_cuenta()

    if args.campaign_id:
        print(f"📡 Obteniendo ad sets de campaña {args.campaign_id}...")
    else:
        print("📡 Obteniendo todos los ad sets de la cuenta...")

    adsets = obtener_adsets(campaign_id=args.campaign_id, filtro_estado=args.status)

    if adsets is None:
        sys.exit(1)

    if args.debug and adsets:
        import json
        print("\n🔍 Targeting crudo del primer ad set:")
        print(json.dumps(adsets[0].get("targeting", {}), indent=2, ensure_ascii=False))
        print()

    imprimir_adsets(adsets, simbolo)


if __name__ == "__main__":
    main()
