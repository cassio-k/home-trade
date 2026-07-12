import streamlit as st
import requests
from datetime import datetime, time
import io
from streamlit_paste_button import paste_image_button
import hashlib

st.set_page_config(layout="wide", page_title="Diário de Trade", page_icon="📝")
API_URL = "http://127.0.0.1:8000/api"


# --- INICIALIZAÇÃO DA MEMÓRIA DE ESTADO (STATE MANAGEMENT) ---
ESTADOS_PADRAO = {
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
    "form_relatorio": ""
}

for chave, valor in ESTADOS_PADRAO.items():
    if chave not in st.session_state:
        st.session_state[chave] = valor


# --- BARRA LATERAL (VERSÃO DINÂMICA E AUTOMATIZADA) ---
with st.sidebar:
    st.header("Gerenciar diário")
    
    # Captura a data de hoje baseada no sistema (Julho de 2026)
    hoje = datetime.now()
    
    # Lista de anos dinâmica (adiciona o ano atual automaticamente se não estiver na lista)
    anos_disponiveis = [2026, 2025, 2024]
    if hoje.year not in anos_disponiveis:
        anos_disponiveis.insert(0, hoje.year)
        
    ano_sel = st.selectbox("Selecione o Ano", anos_disponiveis, index=anos_disponiveis.index(hoje.year))
    
    # Mapeamento completo dos 12 meses do ano
    meses_lista = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    
    # Gera as pastas automaticamente combinando a lista com o ano selecionado
    pastas_dinamicas = [f"{mes} - {ano_sel}" for mes in meses_lista]
    
    # Define o index padrão: se o usuário selecionar o ano atual, o app já abre no mês corrente
    if ano_sel == hoje.year:
        index_padrao = hoje.month - 1  # Subtrai 1 porque arrays começam em 0 (Julho = index 6)
    else:
        index_padrao = 0
        
    pasta_sel = st.selectbox(
        "Selecione a pasta", 
        options=pastas_dinamicas, 
        index=index_padrao
    )
    
    st.divider()
    
    # Carrega a lista de trades salvos para o período selecionado
    lista_trades = []
    try:
        res = requests.get(f"{API_URL}/trades", params={"ano": ano_sel, "mes_nome": pasta_sel}, timeout=5)
        
        if res.status_code == 200:
            lista_trades = res.json()
        else:
            # Exibe o erro real na tela em vez de quebrar o script com um TypeError
            st.error(f"Erro {res.status_code} da API: {res.json().get('detail', res.text)}")
            
    except requests.exceptions.RequestException as e:
        st.error(f"Não foi possível conectar ao servidor: {e}")

    # --- LISTAS GLOBAIS DE MAPEAMENTO DIRETO ---
    SETUPS_MAPPING = ["123", "Gift", "Pullback", "Barra ignorada", "Pivo", "Rompimento", "Reversão", "Fibonacci", "Gap de venda", "Barra de ignição"]
    EMOTIONS_MAPPING = ["Neutro", "Focado", "Ansioso", "Desatento"] # Alinhe com a ordem dos IDs do seu banco (1, 2, 3...)

    # Renderiza os botões dinâmicos de cada trade
    for t in lista_trades:
        dt_objeto = datetime.fromisoformat(t["data_trade"])
        label_botao = f"{t['ativo']} | {dt_objeto.strftime('%d/%m')}"
        
        if st.button(label_botao, key=f"btn_trade_{t['id']}", use_container_width=True):
            # Carrega dados do item clicado para a memória do formulário
            dados_item = requests.get(f"{API_URL}/trades/{t['id']}").json()
            st.session_state.trade_ativo_id = dados_item["id"]
            st.session_state.form_data = datetime.fromisoformat(dados_item["data_trade"]).date()
            st.session_state.form_hora = datetime.fromisoformat(dados_item["data_trade"]).time()
            st.session_state.form_direcao = dados_item["ordem"]
            st.session_state.form_ativo = dados_item["ativo"]
            st.session_state.form_qtd = dados_item["quantidade"]
            st.session_state.form_pe = dados_item["preco_entrada"]
            st.session_state.form_ps = dados_item["preco_saida"]
            st.session_state.form_resultado = dados_item.get("resultado", 0.0)

            id_setup_banco = dados_item.get("setup_id", 1)
            st.session_state.form_setup = SETUPS_MAPPING[id_setup_banco - 1] if 1 <= id_setup_banco <= len(SETUPS_MAPPING) else "123"
            id_emotion_banco = dados_item.get("emocional_id", 4)
            st.session_state.form_emocional = EMOTIONS_MAPPING[id_emotion_banco - 1] if 1 <= id_emotion_banco <= len(EMOTIONS_MAPPING) else "Neutro"
            
            st.session_state.form_url = dados_item.get("url_imagem", "")
            st.session_state.form_relatorio = dados_item.get("relatorio", "")
            st.rerun()

    st.divider()

    # --- O BOTÃO QUE ESTAVA MORTO COORDENADO COM O ESTADO ---
    if st.button("➕ Add Trade", key="btn_sidebar_add_trade_novo", use_container_width=True):
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
        st.toast("Formulário limpo para inserção!", icon="📝")
        st.rerun()

