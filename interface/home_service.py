import requests
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

API_URL = "http://127.0.0.1:8000/api"


def obter_mes_nome(mes_num: int) -> str:
    meses = [
        "Janeiro",
        "Fevereiro",
        "Março",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro",
    ]
    return meses[mes_num - 1]


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


##############
###CHECKINS###
##############

def obter_checkins_mes(ano: int, mes_nome: str) -> Tuple[bool, Any]:
    try:
        response = requests.get(
            f"{API_URL}/checkins", params={"ano": ano, "mes_nome": mes_nome}, timeout=10
        )
        response.raise_for_status()
        return True, response.json()
    except requests.RequestException as exc:
        return False, f"Erro ao buscar check-ins: {exc}"


def carregar_checkin_hoje() -> Tuple[Optional[dict], Optional[str]]:
    hoje = datetime.now().date()
    mes_nome = obter_mes_nome(hoje.month)
    ok, resultado = obter_checkins_mes(hoje.year, mes_nome)
    if not ok:
        return None, resultado

    checkins = resultado if isinstance(resultado, list) else []
    hoje_str = hoje.isoformat()
    for item in checkins:
        if item.get("data") == hoje_str:
            return item, None
    return None, None


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


#################
###CALENDARIO####
#################

def processar_clique_calendario(cal_state: dict) -> str | None:
    """
    Extrai a data clicada no formato YYYY-MM-DD a partir do evento do FullCalendar.
    """
    if not isinstance(cal_state, dict):
        return None

    if "dateClick" in cal_state:
        raw_date = cal_state["dateClick"].get("date", "")
        return raw_date.split("T")[0] if raw_date else None

    if "eventClick" in cal_state:
        raw_date = cal_state["eventClick"].get("event", {}).get("start", "")
        return raw_date.split("T")[0] if raw_date else None

    return None


def obter_resumo_diario(data_alvo: str, lista_checkins: list, lista_trades: list) -> dict | None:
    """
    Filtra checkins e trades para a data alvo utilizando apenas tipos nativos.
    `lista_trades` deve ser uma lista de dicionários (list[dict]).
    """
    if not data_alvo:
        return None

    # 1. Filtra Check-in
    checkin = next(
        (c for c in lista_checkins if str(c.get("data", "")).startswith(data_alvo)),
        None
    )
    
    dados_checkin = None
    if checkin:
        dados_checkin = {
            "status": checkin.get("status", "Registrado"),
            "observacao": checkin.get("observacao", "")
        }

    # 2. Filtra Trades do dia
    trades_dia = [
        t for t in lista_trades 
        if str(t.get("data_trade", "")).startswith(data_alvo)
    ]

    dados_trades = None
    if trades_dia:
        pnl_total = sum(float(t.get("resultado", 0) or 0) for t in trades_dia)
        dados_trades = {
            "total_operacoes": len(trades_dia),
            "pnl": pnl_total,
            "operacoes": trades_dia
        }

    return {
        "data": data_alvo,
        "checkin": dados_checkin,
        "trades": dados_trades
    }