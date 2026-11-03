from servicos.seguranca import (
    criar_token, gerar_hash_senha, ler_token, senha_esta_em_hash, verificar_senha,
)


def test_hash_nao_guarda_senha_em_texto_puro():
    h = gerar_hash_senha("senha123")
    assert "senha123" not in h
    assert senha_esta_em_hash(h)


def test_hash_tem_sal_diferente_a_cada_vez():
    assert gerar_hash_senha("abc123") != gerar_hash_senha("abc123")


def test_verificar_senha_correta_e_incorreta():
    h = gerar_hash_senha("senha123")
    assert verificar_senha("senha123", h)
    assert not verificar_senha("outra", h)


def test_senha_antiga_em_texto_puro_ainda_confere():
    # usuários criados antes do hash continuam conseguindo entrar (e são migrados no login)
    assert verificar_senha("antiga", "antiga")
    assert not verificar_senha("errada", "antiga")
    assert not senha_esta_em_hash("antiga")


def test_token_valido_e_adulterado():
    token = criar_token(7, "Administrador")
    dados = ler_token(token)
    assert dados["sub"] == "7"
    assert dados["perfil"] == "Administrador"
    assert ler_token(token + "x") is None
    assert ler_token("lixo") is None
