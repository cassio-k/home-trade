import streamlit as st
import requests

st.set_page_config(layout="wide", page_title="Biblioteca - Conhecimento", page_icon="📚")
API_URL = "http://127.0.0.1:8000/api/biblioteca"

# --- CONTROLE DE ESTADO LOCAL ---
if "categoria_ativa" not in st.session_state: st.session_state.categoria_ativa = "Geral"
if "nota_ativa_id" not in st.session_state: st.session_state.nota_ativa_id = None
if "memoria_conteudo" not in st.session_state: st.session_state.memoria_conteudo = ""
if "memoria_titulo" not in st.session_state: st.session_state.memoria_titulo = ""
if "memoria_anexos" not in st.session_state: st.session_state.memoria_anexos = []

# --- CARREGA CATEGORIAS DO BANCO ---
try:
    lista_categorias = requests.get(f"{API_URL}/categorias").json()
except Exception:
    st.error("Erro crítico: O backend está inacessível.")
    st.stop()

# --- SIDEBAR: NAVEGAÇÃO ---
with st.sidebar:
    st.header("📁 Pastas / Categorias")
    for cat in lista_categorias:
        if st.button(f"📁 {cat}", key=f"cat_{cat}", use_container_width=True):
            st.session_state.categoria_ativa = cat
            st.session_state.nota_ativa_id = None  # Reseta seleção de nota
            st.rerun()
            
    st.divider()
    st.subheader(f"📝 Notas em '{st.session_state.categoria_ativa}'")
    
    # Criar nota rápida dentro da categoria ativa
    if st.button("➕ Nova Nota", use_container_width=True):
        payload_nova = {"titulo": "Nova Nota", "categoria": st.session_state.categoria_ativa, "conteudo": ""}
        res = requests.post(f"{API_URL}/notas", json=payload_nova).json()
        if res:
            st.session_state.nota_ativa_id = res["id"]
            st.rerun()

    # Listagem das notas existentes nesta categoria
    params = {"categoria": st.session_state.categoria_ativa}
    notas = requests.get(f"{API_URL}/notas", params=params).json()
    for nota in notas:
        if st.button(f"📄 {nota['titulo']}", key=f"nota_btn_{nota['id']}", use_container_width=True):
            detalhe = requests.get(f"{API_URL}/notas/{nota['id']}").json()
            st.session_state.nota_ativa_id = detalhe["id"]
            st.session_state.memoria_titulo = detalhe["titulo"]
            st.session_state.memoria_conteudo = detalhe["conteudo"]
            st.session_state.memoria_anexos = detalhe.get("anexos", [])
            st.rerun()

# --- PAINEL PRINCIPAL (DASHBOARD DE CONHECIMENTO) ---
if not st.session_state.nota_ativa_id:
    st.title("Explorar Conteúdo")
    st.info("Selecione uma categoria e um documento na barra lateral para carregar os slides de estudo.")
    st.stop()

# Cabeçalho de manipulação do registro
col_tit, col_del = st.columns([6, 1])
with col_tit:
    st.session_state.memoria_titulo = st.text_input("Título", value=st.session_state.memoria_titulo, label_visibility="collapsed")
with col_del:
    if st.button("🗑️ Excluir", use_container_width=True):
        requests.delete(f"{API_URL}/notas/{st.session_state.nota_ativa_id}")
        st.session_state.nota_ativa_id = None
        st.rerun()

st.divider()

# Bloco de Conteúdo Textual (Mapeado direto na coluna 'conteudo' da tabela 'biblioteca')
st.markdown("### 📝 Anotações de Estudo")
st.session_state.memoria_conteudo = st.text_area(
    "Conteúdo de texto", 
    value=st.session_state.memoria_conteudo, 
    height=200, 
    label_visibility="collapsed"
)

st.divider()

# Bloco de Imagens Dinâmicas (Mapeado na tabela 'anexos_biblioteca')
st.markdown("### 🖼️ Slides e Capturas de Tela")

anexos_atualizados = []
for idx, url in enumerate(st.session_state.memoria_anexos):
    col_img_input, col_img_del = st.columns([6, 1])
    
    with col_img_input:
        url_editada = st.text_input(f"URL do Slide #{idx + 1}", value=url, key=f"url_anexo_{idx}")
        anexos_atualizados.append(url_editada)
    with col_img_del:
        if st.button("❌ Remover", key=f"del_anexo_{idx}", use_container_width=True):
            st.session_state.memoria_anexos.pop(idx)
            st.rerun()
            
    if url_editada.strip():
        st.image(url_editada, use_container_width=True)
    st.divider()

st.session_state.memoria_anexos = anexos_atualizados

# --- BOTÕES DE COMPOSIÇÃO INFERIORES ---
col_add_slide, col_save_doc = st.columns(2)

with col_add_slide:
    if st.button("➕ Adicionar Próximo Slide / Imagem", use_container_width=True):
        st.session_state.memoria_anexos.append("")
        st.rerun()

with col_save_doc:
    if st.button("💾 Gravar Alterações no Banco", type="primary", use_container_width=True):
        payload_salvar = {
            "titulo": st.session_state.memoria_titulo,
            "conteudo": st.session_state.memoria_conteudo,
            "categoria": st.session_state.categoria_ativa,
            "anexos": st.session_state.memoria_anexos
        }
        res = requests.put(f"{API_URL}/notas/{st.session_state.nota_ativa_id}", json=payload_salvar).json()
        if res.get("status") == "sucesso":
            st.toast("Estudo sincronizado com sucesso!", icon="✅")