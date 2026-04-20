"""
Utilidades compartidas para interactuar con la Meta Graph API.
"""

import os
import requests

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID")
BASE_URL = "https://graph.facebook.com/v25.0"

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
    data = requests.get(url, params=params).json()
    codigo = data.get("currency", "USD")
    return SIMBOLOS_MONEDA.get(codigo, codigo)
