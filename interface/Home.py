import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_calendar import calendar
from home_service import buscar_dashboard, obter_checkins_mes, registrar_checkin, registrar_checkout


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


def carregar_checkin_hoje():
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

if "mostrar_form_checkin" not in st.session_state:
    st.session_state.mostrar_form_checkin = False

st.divider()

hoje = datetime.now().date()
checkin_hoje, erro_checkin = carregar_checkin_hoje()

if checkin_hoje is None and st.session_state.mostrar_form_checkin:
    coluna_esquerda, coluna_meio, coluna_direita = st.columns([1, 2, 1])
    with coluna_meio:
        with st.form("form_checkin"):
            st.markdown("### Registrar Check-in")
            data_checkin = st.date_input("Data", value=hoje)
            hora_checkin = st.time_input("Horário do Check-in", value=datetime.now().time())
            status_checkin = st.selectbox("Status do dia", ["Presente", "Folga", "Ausente"], index=0)
            observacao_checkin = st.text_area("Observação", value=st.session_state.get("observacao_dia", ""), height=120)

            col_submit, col_cancel = st.columns([2, 1])
            with col_submit:
                enviar = st.form_submit_button("Salvar Check-in")
            with col_cancel:
                cancelar = st.form_submit_button("Cancelar")

            if enviar:
                ok, erro = registrar_checkin(
                    data_checkin.isoformat(),
                    datetime.combine(data_checkin, hora_checkin).isoformat(),
                    status=status_checkin,
                    observacao=observacao_checkin,
                )
                if ok:
                    st.success("Check-in registrado com sucesso.")
                    st.session_state.mostrar_form_checkin = False
                    st.experimental_rerun()
                else:
                    st.error(erro)
            if cancelar:
                st.session_state.mostrar_form_checkin = False
                st.experimental_rerun()

elif checkin_hoje is None:
    col_status, col_botao, col_info = st.columns([2, 2, 4])
    with col_status:
        st.write("### Check-in diário")
        st.write("Nenhum check-in registrado para hoje.")
    with col_botao:
        if st.button("✅ Fazer Check-in", key="btn_open_checkin"):
            st.session_state.mostrar_form_checkin = True
            st.experimental_rerun()
    with col_info:
        if erro_checkin:
            st.warning(f"Não foi possível carregar os check-ins: {erro_checkin}")
        else:
            st.info("Clique em 'Fazer Check-in' para registrar o início do seu dia.")

elif checkin_hoje.get("checkout") is None:
    col_status, col_botao, col_info = st.columns([2, 2, 4])
    with col_status:
        st.write("### Check-in de hoje")
        st.write(f"Entrada: {checkin_hoje.get('checkin')}")
        st.write(f"Status atual: {checkin_hoje.get('status')}")
    with col_botao:
        if st.button("⏹️ Fazer Check-out", key="btn_checkout"):
            ok, erro = registrar_checkout(
                int(checkin_hoje["id"]),
                datetime.now().isoformat(),
                status=checkin_hoje.get("status", "Presente"),
            )
            if ok:
                st.success("Check-out registrado com sucesso.")
                st.experimental_rerun()
            else:
                st.error(erro)
    with col_info:
        if erro_checkin:
            st.warning(f"Não foi possível carregar os check-ins: {erro_checkin}")
        else:
            st.info("Você já fez o check-in. Use o botão para registrar o check-out quando terminar.")

else:
    col_status, col_info = st.columns([2, 6])
    with col_status:
        st.success("Check-in e check-out registrados para hoje.")
        st.write(f"Entrada: {checkin_hoje.get('checkin')}")
        st.write(f"Saída: {checkin_hoje.get('checkout')}")
    with col_info:
        if checkin_hoje.get('observacao'):
            st.write(f"Observação: {checkin_hoje.get('observacao')}")

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