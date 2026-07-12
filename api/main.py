import sys
from pathlib import Path

pasta_api = Path(__file__).resolve().parent
if str(pasta_api) not in sys.path:
    sys.path.insert(0, str(pasta_api))

from fastapi import FastAPI, HTTPException, Body, Query, UploadFile, File
from typing import List
from datetime import datetime

from database import supabase
from schemas import TradeInferenciaSchema
import calendar
from pydantic import BaseModel, Field
from typing import Optional
import time

app = FastAPI(title="TradeHome API", version="1.0.0")


####################
# ENDPOINTS DIARIO #
#################### 

@app.get("/api/trades")
def listar_trades_diario(ano: int = Query(...), mes_nome: str = Query(...)):
    try:
        meses_map = {
            "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4,
            "Maio": 5, "Junho": 6, "Julho": 7, "Agosto": 8,
            "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
        }
        
        nome_puro = mes_nome.split(" - ")[0]
        num_mes = meses_map.get(nome_puro, 1)
        
        # Calcula o último dia do mês de forma segura (calcula anos bissextos automaticamente)
        _, ultimo_dia = calendar.monthrange(ano, num_mes)
        
        # Formata strings de ISO timestamp para delimitar o início e o fim exatos do mês
        data_inicio = f"{ano}-{num_mes:02d}-01T00:00:00"
        data_fim = f"{ano}-{num_mes:02d}-{ultimo_dia:02d}T23:59:59"
        
        # Correção estrutural: usando gte (>=) e lte (<=) compatíveis com timestamp
        resposta = supabase.table("trades") \
            .select("id", "ativo", "data_trade") \
            .gte("data_trade", data_inicio) \
            .lte("data_trade", data_fim) \
            .order("data_trade", desc=False) \
            .execute()
            
        return resposta.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno no banco: {str(e)}")
    

@app.get("/api/trades/{trade_id}")
def obter_detalhe_trade(trade_id: int):
    # Busca dados do trade
    res_trade = supabase.table("trades").select("*").eq("id", trade_id).single().execute()
    trade = res_trade.data
    
    # Busca a imagem correspondente na tabela filha anexos_trades
    res_anexo = supabase.table("anexos_trades").select("url_imagem").eq("trade_id", trade_id).execute()
    trade["url_imagem"] = res_anexo.data[0]["url_imagem"] if res_anexo.data else ""
    return trade

@app.post("/api/trades")
def cadastrar_trade_diario(trade: dict = Body(...)):
    try:
        # 1. TRADUÇÃO DOS TEXTOS BRUTOS PARA IDs DO BANCO
        nome_setup = trade.get("setup_id", "123")
        res_setup = supabase.table("setup").select("id").eq("nome", nome_setup).execute()  
        id_setup = res_setup.data[0]["id"] if res_setup.data else 1

        nome_emocional = trade.get("emocional_id", "Neutro")
        res_emocional = supabase.table("emotion").select("id").eq("nome", nome_emocional).execute() 
        id_emocional = res_emocional.data[0]["id"] if res_emocional.data else 3

        # 2. INSERÇÃO COM OS IDs JA RESOLVIDOS
        res_trade = supabase.table("trades").insert({
            "data_trade": trade.get("data_trade"),
            "ativo": trade.get("ativo", "").upper(),
            "ordem": trade.get("ordem"),
            "quantidade": int(trade.get("quantidade", 1)),
            "preco_entrada": float(trade.get("preco_entrada", 0)),
            "preco_saida": float(trade.get("preco_saida", 0)),
            "resultado": float(trade.get("resultado", 0)),
            "relatorio": trade.get("relatorio"),
            "setup_id": id_setup,        # Linha 81 corrigida
            "emocional_id": id_emocional,  # Linha 82 corrigida
            "is_legado": bool(trade.get("is_legado", False))
        }).execute()

        trade_id = res_trade.data[0]["id"]
        url_img = trade.get("url_imagem")
        if url_img and url_img.strip():
            supabase.table("anexos_trades").insert({"trade_id": trade_id, "url_imagem": url_img}).execute()

        return res_trade.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/trades/{trade_id}")
def atualizar_trade_diario(trade_id: int, trade: dict = Body(...)):
    try:
        # 1. TRADUÇÃO DOS TEXTOS BRUTOS PARA IDs DO BANCO
        nome_setup = trade.get("setup_id", "123")
        res_setup = supabase.table("setup").select("id").eq("nome", nome_setup).execute()  
        id_setup = res_setup.data[0]["id"] if res_setup.data else 1

        nome_emocional = trade.get("emocional_id", "Neutro")
        res_emocional = supabase.table("emotion").select("id").eq("nome", nome_emocional).execute()  
        id_emocional = res_emocional.data[0]["id"] if res_emocional.data else 3

        # 2. ATUALIZAÇÃO COM OS IDs JA RESOLVIDOS
        supabase.table("trades").update({
            "data_trade": trade.get("data_trade"),
            "ativo": trade.get("ativo", "").upper(),
            "ordem": trade.get("ordem"),
            "quantidade": int(trade.get("quantidade", 1)),
            "preco_entrada": float(trade.get("preco_entrada", 0)),
            "preco_saida": float(trade.get("preco_saida", 0)),
            "resultado": float(trade.get("resultado", 0)),
            "relatorio": trade.get("relatorio"),
            "setup_id": id_setup,        # Linha 107 corrigida
            "emocional_id": id_emocional,  # Linha 108 corrigida
        }).eq("id", trade_id).execute()

        supabase.table("anexos_trades").delete().eq("trade_id", trade_id).execute()
        url_img = trade.get("url_imagem")
        if url_img and url_img.strip():
            supabase.table("anexos_trades").insert({"trade_id": trade_id, "url_imagem": url_img}).execute()

        return {"status": "atualizado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload")
