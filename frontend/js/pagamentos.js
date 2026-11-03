<<<<<<< HEAD
const usuario = iniciarPagina({ pagina: "pagamentos", titulo: "Pagamentos" });
const $ = id => document.getElementById(id);
const tbody = $("tbody");
let pagamentos = [];

$("f-forma").innerHTML = `<option value="">Todas</option>${opcoesFormaPagamento()}`;

function filtros() {
    return { cliente: $("f-cliente").value.trim(), status_pagamento: $("f-status").value, tipo: $("f-tipo").value,
             forma: $("f-forma").value, inicio: $("f-inicio").value, fim: $("f-fim").value };
}

async function carregarPagina({ pagina, por_pagina }) {
    const r = await api("/pagamentos/pagina", { params: { ...filtros(), pagina, por_pagina } });
    pagamentos = r.itens;
    tbody.innerHTML = r.itens.length ? r.itens.map(p => `<tr>
        <td>${esc(p.cliente_nome || "—")}${p.placa ? `<div>${placaHtml(p.placa)}</div>` : ""}</td>
        <td>${p.tipo_cobranca === "Hora" ? "Por hora" : "Mensal"}</td>
        <td class="num">${moeda(p.valor_total)}</td>
        <td><span class="selo ${p.status === "Pago" ? "pago" : "pendente"}">${esc(p.status)}</span></td>
        <td>${esc(p.forma_pagamento || "—")}${p.valor_recebido !== null && p.valor_recebido !== undefined ? `<div class="ajuda">recebido ${moeda(p.valor_recebido)} · troco ${moeda(p.troco || 0)}</div>` : ""}</td>
        <td>${dataCurta(p.data_vencimento)}</td><td>${dataHora(p.data_pagamento)}</td><td>${esc(p.recebido_por || "—")}</td>
        <td class="acoes-celula">
            ${p.status === "Pendente" ? `<button class="btn pequeno" data-baixa="${p.id}" data-valor="${p.valor_total}" ${dica("Registrar que o cliente pagou esta cobrança (escolhendo a forma de pagamento)")}>Dar baixa</button>` : ""}
            ${ehAdmin() ? `<button class="btn perigo pequeno" data-excluir="${p.id}" ${dica("Apagar este pagamento (não pode ser desfeito)")}>Excluir</button>` : ""}
        </td></tr>`).join("")
        : `<tr><td colspan="9" class="vazio">Nenhum pagamento encontrado.</td></tr>`;
    return r;
}

const paginador = criarPaginador($("paginador"), carregarPagina);
const filtrar = debounce(() => paginador.primeira(), 350);
$("f-cliente").addEventListener("input", filtrar);
["f-status", "f-tipo", "f-forma", "f-inicio", "f-fim"].forEach(id => $(id).addEventListener("change", () => paginador.primeira()));
$("btn-limpar").addEventListener("click", () => { $("f-cliente").value = ""; ["f-status", "f-tipo", "f-forma"].forEach(id => { $(id).value = ""; }); $("f-inicio").value = $("f-fim").value = ""; paginador.primeira(); });

tbody.addEventListener("click", async ev => {
    const baixa = ev.target.closest("[data-baixa]"), excluir = ev.target.closest("[data-excluir]");
    try {
        if (baixa) abrirBaixa(baixa.dataset.baixa, baixa.dataset.valor, () => paginador.recarregar());
        else if (excluir && await confirmar("Esta ação não pode ser desfeita.", { titulo: "Excluir este pagamento?", sim: "Excluir", perigo: true })) {
            await api(`/pagamentos/${excluir.dataset.excluir}`, { metodo: "DELETE" });
            aviso("Pagamento excluído.");
            paginador.recarregar();
        }
    } catch (e) { erroAviso(e); }
});

if (usuario && ehAdmin()) $("bloco-gerar").hidden = false;
$("btn-gerar").addEventListener("click", async () => {
    try {
        const r = await api("/mensalidades/gerar-cobrancas", { metodo: "POST" });
        aviso(r.criadas ? `${r.criadas} mensalidade(s) gerada(s).` : "Nenhuma mensalidade nova a gerar." + (r.sem_preco ? ` (${r.sem_preco} sem preço mensal definido)` : ""));
        paginador.recarregar();
    } catch (e) { erroAviso(e); }
});

if (usuario) paginador.recarregar();
=======
const API_PAGAMENTOS = 'http://127.0.0.1:8000/pagamentos';
const API_CLIENTES = 'http://127.0.0.1:8000/clientes';
const API_MOVIMENTACOES = 'http://127.0.0.1:8000/movimentacoes';

// Executa as funções de carregamento assim que a tela abre
document.addEventListener('DOMContentLoaded', () => {
    carregarClientes();
    carregarMovimentacoes();
    carregarPagamentos();
});

