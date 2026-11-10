"""
Vigila maquillajetrendyshop.com (VTEX) y avisa por Telegram cuando aparezca
un producto de calendario de adviento.

Variables de entorno necesarias:
  TELEGRAM_BOT_TOKEN  -> token que te da @BotFather
  TELEGRAM_CHAT_ID    -> tu chat id (ver instrucciones en el chat)

Uso:
  pip install requests
  python trendy_adviento.py            # una sola revisión
  python trendy_adviento.py --loop     # revisa cada 10 min
"""
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

BASE = "https://www.maquillajetrendyshop.com"
TERMINOS = ["calendario de adviento", "adviento", "advent"]
PALABRAS_CLAVE = ("adviento", "advent")
ESTADO = Path(__file__).with_name("vistos.json")
INTERVALO_SEG = 600
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TrendyWatcher/1.0)"}


def cargar_vistos() -> set:
    if ESTADO.exists():
        return set(json.loads(ESTADO.read_text(encoding="utf-8")))
    return set()


def guardar_vistos(vistos: set) -> None:
    ESTADO.write_text(json.dumps(sorted(vistos), ensure_ascii=False), encoding="utf-8")


def buscar(termino: str) -> list:
    """Búsqueda pública del catálogo VTEX."""
    url = f"{BASE}/api/catalog_system/pub/products/search?ft={quote(termino)}&_from=0&_to=24"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()


def encontrar_calendarios() -> dict:
    """Devuelve {link: nombre} de productos que parezcan el calendario de adviento."""
    hallados = {}
    for termino in TERMINOS:
        try:
            productos = buscar(termino)
            ejemplo = productos[0].get("productName", "?") if productos else "-"
            print(f"[debug] '{termino}': {len(productos)} productos devueltos (ej: {ejemplo})")
            for p in productos:
                nombre = p.get("productName", "")
                if any(k.lower() in nombre.lower() for k in PALABRAS_CLAVE):
                    hallados[p["link"]] = nombre
        except Exception as e:
            print(f"[aviso] falló la búsqueda de '{termino}': {e}", file=sys.stderr)
    return hallados


def telegram(texto: str) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": texto, "disable_web_page_preview": False},
        timeout=20,
    )
    r.raise_for_status()


def revisar() -> None:
    vistos = cargar_vistos()
    hallados = encontrar_calendarios()
    nuevos = {l: n for l, n in hallados.items() if l not in vistos}
    for link, nombre in nuevos.items():
        telegram(f"🎄 ¡Ya subieron el calendario de adviento de Trendy!\n\n{nombre}\n{link}")
        vistos.add(link)
    if nuevos:
        guardar_vistos(vistos)
    print(f"{time.strftime('%H:%M:%S')} - encontrados: {len(hallados)}, nuevos: {len(nuevos)}")


if __name__ == "__main__":
    if "--loop" in sys.argv:
        while True:
            try:
                revisar()
            except Exception as e:
                print(f"[error] {e}", file=sys.stderr)
            time.sleep(INTERVALO_SEG)
    else:
        revisar()
