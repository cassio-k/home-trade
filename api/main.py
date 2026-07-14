import calendar
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from fastapi import Body, FastAPI, File, HTTPException, Query, UploadFile

pasta_api = Path(__file__).resolve().parent
if str(pasta_api) not in sys.path:
    sys.path.insert(0, str(pasta_api))

from database import supabase

app = FastAPI(title="TradeHome API", version="1.0.0")

MESES_MAP = {
    "Janeiro": 1,
    "Fevereiro": 2,
    "Março": 3,
    "Abril": 4,
    "Maio": 5,
    "Junho": 6,
    "Julho": 7,
    "Agosto": 8,
    "Setembro": 9,
    "Outubro": 10,
    "Novembro": 11,
    "Dezembro": 12,
}

SETUP_TABLE = "setup"
EMOCION_TABLE = "emotion"


def _obter_numero_mes(mes_nome: str) -> int:
    nome_puro = mes_nome.split(" - ")[0].strip()
    return MESES_MAP.get(nome_puro, 1)


def _obter_intervalo_mes(ano: int, mes_nome: str) -> Tuple[str, str]:
    num_mes = _obter_numero_mes(mes_nome)
    _, ultimo_dia = calendar.monthrange(ano, num_mes)
    data_inicio = f"{ano}-{num_mes:02d}-01T00:00:00"
    data_fim = f"{ano}-{num_mes:02d}-{ultimo_dia:02d}T23:59:59"
    return data_inicio, data_fim


def _resolver_id_por_nome(tabela: str, valor: Any, default_id: int, campo: str = "nome") -> int:
    try:
        resposta = supabase.table(tabela).select("id").eq(campo, str(valor)).execute()
        dados = getattr(resposta, "data", []) or []
        if dados:
            return dados[0].get("id", default_id)
    except Exception:
        pass
    return default_id


def _montar_payload_trade(trade: Dict[str, Any]) -> Dict[str, Any]:
    setup_id = _resolver_id_por_nome(SETUP_TABLE, trade.get("setup_id", "123"), default_id=1)
    emocional_id = _resolver_id_por_nome(EMOCION_TABLE, trade.get("emocional_id", "Neutro"), default_id=3)

    return {
        "data_trade": trade.get("data_trade"),
        "ativo": str(trade.get("ativo", "")).upper(),
        "ordem": trade.get("ordem"),
        "quantidade": int(trade.get("quantidade", 1)),
        "preco_entrada": float(trade.get("preco_entrada", 0)),
        "preco_saida": float(trade.get("preco_saida", 0)),
        "resultado": float(trade.get("resultado", 0)),
        "relatorio": trade.get("relatorio"),
        "setup_id": setup_id,
        "emocional_id": emocional_id,
        "is_legado": bool(trade.get("is_legado", False)),
    }


def _sincronizar_anexos_trade(trade_id: int, url_imagem: Optional[str]) -> None:
    supabase.table("anexos_trades").delete().eq("trade_id", trade_id).execute()
    if url_imagem and url_imagem.strip():
        supabase.table("anexos_trades").insert({"trade_id": trade_id, "url_imagem": url_imagem}).execute()


def _filtrar_trades_dashboard(trades: list[dict], mes: Optional[str], ativo: Optional[str], setup_id: Optional[str]) -> list[dict]:
    trades_filtrados = []
    for trade in trades:
        data_str = trade.get("data_trade", "")
        if mes and not data_str.startswith(mes):
            continue
        if ativo and trade.get("ativo") != ativo:
            continue
        if setup_id and str(trade.get("setup_id")) != setup_id:
            continue
        trades_filtrados.append(trade)
    return trades_filtrados


def _adicionar_nomes_relacionados(trade: Dict[str, Any]) -> Dict[str, Any]:
    if not trade:
        return trade

    setup_id = trade.get("setup_id")
    if setup_id is not None:
        try:
            response_setup = supabase.table("setup").select("nome").eq("id", setup_id).single().execute()
            if getattr(response_setup, "data", None):
                trade["setup_nome"] = response_setup.data.get("nome")
        except Exception:
            trade["setup_nome"] = None

    emocional_id = trade.get("emocional_id")
    if emocional_id is not None:
        try:
            response_emocional = supabase.table("emotion").select("nome").eq("id", emocional_id).single().execute()
            if getattr(response_emocional, "data", None):
                trade["emocional_nome"] = response_emocional.data.get("nome")
        except Exception:
            trade["emocional_nome"] = None

    return trade


