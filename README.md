# Sistema de Estacionamento (v2)

API em **FastAPI + SQLModel + MySQL** e frontend em **HTML/CSS/JavaScript** puros.

## Como rodar

1. Crie e ative um ambiente virtual (fora desta pasta, ou `venv/`, que já está no `.gitignore`):
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r app\requirements.txt
   ```
2. **Banco de dados:** esta versão acrescenta colunas e uma tabela. Faça backup e rode, **em ordem**, os scripts
   que ainda não rodou (cada um pode ser repetido sem problema):
   ```
   mysql -u SEU_USUARIO -p NOME_DO_BANCO < banco\migracao_v2.sql
   mysql -u SEU_USUARIO -p NOME_DO_BANCO < banco\migracao_v3.sql
   mysql -u SEU_USUARIO -p NOME_DO_BANCO < banco\migracao_v4.sql
   ```
   * `migracao_v3.sql`: `tb_mensalidades`, `ativa` em vagas, `valor_minimo`/`tempo_minimo_minutos` em preços.
   * `migracao_v4.sql`: CNPJ/país/2º telefone/WhatsApp em clientes, troco em pagamentos, quem liberou a entrada
     em movimentações, vagas e preços **Premium**, tipo de plano em mensalidades e a tabela de logs `tb_logs`.
3. Copie `app\.env.example` para `app\.env` e preencha (banco, `SECRET_KEY`, `ADMIN_SENHA_INICIAL`).
4. Suba a API a partir da pasta `app\`:
   ```
   cd app
   uvicorn main:app --reload
   ```
5. Abra **http://127.0.0.1:8000/sistema/html/login.html** (documentação da API em `/docs`).
6. Primeiro acesso: se não houver usuários, o sistema cria o `admin` com a senha de `ADMIN_SENHA_INICIAL`
   (padrão `admin123`). Usuários antigos continuam entrando; a senha é convertida para hash no primeiro login.

## Depois de migrar, configure (como administrador)

1. **Preços:** hora e mensalidade, para **carro** e para **moto**. Na hora, defina também o **valor mínimo** e até
   quantos minutos ele vale (ex.: R$ 3,00 até 15 min).
2. **Vagas:** cada vaga tem *veículo* (carro/moto) e *tipo* (horista/mensalista). Cadastre as vagas de moto.
3. **Usuários:** edite o seu usuário administrador e defina o **código de liberação** (PIN).
   Ele serve para liberar a entrada de cliente inadimplente.
4. Veículos já cadastrados ficam como **Carro** e sem marca. Para corrigir uma moto existente:
   `UPDATE tb_veiculos SET tipo_veiculo='Moto', marca='Honda' WHERE placa='ABC-1234';`

## O que o sistema faz

* **Painel:** vagas (total, livres, ocupadas, horistas, mensalistas, por carro/moto), mapa do pátio, registro
  rápido de entrada e saída, tabela de preços para consulta no balcão, clientes inadimplentes, últimas
  movimentações e gráficos.
* **Cobrança por hora (proporcional):** na saída o valor é `valor da hora × minutos ÷ 60` (minutos completos), com o
  **valor mínimo** valendo até o tempo mínimo e como piso depois disso. Com R$ 12/h e mínimo de R$ 3,00 até 15 min:
  5 min = R$ 3,00 · 15 min = R$ 3,00 · 30 min = R$ 6,00 · 1h = R$ 12,00 · 1h30 = R$ 18,00 · 2h = R$ 24,00.
  O preço é o da **categoria da vaga** (carro ou moto). A forma de pagamento (dinheiro, Pix, cartão de
  débito/crédito, transferência) é escolhida na saída.
* **Plano de mensalista:** no *Novo cadastro* (ou em *Clientes → Plano*) o cliente adere informando categoria, **cotas**
  (quantos veículos podem estar no pátio ao mesmo tempo) e a data de adesão — o plano vale a partir dela. A mensalidade
  é `preço mensal × cotas`; a 1ª cobrança é criada na adesão e as seguintes são geradas sozinhas a cada mês
  (uma vez por dia o sistema confere; há também um botão em *Pagamentos*).
  **Não é possível ter mais cotas contratadas do que vagas de mensalista ativas** (por categoria).
* **Entrada automática:** ao escolher o veículo, o sistema identifica se o cliente é **mensalista** (usa uma cota e
  uma vaga de mensalista) ou **horista** (vaga de horista). Se o mensalista já usou todas as cotas, aparece o
  alerta *"todas as cotas estão em uso… deseja dar entrada como horista?"*; confirmando, a entrada é cobrada por hora.
* **Edição:** clientes (dados e endereço), veículos e vagas (código, tipo, carro/moto) podem ser corrigidos.
  Com o veículo no pátio não se muda tipo/proprietário; com a vaga ocupada não se muda tipo nem categoria.
* **Vagas inativas:** em reforma, a vaga é **inativada**: sai da contagem de disponíveis, aparece tracejada no painel
  e não recebe entradas. Não dá para inativar vaga ocupada, nem vaga de mensalista que sustente cotas já contratadas.
* **Clientes:** a lista mostra quem é mensalista (categoria e cotas), horista ou inadimplente, com filtro.
* **Inadimplência:** cliente com cobrança **pendente e vencida**. Ao tentar registrar a entrada, aparece
  *"Entrada bloqueada. Cliente inadimplente há X dias"* e um campo para o código do administrador.
  Cada liberação fica registrada em `tb_auditoria`. Após 5 códigos errados seguidos o operador é
  bloqueado por 5 minutos.
* **Vaga compatível:** carro só entra em vaga de carro; moto, em vaga de moto.

## Novidades da 4ª rodada

* **Formulários:** preenchimento sequencial (cada campo só abre quando o anterior está correto), CPF/CNPJ validados ao
  digitar (e ao sair do campo), avisos de erro em **modal** (um só, sem empilhar) e confirmações de sucesso em uma faixa
  única no topo. Gravações repetidas por duplo clique viram uma só.
* **Clientes:** pessoa física (CPF), jurídica (CNPJ) ou estrangeira (passaporte), país, dois telefones com marcação de
  WhatsApp (com link direto). **CPF/CNPJ/passaporte não é editável pelo sistema** (só direto no banco).
* **Paginação e filtros:** clientes, veículos, pagamentos, inadimplentes e logs são paginados no servidor (só a página
  da tela é consultada; 10 ou 20 por página conforme a tela). Filtros por nome, documento, telefone, placa, tipo e origem.
* **Troco:** pagamento em dinheiro pede o valor entregue, calcula o troco e registra os dois. O *Fechamento de caixa*
  (Relatórios) mostra dinheiro entregue, troco devolvido e saldo em espécie por usuário e forma de pagamento.
* **Inadimplência:** número no painel e aba própria (com cobrança e baixa). Saiu da aba Pagamentos, assim como o
  lançamento manual de mensalidade (agora a adesão é feita no cadastro/Plano).
* **Vagas premium:** vaga exclusiva de um cliente, com preço próprio (*Preços → Mensalidade premium*). O cliente escolhe a
  vaga ao aderir ao plano Premium; só os veículos dele entram nela. Se a vaga já estiver ocupada, o 2º veículo cai na
  regra de cotas (ou entra como horista).
* **Relatórios:** por veículo (escolha um e veja o histórico do dia ou do mês), clientes e veículos cadastrados,
  recebimentos por cliente, inadimplentes e caixa. Mostram **quem** registrou cada entrada/saída/recebimento e **quem
  liberou** por código.
* **Logs do sistema** (Administração): quem fez o quê e quando, com o valor antigo e o novo
  (ex.: *"Ana alterou o preço Horista (Carro): campo valor de R$ 12,00 para R$ 15,00"*), filtros e exportação em CSV.
* **Hora do servidor:** datas padrão, "hoje" e atalhos de período vêm do servidor, não do relógio do computador.
  O bloqueio por tentativas de código e a expiração do login já usavam o relógio do servidor.

## Perfis e permissões (valem na API, não só nas telas)

| Ação | Operador | Administrador |
|---|:-:|:-:|
| Painel, entrada/saída, clientes e veículos (cadastrar e editar), pagamentos (lançar e dar baixa), aderir a plano | ✔ | ✔ |
| Consultar preços e vagas | ✔ | ✔ |
| Alterar preços; cadastrar, editar, inativar e excluir vagas | | ✔ |
| Alterar cotas, cancelar plano, gerar mensalidades | | ✔ |
| Excluir clientes, veículos e pagamentos | | ✔ |
| Relatórios, usuários, logs do sistema, valores de receita no painel | | ✔ |
| Liberar entrada de inadimplente (código) | | ✔ |

## Datas e horários (importante)

Todas as colunas de data/hora (`data_entrada`, `data_saida`, `data_pagamento`) são `DATETIME` do MySQL e guardam o
**relógio local do estabelecimento, sem fuso** — exatamente como os registros antigos foram gravados. O código segue
essa convenção em um só lugar (`app/servicos/datas.py`) e as entidades declaram as colunas como `DateTime(timezone=False)`.
Nada é convertido para UTC (isso deslocaria os registros existentes em horas).
Se o servidor rodar em outro fuso (ex.: nuvem em UTC), defina `FUSO_HORARIO=America/Sao_Paulo` no `.env`.
**Não é necessária nenhuma alteração no banco.**

## Testes

```
cd app
pytest
```
Os testes de rotas usam mocks (sem MySQL) e `conftest.py` define variáveis de teste, então não precisam do `.env`.

## O que mudou em relação ao seu banco

O código agora usa o nome real da tabela `tb_movimentacao` (antes estava `tb_movimentacoes`, o que fazia o
painel e a movimentação falharem). O campo `perfil` aceita qualquer texto já gravado no banco (ENUM ou VARCHAR).