// --------------------------------------------------------
// 1. CARREGAR SELECTS (Clientes e Movimentações)
// --------------------------------------------------------
async function carregarClientes() {
    try {
        const resposta = await fetch(`${API_CLIENTES}/`);
        if (resposta.ok) {
            const clientes = await resposta.json();
            const selectCliente = document.getElementById('id_cliente');
            clientes.forEach(cliente => {
                const option = document.createElement('option');
                option.value = cliente.id;
                option.textContent = `${cliente.nome} (CPF: ${cliente.cpf})`;
                selectCliente.appendChild(option);
            });
        }
    } catch (error) { console.error('Erro ao buscar clientes:', error); }
}

async function carregarMovimentacoes() {
    try {
        const resposta = await fetch(`${API_MOVIMENTACOES}/`);
        if (resposta.ok) {
            const movimentacoes = await resposta.json();
            const selectMov = document.getElementById('id_movimentacao');
            movimentacoes.forEach(mov => {
                const option = document.createElement('option');
                option.value = mov.id;
                const dataEntrada = new Date(mov.data_entrada).toLocaleString('pt-BR');
                option.textContent = `Mov ID: ${mov.id} - Vaga: ${mov.id_vaga} (${dataEntrada})`;
                selectMov.appendChild(option);
            });
        }
    } catch (error) { console.error('Erro ao buscar movimentacoes:', error); }
}

// --------------------------------------------------------
// 2. REGISTRAR PAGAMENTO (POST)
// --------------------------------------------------------
document.getElementById('form-pagamento').addEventListener('submit', async function(event) {
    event.preventDefault();

    // Captura valores opcionais e converte para número ou null
    const idClienteVal = document.getElementById('id_cliente').value;
    const idMovVal = document.getElementById('id_movimentacao').value;

    const payload = {
        tipo_cobranca: document.getElementById('tipo_cobranca').value,
        id_cliente: idClienteVal ? parseInt(idClienteVal) : null,
        id_movimentacao: idMovVal ? parseInt(idMovVal) : null,
        valor_total: parseFloat(document.getElementById('valor_total').value),
        status: document.getElementById('status').value,
        id_usuario_recebimento: 1,      // Operador que recebeu o dinheiro
        id_usuario_logado: 1,           // Regra Crítica de Auditoria
        nome_usuario_logado: "Admin"    // Regra Crítica de Auditoria
    };

    try {
        const resposta = await fetch(`${API_PAGAMENTOS}/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (resposta.ok) {
            alert('Pagamento registrado com sucesso!');
            document.getElementById('form-pagamento').reset();
            carregarPagamentos();
        } else {
            const erro = await resposta.json();
            alert(`Erro ao registrar: ${erro.detail}`);
        }
    } catch (error) {
        console.error("Erro de conexão:", error);
    }
});

// --------------------------------------------------------
// 3. LISTAR PAGAMENTOS (GET)
// --------------------------------------------------------
async function carregarPagamentos() {
    try {
        const resposta = await fetch(`${API_PAGAMENTOS}/`);
        
        if (resposta.ok) {
            const pagamentos = await resposta.json();
            const corpoTabela = document.querySelector('#tabela-pagamentos tbody');
            corpoTabela.innerHTML = ''; 

            pagamentos.forEach(pag => {
                // Formatação de Moeda e Data
                const valorFormatado = pag.valor_total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
                const dataPag = pag.data_pagamento ? new Date(pag.data_pagamento).toLocaleString('pt-BR') : 'N/A';
                
                // Estilo visual da etiqueta (badge) baseado no status
                const classeStatus = pag.status === 'Pago' ? 'bg-verde badge-status' : 'badge-status';
                const corBadge = pag.status === 'Pendente' ? 'background-color: #f39c12;' : '';

                const linha = document.createElement('tr');
                linha.innerHTML = `
                    <td>${pag.id}</td>
                    <td>${pag.tipo_cobranca}</td>
                    <td><strong>${valorFormatado}</strong></td>
                    <td><span class="${classeStatus}" style="${corBadge}">${pag.status}</span></td>
                    <td>${dataPag}</td>
                    <td>
                        <button onclick="deletarPagamento(${pag.id})" style="color: red; cursor: pointer; border: none; background: none;">Excluir</button>
                    </td>
                `;
                corpoTabela.appendChild(linha);
            });
        }
    } catch (error) {
        console.error('Erro ao buscar pagamentos:', error);
    }
}

// --------------------------------------------------------
// 4. EXCLUIR PAGAMENTO (DELETE)
// --------------------------------------------------------
async function deletarPagamento(id) {
    if (!confirm("Tem certeza que deseja excluir este pagamento?")) return;

    try {
        const urlComAuditoria = `${API_PAGAMENTOS}/${id}?id_usuario_logado=1&nome_usuario_logado=Admin`;
        const resposta = await fetch(urlComAuditoria, { method: 'DELETE' });

        if (resposta.ok) {
            alert('Pagamento excluído!');
            carregarPagamentos();
        } else {
            alert('Erro ao excluir pagamento.');
        }
    } catch (error) {
        console.error('Erro ao deletar:', error);
    }
}
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272