def upload_grafico(file: UploadFile = File(...)):
    try:
        extensao = file.filename.split(".")[-1] if "." in file.filename else "png"
        nome_unico = f"chart_{int(time.time() * 1000)}.{extensao}"
        conteudo_arquivo = file.file.read()
        
        supabase.storage.from_("prints_trades").upload(
            path=nome_unico,
            file=conteudo_arquivo,
            file_options={"content-type": f"image/{extensao}"}
        )
        
        url_publica = supabase.storage.from_("prints_trades").get_public_url(nome_unico)
        return {"url_imagem": url_publica}
    except Exception as e:
        # ISSO VAI EXPOR O COLO DO ERRO NO SEU TERMINAL:
        print("\n" + "="*50)
        print(f"ERRO CRÍTICO NO UPLOAD: {str(e)}")
        print("="*50 + "\n")
        raise HTTPException(status_code=500, detail=str(e))
    

@app.delete("/api/trades/{trade_id}")
def deletar_trade_diario(trade_id: int):
    supabase.table("anexos_trades").delete().eq("trade_id", trade_id).execute()
    supabase.table("trades").delete().eq("id", trade_id).execute()
    return {"status": "deletado"}

#AREA DE TRADUÇÃO SETUP/EMOCIONAL#

@app.post("/api/trades")
def salvar_trade(trade: TradeInferenciaSchema):
    # 1. Traduz o nome do setup para o ID correspondente da tabela fixa
    res_setup = supabase.table("setups").select("id").eq("nome", trade.setup_nome).execute()
    setup_id = res_setup.data[0]["id"] if res_setup.data else 1 # fallback para o ID 1 se não achar

    # 2. Traduz o nome do emocional para o ID correspondente da tabela fixa
    res_emocional = supabase.table("emocionais").select("id").eq("nome", trade.emocional_nome).execute()
    emocional_id = res_emocional.data[0]["id"] if res_emocional.data else 3 # fallback

    # 3. Monta o payload relacional correto para o banco
    payload_banco = {
        "setup_id": setup_id,
        "emocional_id": emocional_id,
        # ... seus outros campos ...
    }
    
    supabase.table("trades").insert(payload_banco).execute()
    return {"status": "sucesso"}

@app.get("/api/trades/{trade_id}")
def obter_trade(trade_id: int):
    # Busca o trade bruto
    trade = supabase.table("trades").select("*").eq("id", trade_id).single().execute().data
    
    # Traduz os IDs numéricos de volta para os nomes textuais antes de enviar para a tela
    nome_setup = supabase.table("setups").select("nome").eq("id", trade["setup_id"]).single().execute().data["nome"]
    nome_emocional = supabase.table("emocionais").select("nome").eq("id", trade["emocional_id"]).single().execute().data["nome"]
    
    # Injeta os nomes amigáveis na resposta
    trade["setup_nome"] = nome_setup
    trade["emocional_name"] = nome_emocional
    
    return trade


#######################
#### ENDPOINTS HOME ###
####################### 

from fastapi import Query
from collections import defaultdict

