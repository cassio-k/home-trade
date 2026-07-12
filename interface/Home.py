import streamlit as st
import requests
import pandas as pd
from streamlit_calendar import calendar

# Configuração para usar o espaço total da tela
st.set_page_config(layout="wide", page_title="Dashboard de Trading", page_icon="📈")

API_URL = "http://127.0.0.1:8000/api"


# --- BARRA LATERAL: FILTROS MACRO ---
with st.sidebar:
    st.header("Filtros Globais")
    
    mes_selecionado = st.selectbox("Filtrar por Mês", ["", "2026-07", "2026-06", "2026-05"])
    ativo_selecionado = st.text_input("Filtrar por Ativo (Ex: WDO)", value="").strip()
    setup_selecionado = st.text_input("Filtrar por Setup (ID)", value="").strip()

params = {}
if mes_selecionado: params["mes"] = mes_selecionado
if ativo_selecionado: params["ativo"] = ativo_selecionado
if setup_selecionado: params["setup_id"] = setup_selecionado


# --- REQUISIÇÃO ÚNICA PARA O BACKEND (FastAPI) ---
try:
    res = requests.get(f"{API_URL}/Home", params=params)
    
    # Se o backend retornar 400, 422, 500, etc., isso vai forçar um erro imediatamente
    res.raise_for_status() 
    resposta_api = res.json()
    
except requests.exceptions.HTTPError as http_err:
    st.error(f"🚨 O Backend respondeu com erro crítico!")
    st.code(res.text, language="json")  # Mostra o erro real do FastAPI na tela
    st.stop()
except Exception as e:
    st.error("🚨 Erro de conexão: O backend (FastAPI) está desligado.")
    st.stop()

# Desempacotamento do payload limpo enviado pelo servidor
metricas = resposta_api["metricas"]
historico = resposta_api["historico"]
graficos = resposta_api["graficos"]

# --- RENDERIZAÇÃO DA INTERFACE ---
st.title("📈 Visão Geral da Performance")
st.caption("Dados analíticos consolidados em tempo real através da API.")

st.divider()

# 1. BLOCO DE MÉTRICAS VITAIS
col1, col2, col3 = st.columns(3)
with col1:
    lucro = metricas["lucro_total"]
    cor_metrica = "green" if lucro >= 0 else "red"
    st.markdown(f"**Resultado Líquido Acumulado**\n### :{cor_metrica}[R$ {lucro:.2f}]")
with col2:
    st.markdown(f"**Volume de Operações**\n### {metricas['total_trades']} trades")
with col3:
    st.markdown(f"**Taxa de Acerto (Win Rate)**\n### {metricas['taxa_acerto']}%")

st.divider()
if not historico:
    st.info("Nenhuma operação encontrada para os filtros selecionados nesta combinação.")
    st.stop()

# Transforma o histórico em DataFrame apenas para alimentar os componentes visuais
df_trades = pd.DataFrame(historico)

# 2. CURVA DE CAPITAL (EQUITY CURVE)
st.subheader("Análise de Performance")
st.caption("Evolução do capital acumulado trade a trade")
if graficos["curva_capital"]:
    df_curva = pd.DataFrame(graficos["curva_capital"])
    df_curva.set_index("data_trade", inplace=True)
    st.line_chart(df_curva, y="saldo", use_container_width=True)

st.divider()

# 3. GRÁFICOS DE PERFORMANCE COMPARATIVOS (LADO A LADO)
col_esq, col_dir = st.columns(2)
with col_esq:
    st.subheader("Performance por Setup")
    if graficos["performance_setup"]:
        st.bar_chart(graficos["performance_setup"])
with col_dir:
    st.subheader("Performance por Estado Emocional")
    if graficos["performance_emocional"]:
        st.bar_chart(graficos["performance_emocional"])

st.divider()

# 4. O CALENDÁRIO 
st.subheader("Calendário de Operações")
eventos = []

for _, row in df_trades.iterrows():
    lucro_trade = float(row["resultado"])
    cor_evento = "#2e7d32" if lucro_trade > 0 else ("#c62828" if lucro_trade < 0 else "#7f8c8d")
    
    try:
        data_formatada = pd.to_datetime(row["data_trade"]).strftime("%Y-%m-%d")
    except Exception:
        continue

    eventos.append({
        "title": f"{str(row['ordem']).upper()} | {row['ativo']}",
        "start": data_formatada,
        "backgroundColor": cor_evento,
        "borderColor": cor_evento,
    })

calendar_options = {
    "editable": True,
    "selectable": True,
    "headerToolbar": {
        "left": "today prev,next",
        "center": "title",
        "right": "dayGridMonth,timeGridWeek,timeGridDay",
    },
    "initialView": "dayGridMonth",
}

calendar(events=eventos, options=calendar_options)

st.divider()

# 5. TABELA DE DADOS BRUTOS (FIM DA PÁGINA)
st.subheader("Listagem Detalhada")
colunas_exibicao = ["data_trade", "ativo", "ordem", "setup_id", "emocional_id", "resultado"]
st.dataframe(df_trades[colunas_exibicao], use_container_width=True)