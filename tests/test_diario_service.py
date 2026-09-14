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