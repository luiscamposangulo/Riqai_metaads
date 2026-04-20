"""
Muestra el detalle de activación de los anuncios de un ad set:
fecha de creación, última modificación, estado real y mensaje preconfigurado.

A diferencia de list_ads.py (que muestra métricas de rendimiento como CPL y CTR),
este script muestra la configuración y estado de cada anuncio — útil para auditar
qué está activo, cuándo se activó y qué mensaje tiene configurado.

Uso:
    # Detalle de todos los anuncios de un ad set
    python src/ads/list_ads_detail.py --adset_id 120201234567890

    # Incluir anuncios borrados
    python src/ads/list_ads_detail.py --adset_id 120201234567890 --include-deleted
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

CAMPOS = (
    "id,name,status,effective_status,"
    "created_time,updated_time,"
    "adset_id,campaign_id,"
    "creative{body,title,object_story_spec}"
)

ESTADO_ICONS = {
    "ACTIVE": "🟢",
    "PAUSED": "⏸️ ",
    "CAMPAIGN_PAUSED": "🟡",
    "ADSET_PAUSED": "🟠",
    "ARCHIVED": "🗄️ ",
    "DELETED": "🗑️ ",
    "WITH_ISSUES": "⚠️ ",
    "IN_PROCESS": "⏳",
}


def obtener_anuncios(adset_id, incluir_borrados=False):
    """
    Obtiene anuncios de un ad set con su detalle completo.

    Args:
        adset_id: ID del ad set a consultar.
        incluir_borrados: si True, hace una segunda llamada para traer los borrados.

    Returns:
        Lista de anuncios o None si hubo error.
    """
    url = f"{BASE_URL}/{AD_ACCOUNT_ID}/ads"
    params = {
        "access_token": ACCESS_TOKEN,
        "fields": CAMPOS,
        "effective_status": '["ACTIVE","PAUSED","CAMPAIGN_PAUSED","ADSET_PAUSED","ARCHIVED","WITH_ISSUES"]',
        "filtering": f'[{{"field":"adset.id","operator":"EQUAL","value":"{adset_id}"}}]',
        "limit": 100,
    }

    todos = []
    while url:
        data = requests.get(url, params=params).json()
        if "error" in data:
            print(f"❌ Error de API: {data['error']['message']}")
            return None
        todos.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")
        params = {}

    if incluir_borrados:
        borrados = obtener_anuncios_borrados(adset_id)
        if borrados is None:
            return None
        todos.extend(borrados)

    return todos


def obtener_anuncios_borrados(adset_id):
    """
    Consulta separada para traer anuncios borrados del ad set.
    Meta no permite filtrar DELETED por adset_id en la API — se trae todo a nivel
    de cuenta y se filtra localmente por adset_id.
    """
    # Meta restringe la consulta de anuncios borrados en cuentas estándar
    # (error_subcode 1815001). Requiere permisos especiales de app o cuenta Business.
    print("⚠️  Los anuncios borrados no están disponibles via API con esta configuración.")
    print("   Meta restringe esta consulta para cuentas estándar (error_subcode 1815001).")
    print("   Para verlos, accede directamente al Administrador de Anuncios en Meta.")
    return []


def extraer_mensaje(creative):
    """Extrae el mensaje preconfigurado del creative del anuncio."""
    if not creative:
        return None

    # Mensaje directo en body/title
    if creative.get("body"):
        return creative["body"]
    if creative.get("title"):
        return creative["title"]

    # Mensaje dentro de object_story_spec (anuncios con historia)
    story = creative.get("object_story_spec", {})
    link_data = story.get("link_data", {})
    if link_data.get("message"):
        return link_data["message"]

    return None


def formatear_fecha(fecha_iso):
    """Convierte fecha ISO 8601 a formato legible."""
    if not fecha_iso:
        return "N/A"
    return fecha_iso[:10]


def imprimir_anuncios(anuncios):
    """Imprime el detalle de cada anuncio."""
    if not anuncios:
        print("⚠️  No se encontraron anuncios para este ad set.")
        return

    print(f"\n📋 Anuncios encontrados: {len(anuncios)}")
    print("=" * 65)

    for ad in anuncios:
        effective = ad.get("effective_status", ad["status"])
        icono = ESTADO_ICONS.get(effective, "❓")
        mensaje = extraer_mensaje(ad.get("creative"))

        print(f"{icono} {ad['name']}")
        print(f"   ID:                  {ad['id']}")
        print(f"   Estado configurado:  {ad['status']}")
        print(f"   Estado real:         {effective}")
        print(f"   Fecha de activación: {formatear_fecha(ad.get('created_time'))}")
        print(f"   Última modificación: {formatear_fecha(ad.get('updated_time'))}")
        print(f"   Ad Set ID:           {ad.get('adset_id', 'N/A')}")
        print(f"   Campaña ID:          {ad.get('campaign_id', 'N/A')}")

        if effective == "DELETED":
            print(f"   ⚠️  Borrado — solo se puede modificar el nombre")

        if mensaje:
            # Truncar mensajes muy largos
            preview = mensaje[:120] + "..." if len(mensaje) > 120 else mensaje
            print(f"   Mensaje:             {preview}")
        else:
            print(f"   Mensaje:             (no disponible)")

        print("-" * 65)


def main():
    parser = argparse.ArgumentParser(description="Detalle de anuncios por ad set")
    parser.add_argument("--adset_id", required=True, help="ID del ad set a consultar")
    parser.add_argument(
        "--include-deleted",
        action="store_true",
        help="Incluir anuncios borrados (requiere consulta adicional a la API)",
    )
    args = parser.parse_args()

    if not ACCESS_TOKEN or not AD_ACCOUNT_ID:
        print("❌ Faltan credenciales en .env (META_ACCESS_TOKEN o META_AD_ACCOUNT_ID)")
        sys.exit(1)

    print(f"\n📡 Obteniendo detalle de anuncios del ad set {args.adset_id}...")
    if args.include_deleted:
        print("   (incluyendo anuncios borrados)")

    anuncios = obtener_anuncios(args.adset_id, incluir_borrados=args.include_deleted)

    if anuncios is None:
        sys.exit(1)

    imprimir_anuncios(anuncios)


if __name__ == "__main__":
    main()