# --- CORPO PRINCIPAL (DIARIOTRADE) ---
st.title("DiarioTrade")

with st.expander("🧠 Filtros de Mentalidade Operacional", expanded=False):
    st.checkbox("No mercado tudo pode acontecer", value=True, key="m1")
    st.checkbox("Para ganhar dinheiro não precisamos saber o que vai acontecer a seguir", value=True, key="m2")
    st.checkbox("Uma estratégia não é mais do que uma indicação de uma maior probabilidade", value=True, key="m3")
    st.checkbox("Um trade de cada vez", value=True, key="m4")
    st.checkbox("Menos é mais", value=True, key="m5")

st.divider()

col_dados, col_grafico = st.columns([1, 1])

with col_dados:
    st.subheader("Dados da Operação")
    
    col_d, col_h = st.columns(2)
    with col_d:
        data_input = st.date_input("Data do Trade", value=st.session_state.form_data)
    with col_h:
        horario_input = st.time_input("Horário", value=st.session_state.form_hora)
    
    direcao = st.selectbox("Direção", ["Buy", "Sell"], index=0 if st.session_state.form_direcao == "Buy" else 1)
    ativo = st.text_input("Ativo", value=st.session_state.form_ativo).strip()
    
    # Garantia de Tipagem contra nulos do banco legado
    val_qtd = int(st.session_state.form_qtd) if st.session_state.form_qtd is not None else 100
    val_pe = float(st.session_state.form_pe) if st.session_state.form_pe is not None else 0.0
    val_ps = float(st.session_state.form_ps) if st.session_state.form_ps is not None else 0.0
    val_setup = st.session_state.form_setup if st.session_state.form_setup is not None else "123"
    val_emocional = st.session_state.form_emocional if st.session_state.form_emocional is not None else "Neutro"


    col_q, col_pe, col_ps = st.columns(3)
    with col_q:
        quantidade = st.number_input("Quantidade", min_value=1, value=val_qtd, step=1)
    with col_pe:
        preco_in = st.number_input("Preço Entrada", min_value=0.0, value=val_pe, step=0.01)
    with col_ps:
        preco_out = st.number_input("Preço Saída", min_value=0.0, value=val_ps, step=0.01)


    SETUPS_DISPONIVEIS = ["123", "Gift", "Pullback", "Barra ignorada", "Pivo", "Rompimento", "Reversão", "Fibonacci", "Gap de venda", "Barra de ignição"]
    EMOCIONAIS_DISPONIVEIS = ["Desatento", "Ansioso", "Focado", "Neutro"]

    col_s, col_e = st.columns(2)
    with col_s:
        setup_selecionado = st.selectbox(
        "Setup", 
        options=SETUPS_DISPONIVEIS, 
        index=SETUPS_DISPONIVEIS.index(st.session_state.get("form_setup", "123")))
        st.session_state.form_setup = setup_selecionado

    with col_e:
        emocional_selecionado = st.select_slider(
        "Emocional", 
        options=EMOCIONAIS_DISPONIVEIS, 
        value=st.session_state.get("form_emocional", "Neutro"))
        st.session_state.form_emocional = emocional_selecionado
 
    resultado = st.number_input("Resultado (R$)", value=float(st.session_state.form_resultado), step=0.01)
    st.session_state.form_resultado = resultado 

