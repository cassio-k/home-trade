import requests
from typing import Any, Dict, Optional, Tuple

API_URL = "http://127.0.0.1:8000/api"


def buscar_dashboard(mes: Optional[str] = None, ativo: Optional[str] = None, setup_id: Optional[str] = None) -> Tuple[bool, Any]:
    try:
        params: Dict[str, str] = {}
        if mes:
            params["mes"] = mes
        if ativo:
            params["ativo"] = ativo
        if setup_id:
            params["setup_id"] = setup_id

        response = requests.get(f"{API_URL}/Home", params=params, timeout=10)
        response.raise_for_status()
        return True, response.json()
    except requests.RequestException as exc:
        return False, f"Erro ao buscar dashboard: {exc}"


def obter_checkins_mes(ano: int, mes_nome: str) -> Tuple[bool, Any]:
    try:
        response = requests.get(
            f"{API_URL}/checkins", params={"ano": ano, "mes_nome": mes_nome}, timeout=10
        )
        response.raise_for_status()
        return True, response.json()
    except requests.RequestException as exc:
        return False, f"Erro ao buscar check-ins: {exc}"


def registrar_checkin(data: str, checkin: str, status: str = "Presente", observacao: str = "") -> Tuple[bool, Optional[str]]:
    payload = {
        "data": data,
        "checkin": checkin,
        "status": status,
        "observacao": observacao,
    }
    try:
        response = requests.post(f"{API_URL}/checkins", json=payload, timeout=10)
        response.raise_for_status()
        return True, None
    except requests.RequestException as exc:
        return False, f"Erro ao registrar o check-in: {exc}"


def registrar_checkout(checkin_id: int, checkout: str, status: str = "Presente") -> Tuple[bool, Optional[str]]:
    payload = {
        "checkout": checkout,
        "status": status,
    }
    try:
        response = requests.put(f"{API_URL}/checkins/{checkin_id}", json=payload, timeout=10)
        response.raise_for_status()
        return True, None
    except requests.RequestException as exc:
        return False, f"Erro ao registrar o check-out: {exc}"
