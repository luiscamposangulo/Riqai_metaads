"""
Prueba de conexión con Meta Graph API.
Valida el token y muestra las campañas activas de la cuenta publicitaria.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID")
BASE_URL = "https://graph.facebook.com/v25.0"


def verificar_token():
    """Verifica que el token sea válido y muestra a qué usuario pertenece."""
    url = f"{BASE_URL}/me"
    params = {"access_token": ACCESS_TOKEN, "fields": "id,name"}
    response = requests.get(url, params=params)
    data = response.json()

    if "error" in data:
        print(f"❌ Token inválido: {data['error']['message']}")
        return False

    print(f"✅ Token válido — Usuario: {data['name']} (ID: {data['id']})")
    return True


def listar_campanias():
    """Lista las campañas de la cuenta publicitaria con su estado y objetivo."""
    url = f"{BASE_URL}/{AD_ACCOUNT_ID}/campaigns"
    params = {
        "access_token": ACCESS_TOKEN,
        "fields": "id,name,status,objective",
        "limit": 10,
    }
    response = requests.get(url, params=params)
    data = response.json()

    if "error" in data:
        print(f"❌ Error al obtener campañas: {data['error']['message']}")
        return

    campanias = data.get("data", [])
    if not campanias:
        print("⚠️  No se encontraron campañas en esta cuenta.")
        return

    print(f"\n📋 Campañas encontradas ({len(campanias)}):")
    print("-" * 60)
    for c in campanias:
        print(f"  ID:       {c['id']}")
        print(f"  Nombre:   {c['name']}")
        print(f"  Estado:   {c['status']}")
        print(f"  Objetivo: {c.get('objective', 'N/A')}")
        print("-" * 60)


if __name__ == "__main__":
    print("🔌 Probando conexión con Meta Graph API...\n")

    if verificar_token():
        listar_campanias()