# --- COLUNA DO GRÁFICO ---
with col_grafico:
    st.subheader("Gráfico da Operação")
        
    pasted = paste_image_button("Grafico", key=f"p_btn_{ativo if ativo else 'novo'}")

    if pasted.image_data is not None:
        # 1. Cria uma assinatura digital única com base nos bytes da imagem colada
        bytes_puros = pasted.image_data.tobytes()
        hash_atual = hashlib.md5(bytes_puros).hexdigest()
        
        # 2. SÓ dispara o upload se essa imagem específica ainda não tiver sido enviada
        if st.session_state.get("ultimo_hash_enviado") != hash_atual:
            img_bytes = io.BytesIO()
            pasted.image_data.save(img_bytes, format="PNG")
            img_bytes.seek(0)
            
            try:
                files = {"file": ("screenshot.png", img_bytes, "image/png")}
                res_upload = requests.post(f"{API_URL}/upload", files=files, timeout=10)
                
                if res_upload.status_code == 200:
                    st.session_state.form_url = res_upload.json()["url_imagem"]
                    # 3. Memoriza o hash da imagem para bloquear reenvios no próximo rerun
                    st.session_state.ultimo_hash_enviado = hash_atual
                    st.toast("Gráfico processado com sucesso!", icon="📸")
                    st.rerun()
                else:
                    st.error("Falha ao salvar a imagem no Storage do Supabase.")
            except Exception as e:
                st.error(f"Erro de comunicação com a API: {e}")

    # --- ESPAÇO DEDICADO PARA EXIBIÇÃO DA IMAGEM ---
    if st.session_state.form_url.strip():
        st.image(st.session_state.form_url, use_container_width=True)
    else:
        st.info("Nenhum gráfico anexado a esta operação.")


st.subheader("Observações")
relatorio = st.text_area("Relatório", value=st.session_state.form_relatorio, height=100, label_visibility="collapsed")

st.divider()

# --- BOTÕES DE COMPOSIÇÃO DE SALVAMENTO/EXCLUSÃO ---
col_salvar, col_deletar = st.columns([5, 2])

with col_salvar:
    texto_botao = "💾 ATUALIZAR ALTERAÇÕES" if st.session_state.trade_ativo_id else "💾 FINALIZAR E SALVAR"
    if st.button(texto_botao, type="primary", use_container_width=True):
        timestamp_combinado = datetime.combine(data_input, horario_input).isoformat()
        payload = {
            "data_trade": timestamp_combinado, "ativo": ativo, "ordem": direcao, "quantidade": quantidade,
            "preco_entrada": preco_in, "preco_saida": preco_out, "resultado": resultado, "relatorio": relatorio,
            "setup_id": setup_selecionado, "emocional_id": emocional_selecionado, "is_legado": False, "url_imagem": st.session_state.form_url
        }
        
        if st.session_state.trade_ativo_id:
            # Rota PUT (Edição)
            res = requests.put(f"{API_URL}/trades/{st.session_state.trade_ativo_id}", json=payload)
        else:
            # Rota POST (Inserção)
            res = requests.post(f"{API_URL}/trades", json=payload)
            
        if res.status_code == 200:
            st.toast("Operação salva com sucesso no Supabase!", icon="✅")
            st.session_state.trade_ativo_id = None
            st.rerun()
        else:
            st.error(f"Erro no processamento: {res.text}")

with col_deletar:
    if st.session_state.trade_ativo_id:
        if st.button("🗑️ APAGAR DO BANCO", type="secondary", use_container_width=True):
            requests.delete(f"{API_URL}/trades/{st.session_state.trade_ativo_id}")
            st.session_state.trade_ativo_id = None
            st.rerun()