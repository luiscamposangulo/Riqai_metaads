"""
Lista todas las campañas de la cuenta publicitaria de Meta Ads.
Muestra ID, nombre, estado, objetivo y presupuesto (diario o total).

Uso:
    python src/campaigns/list_campaigns.py
    python src/campaigns/list_campaigns.py --status ACTIVE
    python src/campaigns/list_campaigns.py --status PAUSED
"""

import os
import sys
import argparse
import requests
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID")
BASE_URL = "https://graph.facebook.com/v21.0"

CAMPOS = "id,name,status,objective,daily_budget,lifetime_budget,start_time,stop_time"

# Símbolos por código de moneda ISO 4217
SIMBOLOS_MONEDA = {
    "USD": "$",
    "PEN": "S/",
    "MXN": "MX$",
    "COP": "COP$",
    "ARS": "AR$",
    "CLP": "CLP$",
    "EUR": "€",
    "BRL": "R$",
}


def obtener_moneda_cuenta():
    """
    Consulta la moneda configurada en la cuenta publicitaria.

    Returns:
        Símbolo de moneda (ej: 'S/', '$') o '$' por defecto si falla.
    """
    url = f"{BASE_URL}/{AD_ACCOUNT_ID}"
    params = {"access_token": ACCESS_TOKEN, "fields": "currency"}
    response = requests.get(url, params=params)
    data = response.json()

    if "error" in data or "currency" not in data:
        return "$"  # Fallback si no se puede obtener

    codigo = data["currency"]
    return SIMBOLOS_MONEDA.get(codigo, codigo)  # Devuelve el código si no está en el mapa


def obtener_campanias(filtro_estado=None):
    """
    Obtiene todas las campañas de la cuenta publicitaria.
    Maneja paginación para cuentas con muchas campañas.

    Args:
        filtro_estado: 'ACTIVE', 'PAUSED', 'ARCHIVED' o None para todas.

    Returns:
        Lista de campañas o None si hubo error.
    """
    url = f"{BASE_URL}/{AD_ACCOUNT_ID}/campaigns"
    params = {
        "access_token": ACCESS_TOKEN,
        "fields": CAMPOS,
        "limit": 100,
    }

    # Filtrar por estado si se especifica
    if filtro_estado:
        params["effective_status"] = f'["{filtro_estado}"]'

    todas = []

    while url:
        response = requests.get(url, params=params)
        data = response.json()

        if "error" in data:
            print(f"❌ Error de API: {data['error']['message']}")
            print(f"   Código: {data['error']['code']}")
            return None

        todas.extend(data.get("data", []))

        # Paginación — si hay más páginas, seguir
        paging = data.get("paging", {})
        url = paging.get("next")
        params = {}  # La URL de 'next' ya incluye todos los params

    return todas


def formatear_presupuesto(campania, simbolo):
    """Devuelve el presupuesto formateado (diario o total) con el símbolo correcto."""
    diario = campania.get("daily_budget")
    total = campania.get("lifetime_budget")

    if diario and diario != "0":
        return f"Diario:  {simbolo} {int(diario) / 100:.2f}"
    elif total and total != "0":
        return f"Total:   {simbolo} {int(total) / 100:.2f}"
    else:
        return "Presupuesto: N/A (heredado del Ad Set)"


def imprimir_campanias(campanias, simbolo):
    """Imprime las campañas en formato legible."""
    if not campanias:
        print("⚠️  No se encontraron campañas con los filtros aplicados.")
        return

    print(f"\n📋 Campañas encontradas: {len(campanias)}")
    print("=" * 65)

    for c in campanias:
        estado_icon = "🟢" if c["status"] == "ACTIVE" else "⏸️ " if c["status"] == "PAUSED" else "🗄️ "
        print(f"{estado_icon} {c['name']}")
        print(f"   ID:         {c['id']}")
        print(f"   Estado:     {c['status']}")
        print(f"   Objetivo:   {c.get('objective', 'N/A')}")
        print(f"   {formatear_presupuesto(c, simbolo)}")
        if c.get("start_time"):
            print(f"   Inicio:     {c['start_time'][:10]}")
        if c.get("stop_time"):
            print(f"   Fin:        {c['stop_time'][:10]}")
        print("-" * 65)


def main():
    parser = argparse.ArgumentParser(description="Lista campañas de Meta Ads")
    parser.add_argument(
        "--status",
        choices=["ACTIVE", "PAUSED", "ARCHIVED"],
        help="Filtrar por estado: ACTIVE, PAUSED o ARCHIVED",
    )
    args = parser.parse_args()

    # Validar credenciales mínimas
    if not ACCESS_TOKEN or not AD_ACCOUNT_ID:
        print("❌ Faltan credenciales en .env (META_ACCESS_TOKEN o META_AD_ACCOUNT_ID)")
        sys.exit(1)

    filtro = args.status
    label = f" [{filtro}]" if filtro else " [todas]"
    print(f"📡 Obteniendo campañas{label}...")

    simbolo = obtener_moneda_cuenta()
    campanias = obtener_campanias(filtro_estado=filtro)

    if campanias is None:
        sys.exit(1)

    imprimir_campanias(campanias, simbolo)


if __name__ == "__main__":
    main()