@app.get("/api/Home")
def obter_dados_dashboard(
    mes: str = Query(None),
    ativo: str = Query(None),
    setup_id: str = Query(None)
):
    # 1. Busca os dados brutos no Supabase
    resposta = supabase.table("trades").select("*").order("data_trade", desc=False).execute()
    todos_trades = resposta.data

    # 2. Filtragem Inteligente no Backend
    trades_filtrados = []
    for t in todos_trades:
        # Extrações de tempo para consistência dos filtros
        # Adaptar chaves de acordo com o retorno real da sua tabela
        data_str = t.get("data_trade", "")
        
        # Filtro por Mês (Exemplo de formato: "2026-07")
        if mes and not data_str.startswith(mes):
            continue
        if ativo and t.get("ativo") != ativo:
            continue
        if setup_id and str(t.get("setup_id")) != setup_id:
            continue
            
        trades_filtrados.append(t)

    # 3. Processamento do Resumo Estatístico
    total_trades = len(trades_filtrados)
    lucro_total = sum(float(t.get("resultado", 0)) for t in trades_filtrados)
    
    trades_ganhos = sum(1 for t in trades_filtrados if float(t.get("resultado", 0)) > 0)
    taxa_acerto = (trades_ganhos / total_trades * 100) if total_trades > 0 else 0.0

    # 4. Construção da Curva de Capital (Equity Curve)
    curva_capital = []
    saldo_acumulado = 0.0
    for t in trades_filtrados:
        saldo_acumulado += float(t.get("resultado", 0))
        curva_capital.append({
            "data_trade": t.get("data_trade"),
            "saldo": saldo_acumulado
        })

    # 5. Agrupamentos para os Gráficos de Barras (Performance)
    perf_setup = defaultdict(float)
    perf_emocional = defaultdict(float)
    perf_ativo = defaultdict(float)

    for t in trades_filtrados:
        res = float(t.get("resultado", 0))
        perf_setup[str(t.get("setup_id", "Sem Setup"))] += res
        perf_emocional[str(t.get("emocional_id", "Neutro"))] += res
        perf_ativo[str(t.get("ativo", "Desconhecido"))] += res

    # 6. Retorno Consolidado (Payload Único)
    return {
        "metricas": {
            "lucro_total": lucro_total,
            "total_trades": total_trades,
            "taxa_acerto": round(taxa_acerto, 1)
        },
        "historico": trades_filtrados,  # Dados puros para a tabela e calendário
        "graficos": {
            "curva_capital": curva_capital,
            "performance_setup": dict(perf_setup),
            "performance_emocional": dict(perf_emocional),
            "performance_ativo": dict(perf_ativo)
        }
    }


########################
# ENDPOINTS BIBLIOTECA #
########################

from fastapi import Body, Query

@app.get("/api/biblioteca/categorias")
def listar_categorias_existentes():
    # Coleta as categorias diretamente do seu campo 'categoria' da tabela 'biblioteca'
    resposta = supabase.table("biblioteca").select("categoria").execute()
    # Filtra valores únicos e remove nulos para montar os botões da barra lateral
    categorias = sorted(list(set([r["categoria"] for r in resposta.data if r.get("categoria")])))
    if not categorias:
        categorias = ["Geral", "Livros", "Estudos"]  # Fallback inicial se o banco estiver vazio
    return categorias

@app.get("/api/biblioteca/notas")
def listar_notas_por_categoria(categoria: str = Query(...)):
    # Busca títulos filtrando pela coluna 'categoria' da sua tabela 'biblioteca'
    resposta = supabase.table("biblioteca").select("id", "titulo", "categoria").eq("categoria", categoria).execute()
    return resposta.data

@app.get("/api/biblioteca/notas/{nota_id}")
def obter_detalhe_nota_completa(nota_id: int):
    # 1. Busca os dados textuais da nota principal
    nota_res = supabase.table("biblioteca").select("*").eq("id", nota_id).single().execute()
    nota = nota_res.data
    
    # 2. Busca todas as URLs de slides vinculadas na sua tabela 'anexos_biblioteca'
    anexos_res = supabase.table("anexos_biblioteca").select("url_imagem").eq("biblioteca_id", nota_id).execute()
    nota["anexos"] = [item["url_imagem"] for item in anexos_res.data] if anexos_res.data else []
    
    return nota

@app.post("/api/biblioteca/notas")
def criar_nova_nota(dados: dict = Body(...)):
    # Cria registro usando as colunas exatas da sua tabela 'biblioteca'
    payload = {
        "titulo": dados.get("titulo", "Sem Título"),
        "categoria": dados.get("categoria", "Geral"),
        "conteudo": dados.get("conteudo", "")
    }
    resposta = supabase.table("biblioteca").insert(payload).execute()
    return resposta.data[0] if resposta.data else {}

@app.put("/api/biblioteca/notas/{nota_id}")
def atualizar_nota_e_anexos(nota_id: int, dados: dict = Body(...)):
    # 1. Atualiza as colunas de texto 'titulo' e 'conteudo' na tabela 'biblioteca'
    supabase.table("biblioteca").update({
        "titulo": dados.get("titulo"),
        "conteudo": dados.get("conteudo"),
        "categoria": dados.get("categoria")
    }).eq("id", nota_id).execute()
    
    # 2. Sincroniza as imagens na tabela 'anexos_biblioteca' (Limpa as antigas e insere as atuais)
    supabase.table("anexos_biblioteca").delete().eq("biblioteca_id", nota_id).execute()
    
    novas_urls = dados.get("anexos", [])
    payload_anexos = [{"biblioteca_id": nota_id, "url_imagem": url} for url in novas_urls if url.strip()]
    
    if payload_anexos:
        supabase.table("anexos_biblioteca").insert(payload_anexos).execute()
    return {"status": "sucesso"}

@app.delete("/api/biblioteca/notas/{nota_id}")
def deletar_nota_completa(nota_id: int):
    # Remove os vínculos primeiro para evitar quebra de chave estrangeira
    supabase.table("anexos_biblioteca").delete().eq("biblioteca_id", nota_id).execute()
    supabase.table("biblioteca").delete().eq("id", nota_id).execute()
    return {"status": "sucesso"}