####################
# ENDPOINTS DIARIO #
####################

@app.get("/api/trades")
def listar_trades_diario(ano: int = Query(...), mes_nome: str = Query(...)):
    try:
        data_inicio, data_fim = _obter_intervalo_mes(ano, mes_nome)
        resposta = (
            supabase.table("trades")
            .select("id", "ativo", "data_trade")
            .gte("data_trade", data_inicio)
            .lte("data_trade", data_fim)
            .order("data_trade", desc=False)
            .execute()
        )
        return resposta.data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro interno no banco: {str(exc)}") from exc


@app.get("/api/trades/{trade_id}")
def obter_detalhe_trade(trade_id: int):
    try:
        response_trade = supabase.table("trades").select("*").eq("id", trade_id).single().execute()
        trade = response_trade.data
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Trade não encontrado") from exc

    if not trade:
        raise HTTPException(status_code=404, detail="Trade não encontrado")

    response_anexo = supabase.table("anexos_trades").select("url_imagem").eq("trade_id", trade_id).execute()
    trade["url_imagem"] = response_anexo.data[0]["url_imagem"] if response_anexo.data else ""
    return _adicionar_nomes_relacionados(trade)


@app.post("/api/trades")
def cadastrar_trade_diario(trade: dict = Body(...)):
    try:
        payload_trade = _montar_payload_trade(trade)
        response_trade = supabase.table("trades").insert(payload_trade).execute()

        trade_id = response_trade.data[0]["id"] if response_trade.data else None
        if trade_id is not None:
            _sincronizar_anexos_trade(trade_id, trade.get("url_imagem"))

        return response_trade.data[0] if response_trade.data else {}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.put("/api/trades/{trade_id}")
