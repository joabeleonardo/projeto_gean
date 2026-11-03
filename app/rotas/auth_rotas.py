from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from controllers import usuarios_controller
from controllers.logs import registrar_log
from dependencies.auth import get_usuario_atual
from dependencies.database import get_db
from entidades.entidades import Usuario
from modelos.schemas import AlterarSenha, LoginEntrada, LoginResposta, UsuarioPublico
from rotas._erros import tratar_erros
from servicos.seguranca import criar_token

auth_router = APIRouter(prefix="/auth", tags=["Autenticação"])


@auth_router.post("/login", response_model=LoginResposta, status_code=status.HTTP_200_OK)
def login(dados: LoginEntrada, db: Session = Depends(get_db)):
    """Recebe login e senha e devolve o token que o frontend envia nas próximas chamadas."""
    try:
        with tratar_erros():
            usuario = usuarios_controller.autenticar(dados.login, dados.senha, db)
    except HTTPException as e:
        # login/senha incorretos viram 401; erros de banco continuam 500
        if e.status_code == status.HTTP_400_BAD_REQUEST:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.detail)
        raise
    perfil = str(getattr(usuario.perfil, "value", usuario.perfil))
    registrar_log(db, usuario.id, usuario.nome, "LOGIN", "Usuário", f"{usuario.nome} entrou no sistema", usuario.id)
    db.commit()
    return {
        "access_token": criar_token(usuario.id, perfil),
        "token_type": "bearer",
        "usuario": {"id": usuario.id, "nome": usuario.nome, "login": usuario.login, "perfil": perfil},
    }


@auth_router.get("/me", response_model=UsuarioPublico, status_code=status.HTTP_200_OK)
def quem_sou_eu(usuario: Usuario = Depends(get_usuario_atual)):
    return usuario


@auth_router.put("/senha", status_code=status.HTTP_204_NO_CONTENT)
def alterar_senha(dados: AlterarSenha, usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    with tratar_erros():
        usuarios_controller.alterar_propria_senha(usuario, dados.senha_atual, dados.nova_senha, db)
