"""
storage.py — Persistencia de datos
Usa un archivo JSON local. En Railway el volumen persiste si se monta /data.
Para producción robusta, migrar a Supabase (ver comentarios).
"""

import json
import os
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("storage")

# Railway monta volúmenes en /data — si no existe, usar directorio local
DATA_DIR = Path(os.getenv("DATA_DIR", "/data" if os.path.exists("/data") else "."))
DATA_FILE = DATA_DIR / "psoe_monitor_historico.json"
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "90"))  # días de histórico


def load_data() -> dict:
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error leyendo datos: {e}")
    return {"history": [], "last_update": None}


def save_data(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error guardando datos: {e}")


def append_entry(entry: dict) -> None:
    data = load_data()
    data["history"].append(entry)
    # Mantener solo los últimos MAX_HISTORY días
    if len(data["history"]) > MAX_HISTORY:
        data["history"] = data["history"][-MAX_HISTORY:]
    data["last_update"] = entry["timestamp"]
    save_data(data)
    logger.info(f"Entry guardada. Total en histórico: {len(data['history'])}")


# ── Supabase (alternativa productiva) ────────────────────────────────────────
# Para usar Supabase en lugar de JSON, instalar: pip install supabase
# y descomentar el siguiente bloque. Añadir SUPABASE_URL y SUPABASE_KEY en .env
#
# from supabase import create_client
# _sb = None
# def _get_supabase():
#     global _sb
#     if _sb is None:
#         url = os.getenv("SUPABASE_URL")
#         key = os.getenv("SUPABASE_KEY")
#         if url and key:
#             _sb = create_client(url, key)
#     return _sb
#
# def append_entry_supabase(entry: dict):
#     sb = _get_supabase()
#     if sb:
#         sb.table("monitor_history").insert(entry).execute()
