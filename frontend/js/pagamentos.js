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