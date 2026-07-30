import sys
from pathlib import Path

from fastapi import background
import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_calendar import calendar

pasta_interface = Path(__file__).resolve().parent
if str(pasta_interface) not in sys.path:
    sys.path.insert(0, str(pasta_interface))

from home_service import buscar_dashboard, obter_checkins_mes, carregar_checkin_hoje, registrar_checkin, registrar_checkout, obter_mes_nome


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


def rerun_if_possible():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    else:
        st.stop()


@st.dialog("📋 Check-in Pré-Market")
def modal_checkin():
    st.write("Registre seu estado pré-sessão:")
    data_checkin = st.date_input("Data", value=datetime.now().date())
    hora_checkin = st.time_input("Horário do Check-in", value=datetime.now().time())
    status = st.selectbox("Status do dia", ["Presente", "Folga", "Ausente"], index=0)
    observacao = st.text_area("Observação", placeholder="Digite sua observação...", height=120)

    if st.button("Gravar Check-in", use_container_width=True, type="primary"):
        ok, erro = registrar_checkin(
            data=data_checkin.isoformat(),
            checkin=datetime.combine(data_checkin, hora_checkin).isoformat(),
            status=status,
            observacao=observacao,
        )
        if ok:
            st.toast("Check-in realizado com sucesso!", icon="✅")
            rerun_if_possible()
        else:
            st.error(erro)


checkin_hoje, erro_checkin = carregar_checkin_hoje()
if erro_checkin:
    st.sidebar.warning(f"Não foi possível carregar o check-in de hoje: {erro_checkin}")

if st.sidebar.button("📌 Check-in", use_container_width=True):
    modal_checkin()


if checkin_hoje is None:
    st.sidebar.info("Nenhum check-in registrado para hoje.")
elif checkin_hoje.get("checkout") is None:
    st.sidebar.success("Check-in ativo")
    st.sidebar.write(f"**Entrada:** {checkin_hoje.get('checkin')}")
    st.sidebar.write(f"**Status:** {checkin_hoje.get('status')}")
    if checkin_hoje.get('observacao'):
        st.sidebar.write(f"**Observação:** {checkin_hoje.get('observacao')}")
    if st.sidebar.button("⏹️ Fazer Check-out", use_container_width=True, key="btn_sidebar_checkout"):
        ok, erro = registrar_checkout(
            int(checkin_hoje["id"]),
            datetime.now().isoformat(),
            status=checkin_hoje.get("status", "Presente"),
        )
        if ok:
            st.sidebar.success("Check-out registrado com sucesso.")
            rerun_if_possible()
        else:
            st.sidebar.error(erro)
else:
    st.sidebar.success("Check-in concluído")
    st.sidebar.write(f"**Entrada:** {checkin_hoje.get('checkin')}")
    st.sidebar.write(f"**Saída:** {checkin_hoje.get('checkout')}")
    st.sidebar.write(f"**Status:** {checkin_hoje.get('status')}")
    if checkin_hoje.get('observacao'):
        st.sidebar.write(f"**Observação:** {checkin_hoje.get('observacao')}")


st.divider()


# --- REQUISIÇÃO ÚNICA PARA O BACKEND (FastAPI) ---
ok, resposta_api = buscar_dashboard(
    mes=params.get("mes"), ativo=params.get("ativo"), setup_id=params.get("setup_id")
)
if not ok:
    st.error(resposta_api)
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


ano_consulta = datetime.now().year
mes_consulta = None

if mes_selecionado:
    ano_consulta = int(mes_selecionado.split("-")[0])
    mes_num = int(mes_selecionado.split("-")[1])
    mes_consulta = obter_mes_nome(mes_num)
else:
    mes_consulta = obter_mes_nome(datetime.now().month)

ok_checkins, dados_checkins = obter_checkins_mes(ano_consulta, mes_consulta)
lista_checkins = dados_checkins if (ok_checkins and isinstance(dados_checkins, list)) else []

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

for c in lista_checkins:
    cor_check = "#0096FA" if 'Presente' in str(c.get("status")) else ("#FDFDFD" if c.get("status") == "Ausente" else "#7f8c8d")

    try:
        data_raw = c.get("data")
        if not data_raw:
            continue

        data_checkin = pd.to_datetime(data_raw).strftime("%Y-%m-%d")
        status = str(c.get("status") or "Check-in")

        eventos.append({
            "start": data_checkin,
            "display": "background",
            "color": cor_check,
        })
    except Exception as e:
        st.write(f"Erro ao formatar item do checkin: {e}")

# 4. Renderização
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