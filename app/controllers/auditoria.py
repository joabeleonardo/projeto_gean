from sqlalchemy import text


def aplicar_auditoria(db, id_usuario, nome_usuario) -> None:
    """Informa ao MySQL quem está alterando os dados (usado pelas triggers de auditoria).

    O valor vai como parâmetro (nunca concatenado no SQL), o que evita SQL injection.
    Em outros bancos (ex.: SQLite nos testes) não há triggers, então não faz nada.
    """
    # quem está gravando: usado pelos logs do sistema (controllers/logs.py) em qualquer banco
    db.info["usuario_log"] = (id_usuario, nome_usuario)
    from controllers.logs import registrar_hooks
    registrar_hooks()
    if db.get_bind().dialect.name != "mysql":
        return
    db.execute(
        text("SET @usuario_logado = :usuario"),
        {"usuario": f"ID: {id_usuario} - {nome_usuario}"},
    )


def registrar_evento_auditoria(db, tabela: str, acao: str, id_registro: int, descricao: str, responsavel: str) -> None:
    """Grava uma linha em tb_auditoria para eventos que as triggers não enxergam
    (ex.: entrada liberada por código do administrador). Só existe no MySQL."""
    if db.get_bind().dialect.name != "mysql":
        return
    db.execute(
        text(
            "INSERT INTO tb_auditoria (tabela_afetada, acao, id_registro, dados_novos, usuario_responsavel) "
            "VALUES (:tabela, :acao, :id_registro, :descricao, :responsavel)"
        ),
        {"tabela": tabela, "acao": acao, "id_registro": id_registro, "descricao": descricao[:60000], "responsavel": responsavel[:100]},
    )
