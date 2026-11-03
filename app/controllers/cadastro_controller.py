from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError, OperationalError

from controllers import mensalidade_controller
from controllers.auditoria import aplicar_auditoria
from entidades.entidades import Cliente, Endereco, Veiculo
from modelos.schemas import CadastroCompletoCreate, CadastroCompletoPublico, ClienteAtualizar, EnderecoEntrada, VeiculoEntrada


def cadastrar_completo(dados: CadastroCompletoCreate, usuario, db: Session) -> dict:
    """Cadastra cliente + endereço + primeiro veículo na mesma transação:
    se qualquer parte falhar, nada é gravado."""
    try:
        if db.exec(select(Cliente).where(Cliente.cpf == dados.cliente.cpf)).first():
            raise ValueError(f"Já existe um cliente com o documento {dados.cliente.cpf}.")
        if dados.veiculo and db.exec(select(Veiculo).where(Veiculo.placa == dados.veiculo.placa)).first():
            raise ValueError(f"Já existe um veículo com a placa {dados.veiculo.placa}.")

        aplicar_auditoria(db, usuario.id, usuario.nome)

        endereco = None
        if dados.endereco:
            endereco = Endereco(**dados.endereco.model_dump())
            db.add(endereco)
            db.flush()

        cliente = Cliente(
            **dados.cliente.model_dump(mode="json"),     # nome, documento, tipo, país e telefones (com WhatsApp)
            id_endereco=endereco.id if endereco else None,
        )
        db.add(cliente)
        db.flush()

        veiculo = None
        if dados.veiculo:
            veiculo = Veiculo(**dados.veiculo.model_dump(mode="json"), id_cliente=cliente.id)
            db.add(veiculo)
            db.flush()

        # plano de mensalista (opcional): vale a partir da data da adesão, com a 1ª cobrança
        plano = None
        if dados.mensalidade:
            plano = mensalidade_controller.criar_plano_e_cobranca(db, cliente.id, dados.mensalidade, usuario)


        resposta = CadastroCompletoPublico.model_validate({
            "cliente": cliente.model_dump(),
            "endereco": endereco.model_dump() if endereco else None,
            "veiculo": veiculo.model_dump(mode="json") if veiculo else None,
            "mensalidade": plano.model_dump(mode="json") if plano else None,
        })

        db.commit()
        return resposta

        # db.commit()
        # db.refresh(cliente)
        # return {
        #     "cliente": cliente.model_dump(),
        #     "endereco": endereco.model_dump() if endereco else None,
        #     "veiculo": veiculo.model_dump(mode="json") if veiculo else None,
        #     "mensalidade": plano.model_dump(mode="json") if plano else None,
        # }
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Não foi possível cadastrar: documento ou placa já cadastrados.") from e
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e
    except (ValueError, KeyError):
        db.rollback()
        raise


def buscar_endereco(id_endereco: int, db: Session) -> Endereco:
    endereco = db.get(Endereco, id_endereco)
    if not endereco:
        raise KeyError(f"Endereço de ID {id_endereco} não encontrado.")
    return endereco


def atualizar_endereco(id_endereco: int, dados: EnderecoEntrada, usuario, db: Session) -> Endereco:
    try:
        endereco = buscar_endereco(id_endereco, db)
        aplicar_auditoria(db, usuario.id, usuario.nome)
        for campo, valor in dados.model_dump().items():
            setattr(endereco, campo, valor)
        db.add(endereco)
        db.commit()
        db.refresh(endereco)
        return endereco
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e


def obter_cliente_completo(id_cliente: int, db: Session) -> dict:
    """Cliente + endereço + veículos + planos de mensalista (para a tela de edição)."""
    try:
        cliente = db.get(Cliente, id_cliente)
        if not cliente:
            raise KeyError(f"Cliente de ID {id_cliente} não encontrado.")
        endereco = db.get(Endereco, cliente.id_endereco) if cliente.id_endereco else None
        veiculos = db.exec(select(Veiculo).where(Veiculo.id_cliente == id_cliente).order_by(Veiculo.placa)).all()
        return {
            "cliente": cliente.model_dump(),
            "endereco": endereco.model_dump() if endereco else None,
            "veiculos": [v.model_dump(mode="json") for v in veiculos],
            "mensalidades": mensalidade_controller.listar_ativas(db, id_cliente),
        }
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e


def atualizar_cliente_completo(id_cliente: int, dados: ClienteAtualizar, usuario, db: Session) -> dict:
    """Atualiza nome, CPF, telefone e endereço (cria o endereço se o cliente ainda não tinha)."""
    try:
        cliente = db.get(Cliente, id_cliente)
        if not cliente:
            raise KeyError(f"Cliente de ID {id_cliente} não encontrado.")
        aplicar_auditoria(db, usuario.id, usuario.nome)
        # o documento (CPF/CNPJ/passaporte) não é editável: só nome, país e telefones
        cliente.nome = dados.cliente.nome
        cliente.pais = dados.cliente.pais
        cliente.telefone = dados.cliente.telefone
        cliente.telefone_whatsapp = dados.cliente.telefone_whatsapp
        cliente.telefone2 = dados.cliente.telefone2
        cliente.telefone2_whatsapp = dados.cliente.telefone2_whatsapp
        if dados.endereco:
            endereco = db.get(Endereco, cliente.id_endereco) if cliente.id_endereco else None
            if endereco is None:
                endereco = Endereco(**dados.endereco.model_dump())
                db.add(endereco)
                db.flush()
                cliente.id_endereco = endereco.id
            else:
                for campo, valor in dados.endereco.model_dump().items():
                    setattr(endereco, campo, valor)
                db.add(endereco)
        db.add(cliente)
        db.commit()
        return obter_cliente_completo(id_cliente, db)
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Não foi possível salvar o cadastro.") from e
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e
    except (ValueError, KeyError):
        db.rollback()
        raise
