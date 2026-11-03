from sqlmodel import Session, select
from controllers.auditoria import aplicar_auditoria
from sqlalchemy.exc import OperationalError, IntegrityError

from entidades.entidades import Usuario, PerfilEnum
from modelos.schemas import UsuarioCreate, UsuarioUpdate
from servicos.seguranca import gerar_hash_senha, verificar_senha, senha_esta_em_hash
import os

def inserir_usuario(usuario_in: UsuarioCreate, db: Session) -> Usuario:
    try:
        # REGRA CRÍTICA DE AUDITORIA[cite: 1, 2]
        aplicar_auditoria(db, usuario_in.id_usuario_logado, usuario_in.nome_usuario_logado)

        dados = usuario_in.model_dump(mode="json", exclude={"id_usuario_logado", "nome_usuario_logado"})
        dados["senha"] = gerar_hash_senha(dados["senha"])
        codigo = dados.pop("codigo_liberacao", None)
        if codigo:
            if dados.get("perfil") != "Administrador":
                raise ValueError("Somente administradores podem ter código de liberação.")
            dados["codigo_liberacao"] = gerar_hash_senha(codigo)
        usuario_insert = Usuario.model_validate(dados)
        db.add(usuario_insert)
        db.commit()
        db.refresh(usuario_insert)
        return usuario_insert
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Erro de integridade ao inserir usuário (Login já existente).") from e
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def buscar_usuarios(db: Session) -> list[Usuario]:
    try:
        statement = select(Usuario)
        return db.exec(statement).all()
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def buscar_usuario_por_id(id_usuario: int, db: Session) -> Usuario:
    try:
        usuario = db.get(Usuario, id_usuario)
        if not usuario:
            raise KeyError(f"Usuário de ID {id_usuario} não encontrado.")
        return usuario
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def atualizar_usuario(id_usuario: int, dados_atualizados: UsuarioUpdate, db: Session) -> Usuario:
    try:
        usuario = db.get(Usuario, id_usuario)
        if not usuario:
            raise KeyError(f"Usuário de ID {id_usuario} não encontrado.")
        
        # REGRA CRÍTICA DE AUDITORIA[cite: 1, 2]
        aplicar_auditoria(db, dados_atualizados.id_usuario_logado, dados_atualizados.nome_usuario_logado)

        usuario_data = dados_atualizados.model_dump(exclude_unset=True, exclude={"id_usuario_logado", "nome_usuario_logado"})
        nova_senha = usuario_data.pop("senha", None)
        novo_codigo = usuario_data.pop("codigo_liberacao", None)
        if "perfil" in usuario_data:
            usuario_data["perfil"] = getattr(usuario_data["perfil"], "value", usuario_data["perfil"])
        for key, value in usuario_data.items():
            setattr(usuario, key, value)
        if nova_senha:  # em branco = mantém a senha atual
            usuario.senha = gerar_hash_senha(nova_senha)
        virou_admin = str(usuario.perfil).strip().lower() in ("administrador", "admin")
        if not virou_admin:
            usuario.codigo_liberacao = None  # só administrador tem código de liberação
        elif novo_codigo:
            usuario.codigo_liberacao = gerar_hash_senha(novo_codigo)
        
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Erro de integridade ao atualizar usuário.") from e
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def deletar_usuario(id_usuario: int, id_usuario_logado: int, nome_usuario_logado: str, db: Session):
    try:
        usuario = db.get(Usuario, id_usuario)
        if not usuario:
            raise KeyError(f"Usuário de ID {id_usuario} não encontrado.")
        
        # REGRA CRÍTICA DE AUDITORIA[cite: 1, 2]
        aplicar_auditoria(db, id_usuario_logado, nome_usuario_logado)
        
        db.delete(usuario)
        db.commit()
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e


def autenticar(login: str, senha: str, db: Session) -> Usuario:
    """Confere login e senha. A mensagem é a mesma para login ou senha errados."""
    try:
        usuario = db.exec(select(Usuario).where(Usuario.login == login.strip())).first()
        if usuario is None or not verificar_senha(senha, usuario.senha):
            raise ValueError("Login ou senha incorretos.")
        if not senha_esta_em_hash(usuario.senha):
            # senha antiga em texto puro: regrava com hash
            aplicar_auditoria(db, usuario.id, usuario.nome)
            usuario.senha = gerar_hash_senha(senha)
            db.add(usuario)
            db.commit()
            db.refresh(usuario)
        return usuario
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e


def alterar_propria_senha(usuario: Usuario, senha_atual: str, nova_senha: str, db: Session) -> None:
    try:
        if not verificar_senha(senha_atual, usuario.senha):
            raise ValueError("Senha atual incorreta.")
        aplicar_auditoria(db, usuario.id, usuario.nome)
        usuario.senha = gerar_hash_senha(nova_senha)
        db.add(usuario)
        db.commit()
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e


def garantir_admin_inicial(db: Session) -> bool:
    """Se não existir nenhum usuário, cria o administrador inicial.

    Login: admin | Senha: ADMIN_SENHA_INICIAL do .env (padrão: admin123).
    Troque a senha no primeiro acesso.
    """
    if db.exec(select(Usuario)).first() is not None:
        return False
    senha = os.getenv("ADMIN_SENHA_INICIAL") or "admin123"
    admin = Usuario(
        nome="Administrador",
        login="admin",
        senha=gerar_hash_senha(senha),
        perfil="Administrador",
    )
    aplicar_auditoria(db, 0, "Sistema (criação do admin inicial)")
    db.add(admin)
    db.commit()
    return True



def autorizar_liberacao(codigo: str, db: Session):
    """Devolve o administrador dono do código de liberação informado (ou None)."""
    administradores = db.exec(select(Usuario).where(Usuario.codigo_liberacao != None)).all()  # noqa: E711
    for admin in administradores:
        eh_admin = str(admin.perfil).strip().lower() in ("administrador", "admin")
        if eh_admin and verificar_senha(codigo, admin.codigo_liberacao):
            return admin
    return None
