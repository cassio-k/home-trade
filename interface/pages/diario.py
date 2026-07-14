import hashlib
import io
from datetime import datetime

import streamlit as st
from streamlit_paste_button import paste_image_button

from diario_service import (
    EMOCIONAIS_DISPONIVEIS,
    SETUPS_DISPONIVEIS,
    carregar_trade_no_form,
    carregar_trade_por_id,
    carregar_trades_mes,
    construir_payload,
    enviar_imagem_para_api,
    excluir_trade,
    inicializar_estado,
    obter_indice_opcao,
    resetar_formulario,
    salvar_trade,
)

st.set_page_config(layout="wide", page_title="Diário de Trade", page_icon="📝")


def renderizar_sidebar():
    with st.sidebar:
        st.header("Gerenciar diário")

        hoje = datetime.now()
        anos_disponiveis = [2026, 2025, 2024]
        if hoje.year not in anos_disponiveis:
            anos_disponiveis.insert(0, hoje.year)

        ano_sel = st.selectbox("Selecione o Ano", anos_disponiveis, index=anos_disponiveis.index(hoje.year))
        meses_lista = [
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
        pastas_dinamicas = [f"{mes} - {ano_sel}" for mes in meses_lista]
        index_padrao = hoje.month - 1 if ano_sel == hoje.year else 0
        pasta_sel = st.selectbox("Selecione a pasta", options=pastas_dinamicas, index=index_padrao)

        st.divider()

        lista_trades = carregar_trades_mes(ano_sel, pasta_sel)
        if lista_trades:
            for trade in lista_trades:
                dt_objeto = datetime.fromisoformat(trade["data_trade"])
                label_botao = f"{trade['ativo']} | {dt_objeto.strftime('%d/%m')}"
                if st.button(label_botao, key=f"btn_trade_{trade['id']}", use_container_width=True):
                    ok, resultado = carregar_trade_por_id(trade["id"])
                    if ok:
                        carregar_trade_no_form(resultado)
                        st.rerun()
                    else:
                        st.error(resultado)
        else:
            st.info("Nenhum trade encontrado para este período.")

        st.divider()

        if st.button("➕ Add Trade", key="btn_sidebar_add_trade_novo", use_container_width=True):
            resetar_formulario()
            st.toast("Formulário limpo para inserção!", icon="📝")
            st.rerun()


def renderizar_filtros_mentais():
    with st.expander("🧠 Filtros de Mentalidade Operacional", expanded=False):
        st.checkbox("No mercado tudo pode acontecer", value=True, key="m1")
        st.checkbox("Para ganhar dinheiro não precisamos saber o que vai acontecer a seguir", value=True, key="m2")
        st.checkbox("Uma estratégia não é mais do que uma indicação de uma maior probabilidade", value=True, key="m3")
        st.checkbox("Um trade de cada vez", value=True, key="m4")
        st.checkbox("Menos é mais", value=True, key="m5")


def renderizar_formulario():
    st.title("DiarioTrade")
    renderizar_filtros_mentais()
    st.divider()

    col_dados, col_grafico = st.columns([1, 1])

    with col_dados:
        st.subheader("Dados da Operação")

        col_d, col_h = st.columns(2)
        with col_d:
            data_input = st.date_input("Data do Trade", value=st.session_state.form_data)
            st.session_state.form_data = data_input
        with col_h:
            horario_input = st.time_input("Horário", value=st.session_state.form_hora)
            st.session_state.form_hora = horario_input

        direcao = st.selectbox(
            "Direção",
            ["Buy", "Sell"],
            index=0 if st.session_state.form_direcao == "Buy" else 1,
        )
        st.session_state.form_direcao = direcao

        ativo = st.text_input("Ativo", value=st.session_state.form_ativo).strip()
        st.session_state.form_ativo = ativo

        val_qtd = int(st.session_state.form_qtd) if st.session_state.form_qtd is not None else 100
        val_pe = float(st.session_state.form_pe) if st.session_state.form_pe is not None else 0.0
        val_ps = float(st.session_state.form_ps) if st.session_state.form_ps is not None else 0.0

        col_q, col_pe, col_ps = st.columns(3)
        with col_q:
            quantidade = st.number_input("Quantidade", min_value=1, value=val_qtd, step=1)
            st.session_state.form_qtd = quantidade
        with col_pe:
            preco_in = st.number_input("Preço Entrada", min_value=0.0, value=val_pe, step=0.01)
            st.session_state.form_pe = preco_in
        with col_ps:
            preco_out = st.number_input("Preço Saída", min_value=0.0, value=val_ps, step=0.01)
            st.session_state.form_ps = preco_out

        col_s, col_e = st.columns(2)
        with col_s:
            setup_selecionado = st.selectbox(
                "Setup",
                options=SETUPS_DISPONIVEIS,
                index=obter_indice_opcao(st.session_state.get("form_setup", "123"), SETUPS_DISPONIVEIS, "123"),
            )
            st.session_state.form_setup = setup_selecionado

        with col_e:
            emocional_selecionado = st.select_slider(
                "Emocional",
                options=EMOCIONAIS_DISPONIVEIS,
                value=st.session_state.get("form_emocional", "Neutro"),
            )
            st.session_state.form_emocional = emocional_selecionado

        resultado = st.number_input("Resultado (R$)", value=float(st.session_state.form_resultado), step=0.01)
        st.session_state.form_resultado = resultado

    with col_grafico:
        st.subheader("Gráfico da Operação")
        pasted = paste_image_button("Grafico", key=f"p_btn_{ativo if ativo else 'novo'}")

        if pasted.image_data is not None:
            bytes_puros = pasted.image_data.tobytes()
            hash_atual = hashlib.md5(bytes_puros).hexdigest()

            if st.session_state.get("ultimo_hash_enviado") != hash_atual:
                img_bytes = io.BytesIO()
                pasted.image_data.save(img_bytes, format="PNG")
                img_bytes.seek(0)

                ok, resposta = enviar_imagem_para_api(img_bytes.getvalue())
                if ok:
                    st.session_state.form_url = resposta
                    st.session_state.ultimo_hash_enviado = hash_atual
                    st.toast("Gráfico processado com sucesso!", icon="📸")
                    st.rerun()
                else:
                    st.error(resposta)

        if st.session_state.form_url.strip():
            st.image(st.session_state.form_url, use_container_width=True)
        else:
            st.info("Nenhum gráfico anexado a esta operação.")

    st.subheader("Observações")
    relatorio = st.text_area("Relatório", value=st.session_state.form_relatorio, height=100, label_visibility="collapsed")
    st.session_state.form_relatorio = relatorio

    st.divider()

    col_salvar, col_deletar = st.columns([5, 2])
    with col_salvar:
        texto_botao = "💾 ATUALIZAR ALTERAÇÕES" if st.session_state.trade_ativo_id else "💾 FINALIZAR E SALVAR"
        if st.button(texto_botao, type="primary", use_container_width=True):
            payload = construir_payload(
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
                st.session_state.form_url,
            )

            ok, erro = salvar_trade(payload, trade_id=st.session_state.trade_ativo_id)
            if ok:
                st.toast("Operação salva com sucesso no Supabase!", icon="✅")
                resetar_formulario()
                st.rerun()
            else:
                st.error(erro)

    with col_deletar:
        if st.session_state.trade_ativo_id:
            if st.button("🗑️ APAGAR DO BANCO", type="secondary", use_container_width=True):
                ok, erro = excluir_trade(st.session_state.trade_ativo_id)
                if ok:
                    resetar_formulario()
                    st.rerun()
                else:
                    st.error(erro)


inicializar_estado()
renderizar_sidebar()
renderizar_formulario()