def atualizar_trade_diario(trade_id: int, trade: dict = Body(...)):
    try:
        payload_trade = _montar_payload_trade(trade)
        supabase.table("trades").update(payload_trade).eq("id", trade_id).execute()
        _sincronizar_anexos_trade(trade_id, trade.get("url_imagem"))
        return {"status": "atualizado"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/upload")
def upload_grafico(file: UploadFile = File(...)):
    try:
        extensao = file.filename.split(".")[-1] if "." in (file.filename or "") else "png"
        nome_unico = f"chart_{int(time.time() * 1000)}.{extensao}"
        conteudo_arquivo = file.file.read()

        supabase.storage.from_("prints_trades").upload(
            path=nome_unico,
            file=conteudo_arquivo,
            file_options={"content-type": f"image/{extensao}"},
        )

        url_publica = supabase.storage.from_("prints_trades").get_public_url(nome_unico)
        return {"url_imagem": url_publica}
    except Exception as exc:
        print("\n" + "=" * 50)
        print(f"ERRO CRÍTICO NO UPLOAD: {str(exc)}")
        print("=" * 50 + "\n")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.delete("/api/trades/{trade_id}")
def deletar_trade_diario(trade_id: int):
    supabase.table("anexos_trades").delete().eq("trade_id", trade_id).execute()
    supabase.table("trades").delete().eq("id", trade_id).execute()
    return {"status": "deletado"}

#######################
#### ENDPOINTS HOME ###
#######################

@app.get("/api/Home")
def obter_dados_dashboard(
    mes: str = Query(None),
    ativo: str = Query(None),
    setup_id: str = Query(None),
):
    resposta = supabase.table("trades").select("*").order("data_trade", desc=False).execute()
    todos_trades = resposta.data or []
    trades_filtrados = _filtrar_trades_dashboard(todos_trades, mes=mes, ativo=ativo, setup_id=setup_id)

    total_trades = len(trades_filtrados)
    lucro_total = sum(float(trade.get("resultado", 0)) for trade in trades_filtrados)

    trades_ganhos = sum(1 for trade in trades_filtrados if float(trade.get("resultado", 0)) > 0)
    taxa_acerto = (trades_ganhos / total_trades * 100) if total_trades > 0 else 0.0

    curva_capital = []
    saldo_acumulado = 0.0
    for trade in trades_filtrados:
        saldo_acumulado += float(trade.get("resultado", 0))
        curva_capital.append({"data_trade": trade.get("data_trade"), "saldo": saldo_acumulado})

    perf_setup = defaultdict(float)
    perf_emocional = defaultdict(float)
    perf_ativo = defaultdict(float)

    for trade in trades_filtrados:
        resultado = float(trade.get("resultado", 0))
        perf_setup[str(trade.get("setup_id", "Sem Setup"))] += resultado
        perf_emocional[str(trade.get("emocional_id", "Neutro"))] += resultado
        perf_ativo[str(trade.get("ativo", "Desconhecido"))] += resultado

    return {
        "metricas": {
            "lucro_total": lucro_total,
            "total_trades": total_trades,
            "taxa_acerto": round(taxa_acerto, 1),
        },
        "historico": trades_filtrados,
        "graficos": {
            "curva_capital": curva_capital,
            "performance_setup": dict(perf_setup),
            "performance_emocional": dict(perf_emocional),
            "performance_ativo": dict(perf_ativo),
        },
    }


########################
# ENDPOINTS BIBLIOTECA #
########################

@app.get("/api/biblioteca/categorias")
def listar_categorias_existentes():
    resposta = supabase.table("biblioteca").select("categoria").execute()
    categorias = sorted({item["categoria"] for item in resposta.data if item.get("categoria")})
    if not categorias:
        categorias = ["Geral", "Livros", "Estudos"]
    return categorias


@app.get("/api/biblioteca/notas")
def listar_notas_por_categoria(categoria: str = Query(...)):
    resposta = supabase.table("biblioteca").select("id", "titulo", "categoria").eq("categoria", categoria).execute()
    return resposta.data or []


@app.get("/api/biblioteca/notas/{nota_id}")
def obter_detalhe_nota_completa(nota_id: int):
    nota_res = supabase.table("biblioteca").select("*").eq("id", nota_id).single().execute()
    nota = nota_res.data

    anexos_res = supabase.table("anexos_biblioteca").select("url_imagem").eq("biblioteca_id", nota_id).execute()
    nota["anexos"] = [item["url_imagem"] for item in anexos_res.data] if anexos_res.data else []

    return nota


@app.post("/api/biblioteca/notas")
def criar_nova_nota(dados: dict = Body(...)):
    payload = {
        "titulo": dados.get("titulo", "Sem Título"),
        "categoria": dados.get("categoria", "Geral"),
        "conteudo": dados.get("conteudo", ""),
    }
    resposta = supabase.table("biblioteca").insert(payload).execute()
    return resposta.data[0] if resposta.data else {}


@app.put("/api/biblioteca/notas/{nota_id}")
def atualizar_nota_e_anexos(nota_id: int, dados: dict = Body(...)):
    supabase.table("biblioteca").update({
        "titulo": dados.get("titulo"),
        "conteudo": dados.get("conteudo"),
        "categoria": dados.get("categoria"),
    }).eq("id", nota_id).execute()

    supabase.table("anexos_biblioteca").delete().eq("biblioteca_id", nota_id).execute()

    novas_urls = dados.get("anexos", [])
    payload_anexos = [{"biblioteca_id": nota_id, "url_imagem": url} for url in novas_urls if str(url).strip()]

    if payload_anexos:
        supabase.table("anexos_biblioteca").insert(payload_anexos).execute()
    return {"status": "sucesso"}


@app.delete("/api/biblioteca/notas/{nota_id}")
def deletar_nota_completa(nota_id: int):
    supabase.table("anexos_biblioteca").delete().eq("biblioteca_id", nota_id).execute()
    supabase.table("biblioteca").delete().eq("id", nota_id).execute()
    return {"status": "sucesso"}