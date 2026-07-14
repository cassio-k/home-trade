from datetime import datetime, time
from typing import Any, Dict, Optional, Tuple

import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000/api"

SETUPS_DISPONIVEIS = [
    "123",
    "Gift",
    "Pullback",
    "Barra ignorada",
    "Pivo",
    "Rompimento",
    "Reversão",
    "Fibonacci",
    "Gap de venda",
    "Barra de ignição",
]
EMOCIONAIS_DISPONIVEIS = ["Desatento", "Ansioso", "Focado", "Neutro"]
SETUPS_MAPPING = {
    1: "123",
    2: "Gift",
    3: "Pullback",
    4: "Barra ignorada",
    5: "Pivo",
    6: "Rompimento",
    7: "Reversão",
    8: "Fibonacci",
    9: "Gap de venda",
    10: "Barra de ignição",
}
EMOTIONS_MAPPING = {
    1: "Neutro",
    2: "Focado",
    3: "Ansioso",
    4: "Desatento",
}


def obter_indice_opcao(valor, opcoes, fallback):
    if valor in opcoes:
        return opcoes.index(valor)
    return opcoes.index(fallback)


def resolver_valor_select(valor, mapping, fallback, opcoes):
    if valor in opcoes:
        return valor
    if isinstance(valor, int) and valor in mapping:
        return mapping[valor]
    return fallback


def inicializar_estado():
    estados_padrao = {
        "trade_ativo_id": None,
        "form_data": datetime.now().date(),
        "form_hora": time(11, 19),
        "form_direcao": "Buy",
        "form_ativo": "WEGE3",
        "form_qtd": 100,
        "form_pe": 40.0,
        "form_ps": 39.5,
        "form_resultado": 0.0,
        "form_setup": "123",
        "form_emocional": "Neutro",
        "form_url": "",
        "form_relatorio": "",
        "ultimo_hash_enviado": None,
    }

    for chave, valor in estados_padrao.items():
        if chave not in st.session_state:
            st.session_state[chave] = valor


def resetar_formulario():
    st.session_state.trade_ativo_id = None
    st.session_state.form_data = datetime.now().date()
    st.session_state.form_hora = time(11, 19)
    st.session_state.form_direcao = "Buy"
    st.session_state.form_ativo = ""
    st.session_state.form_qtd = 100
    st.session_state.form_pe = 0.0
    st.session_state.form_ps = 0.0
    st.session_state.form_resultado = 0.0
    st.session_state.form_setup = "123"
    st.session_state.form_emocional = "Neutro"
    st.session_state.form_url = ""
    st.session_state.form_relatorio = ""
    st.session_state.ultimo_hash_enviado = None


def carregar_trade_no_form(dados_item):
    st.session_state.trade_ativo_id = dados_item["id"]
    st.session_state.form_data = datetime.fromisoformat(dados_item["data_trade"]).date()
    st.session_state.form_hora = datetime.fromisoformat(dados_item["data_trade"]).time()
    st.session_state.form_direcao = dados_item["ordem"]
    st.session_state.form_ativo = dados_item["ativo"]
    st.session_state.form_qtd = dados_item["quantidade"]
    st.session_state.form_pe = dados_item["preco_entrada"]
    st.session_state.form_ps = dados_item["preco_saida"]
    st.session_state.form_resultado = dados_item.get("resultado", 0.0)
    st.session_state.form_setup = resolver_valor_select(
        dados_item.get("setup_nome") or dados_item.get("setup_id"),
        SETUPS_MAPPING,
        "123",
        SETUPS_DISPONIVEIS,
    )
    st.session_state.form_emocional = resolver_valor_select(
        dados_item.get("emocional_nome") or dados_item.get("emocional_id"),
        EMOTIONS_MAPPING,
        "Neutro",
        EMOCIONAIS_DISPONIVEIS,
    )
    st.session_state.form_url = dados_item.get("url_imagem", "")
    st.session_state.form_relatorio = dados_item.get("relatorio", "")


def carregar_trades_mes(ano_sel, pasta_sel):
    try:
        response = requests.get(f"{API_URL}/trades", params={"ano": ano_sel, "mes_nome": pasta_sel}, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        st.error(f"Não foi possível conectar ao servidor: {exc}")
        return []


def carregar_trade_por_id(trade_id: int) -> Tuple[bool, Any]:
    try:
        response = requests.get(f"{API_URL}/trades/{trade_id}", timeout=8)
        response.raise_for_status()
        return True, response.json()
    except requests.RequestException as exc:
        return False, f"Não foi possível carregar o trade: {exc}"


def construir_payload(
    data_input,
    horario_input,
    direcao,
    ativo,
    quantidade,
    preco_in,
    preco_out,
    resultado,
    relatorio,
    setup_selecionado,
    emocional_selecionado,
    form_url,
) -> Dict[str, Any]:
    return {
        "data_trade": datetime.combine(data_input, horario_input).isoformat(),
        "ativo": ativo,
        "ordem": direcao,
        "quantidade": quantidade,
        "preco_entrada": preco_in,
        "preco_saida": preco_out,
        "resultado": resultado,
        "relatorio": relatorio,
        "setup_id": setup_selecionado,
        "emocional_id": emocional_selecionado,
        "is_legado": False,
        "url_imagem": form_url,
    }


def salvar_trade(payload: Dict[str, Any], trade_id: Optional[int] = None) -> Tuple[bool, Optional[str]]:
    try:
        if trade_id:
            response = requests.put(f"{API_URL}/trades/{trade_id}", json=payload, timeout=10)
        else:
            response = requests.post(f"{API_URL}/trades", json=payload, timeout=10)
        response.raise_for_status()
        return True, None
    except requests.RequestException as exc:
        return False, f"Erro de comunicação com a API: {exc}"


def excluir_trade(trade_id: int) -> Tuple[bool, Optional[str]]:
    try:
        response = requests.delete(f"{API_URL}/trades/{trade_id}", timeout=10)
        response.raise_for_status()
        return True, None
    except requests.RequestException as exc:
        return False, f"Erro de comunicação com a API: {exc}"


def enviar_imagem_para_api(image_bytes) -> Tuple[bool, Any]:
    try:
        files = {"file": ("screenshot.png", image_bytes, "image/png")}
        response = requests.post(f"{API_URL}/upload", files=files, timeout=10)
        response.raise_for_status()
        return True, response.json().get("url_imagem")
    except requests.RequestException as exc:
        return False, f"Erro de comunicação com a API: {exc}"
