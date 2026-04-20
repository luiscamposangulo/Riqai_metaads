"""
Pausa o activa un anuncio, ad set o campaña en Meta Ads.

A diferencia de los scripts de lectura, este script realiza cambios reales en Meta.
Muestra el estado actual antes de cambiar y pide confirmación salvo que se use --yes.

Uso:
    # Pausar un anuncio
    python src/ads/update_status.py --ad_id 120201234567890 --status PAUSED

    # Activar un anuncio
    python src/ads/update_status.py --ad_id 120201234567890 --status ACTIVE

    # Pausar un ad set completo (pausa todos sus anuncios)
    python src/ads/update_status.py --adset_id 120201234567890 --status PAUSED

    # Pausar una campaña completa
    python src/ads/update_status.py --campaign_id 120201234567890 --status PAUSED

    # Sin confirmación interactiva (útil para automatización)
    python src/ads/update_status.py --ad_id 120201234567890 --status PAUSED --yes
"""

import os
import sys
import argparse
from pathlib import Path
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

load_dotenv()

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
BASE_URL = "https://graph.facebook.com/v25.0"

TIPO_LABELS = {
    "ad": "Anuncio",
    "adset": "Ad Set",
    "campaign": "Campaña",
}

ESTADO_ICONS = {
    "ACTIVE": "🟢 ACTIVE",
    "PAUSED": "⏸️  PAUSED",
    "CAMPAIGN_PAUSED": "🟡 CAMPAIGN_PAUSED",
    "ADSET_PAUSED": "🟠 ADSET_PAUSED",
    "ARCHIVED": "🗄️  ARCHIVED",
    "DELETED": "🗑️  DELETED",
    "WITH_ISSUES": "⚠️  WITH_ISSUES",
}


def obtener_estado_actual(object_id, tipo):
    """
    Consulta el estado actual del objeto antes de modificarlo.

    Returns:
        Dict con id, name, status, effective_status o None si hubo error.
    """
    url = f"{BASE_URL}/{object_id}"
    params = {
        "access_token": ACCESS_TOKEN,
        "fields": "id,name,status,effective_status",
    }
    data = requests.get(url, params=params).json()

    if "error" in data:
        print(f"❌ Error al consultar {TIPO_LABELS[tipo]}: {data['error']['message']}")
        return None

    return data


def actualizar_status(object_id, nuevo_status):
    """
    Envía el cambio de status a la API de Meta.

    Returns:
        True si el cambio fue exitoso, False si hubo error.
    """
    url = f"{BASE_URL}/{object_id}"
    params = {
        "access_token": ACCESS_TOKEN,
        "status": nuevo_status,
    }
    data = requests.post(url, params=params).json()

    if "error" in data:
        print(f"❌ Error al actualizar: {data['error']['message']}")
        return False

    return data.get("success", False)


def mostrar_estado(objeto, tipo, prefijo=""):
    """Imprime el estado de un objeto con formato."""
    effective = objeto.get("effective_status", objeto["status"])
    icono = ESTADO_ICONS.get(effective, effective)
    print(f"{prefijo}{TIPO_LABELS[tipo]}: {objeto['name']}")
    print(f"{prefijo}   ID:              {objeto['id']}")
    print(f"{prefijo}   Estado config.:  {objeto['status']}")
    print(f"{prefijo}   Estado real:     {icono}")


def confirmar_accion(nombre, tipo, estado_actual, nuevo_status):
    """Muestra resumen del cambio y pide confirmación al usuario."""
    print(f"\n{'=' * 60}")
    print(f"  Cambio solicitado:")
    print(f"  {TIPO_LABELS[tipo]}: {nombre}")
    print(f"  Estado actual → nuevo estado:")
    print(f"  {estado_actual}  →  {nuevo_status}")
    print(f"{'=' * 60}")
    respuesta = input("\n  ¿Confirmar cambio? [s/N]: ").strip().lower()
    return respuesta in ("s", "si", "sí", "y", "yes")


def main():
    parser = argparse.ArgumentParser(description="Pausa o activa un anuncio, ad set o campaña")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--ad_id", help="ID del anuncio")
    grupo.add_argument("--adset_id", help="ID del ad set")
    grupo.add_argument("--campaign_id", help="ID de la campaña")
    parser.add_argument(
        "--status",
        required=True,
        choices=["ACTIVE", "PAUSED"],
        help="Nuevo estado: ACTIVE o PAUSED",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirmar cambio sin prompt interactivo",
    )
    args = parser.parse_args()

    if not ACCESS_TOKEN:
        print("❌ Falta META_ACCESS_TOKEN en .env")
        sys.exit(1)

    # Determinar tipo y ID del objeto
    if args.ad_id:
        object_id, tipo = args.ad_id, "ad"
    elif args.adset_id:
        object_id, tipo = args.adset_id, "adset"
    else:
        object_id, tipo = args.campaign_id, "campaign"

    # Consultar estado actual
    print(f"\n📡 Consultando estado actual del {TIPO_LABELS[tipo]}...")
    objeto = obtener_estado_actual(object_id, tipo)
    if objeto is None:
        sys.exit(1)

    print()
    mostrar_estado(objeto, tipo)

    estado_actual = objeto.get("effective_status", objeto["status"])

    # Verificar si el cambio es necesario
    if estado_actual == args.status:
        print(f"\n✅ El {TIPO_LABELS[tipo]} ya está en estado {args.status}. No se realizó ningún cambio.")
        sys.exit(0)

    # Confirmación
    if not args.yes:
        if not confirmar_accion(objeto["name"], tipo, estado_actual, args.status):
            print("\n  Operación cancelada.")
            sys.exit(0)

    # Ejecutar el cambio
    print(f"\n⏳ Aplicando cambio...")
    exito = actualizar_status(object_id, args.status)

    if not exito:
        sys.exit(1)

    # Verificar estado resultante
    objeto_actualizado = obtener_estado_actual(object_id, tipo)
    if objeto_actualizado:
        print(f"\n✅ Cambio aplicado exitosamente:")
        mostrar_estado(objeto_actualizado, tipo, prefijo="   ")
    else:
        print(f"\n✅ Cambio aplicado. (No se pudo verificar el estado final)")


if __name__ == "__main__":
    main()
