import pytest
from interface.diario_service import obter_indice_opcao, resolver_valor_select

def test_quando_o_valor_existe_retorna_o_indice_certo():
    # 1. Dados de teste (fictícios)
    lista = ["2024", "2025", "2026"]
    
    # 2. Chama a sua função
    resposta = obter_indice_opcao(valor="2025", opcoes=lista, fallback="2026")
    
    # 3. Garanta que a resposta foi o índice 1
    assert resposta == 1


def test_quando_o_valor_nao_existe_usa_o_fallback():
    # 1. Dados de teste
    lista = ["2024", "2025", "2026"]
    
    # 2. Chama a sua função passando um valor que não tá na lista ("2020")
    resposta = obter_indice_opcao(valor="2020", opcoes=lista, fallback="2026")
    
    # 3. Garanta que a resposta foi o índice do fallback (posição 2, que é "2026")
    assert resposta == 2


def test_resolver_valor_select_retorna_valor_correto():
    # 1. Dados de teste
    mapping = {1: "Neutro", 2: "Focado", 3: "Ansioso", 4: "Desatento"}
    opcoes = ["Neutro", "Focado", "Ansioso", "Desatento"]
    
    # 2. Chama a função com um valor que existe no mapping
    resposta = resolver_valor_select(valor=2, mapping=mapping, fallback="Neutro", opcoes=opcoes)
    
    # 3. Garanta que a resposta foi o valor correto do mapping
    assert resposta == "Focado"

def test_resolver_valor_select_retorna_fallback_quando_valor_nao_existe():
    # 1. Dados de teste
    mapping = {1: "Neutro", 2: "Focado", 3: "Ansioso", 4: "Desatento"}
    opcoes = ["Neutro", "Focado", "Ansioso", "Desatento"]
    
    # 2. Chama a função com um valor que não existe no mapping nem nas opções
    resposta = resolver_valor_select(valor=5, mapping=mapping, fallback="Neutro", opcoes=opcoes)
    
    # 3. Garanta que a resposta foi o fallback
    assert resposta == "Neutro"

def test_resolver_valor_select_retorna_valor_quando_valor_existe_nas_opcoes():
    # 1. Dados de teste
    mapping = {1: "Neutro", 2: "Focado", 3: "Ansioso", 4: "Desatento"}
    opcoes = ["Neutro", "Focado", "Ansioso", "Desatento"]
    
    # 2. Chama a função com um valor que existe nas opções
    resposta = resolver_valor_select(valor="Ansioso", mapping=mapping, fallback="Neutro", opcoes=opcoes)
    
    # 3. Garanta que a resposta foi o valor correto das opções
    assert resposta == "Ansioso"

def test_resolver_valor_select_retorna_fallback_quando_valor_nao_existe_nem_no_mapping_nem_nas_opcoes():
    # 1. Dados de teste
    mapping = {1: "Neutro", 2: "Focado", 3: "Ansioso", 4: "Desatento"}
    opcoes = ["Neutro", "Focado", "Ansioso", "Desatento"]
    
    # 2. Chama a função com um valor que não existe no mapping nem nas opções
    resposta = resolver_valor_select(valor="Inexistente", mapping=mapping, fallback="Neutro", opcoes=opcoes)
    
    # 3. Garanta que a resposta foi o fallback
    assert resposta == "Neutro"
