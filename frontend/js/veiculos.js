const API_VEICULOS = 'http://127.0.0.1:8000/veiculos';
const API_CLIENTES = 'http://127.0.0.1:8000/clientes';

// Carrega os dados assim que a tela abre
document.addEventListener('DOMContentLoaded', () => {
    carregarClientesParaSelect();
    carregarVeiculos();
});

// --------------------------------------------------------
// 1. CARREGAR CLIENTES (Para o campo Select)
// --------------------------------------------------------
async function carregarClientesParaSelect() {
    try {
        const resposta = await fetch(`${API_CLIENTES}/`);
        if (resposta.ok) {
            const clientes = await resposta.json();
            const selectCliente = document.getElementById('id_cliente');
            
            // Limpa o select e adiciona a opção padrão
            selectCliente.innerHTML = '<option value="">Selecione um cliente...</option>';
            
            // Preenche com os clientes do banco
            clientes.forEach(cliente => {
                const option = document.createElement('option');
                option.value = cliente.id;
                option.textContent = `${cliente.nome} (CPF: ${cliente.cpf})`;
                selectCliente.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Erro ao buscar clientes:', error);
    }
}

// --------------------------------------------------------
// 2. CADASTRAR VEÍCULO (POST)
// --------------------------------------------------------
document.getElementById('form-veiculo').addEventListener('submit', async function(event) {
    event.preventDefault();

    // Monta o payload conforme a Entidade Veiculo do FastAPI
    const payload = {
        id_cliente: parseInt(document.getElementById('id_cliente').value),
        placa: document.getElementById('placa').value,
        modelo: document.getElementById('modelo').value,
        cor: document.getElementById('cor').value,
        id_usuario_logado: 1,           // Regra Crítica de Auditoria
        nome_usuario_logado: "Admin"    // Regra Crítica de Auditoria
    };

    try {
        const resposta = await fetch(`${API_VEICULOS}/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (resposta.ok) {
            alert('Veículo cadastrado com sucesso!');
            document.getElementById('form-veiculo').reset();
            carregarVeiculos(); // Atualiza a tabela
        } else {
            const erro = await resposta.json();
            alert(`Erro ao cadastrar: ${erro.detail}`);
        }
    } catch (error) {
        console.error("Erro de conexão:", error);
    }
});

// --------------------------------------------------------
// 3. LISTAR VEÍCULOS (GET)
// --------------------------------------------------------
async function carregarVeiculos() {
    try {
        const resposta = await fetch(`${API_VEICULOS}/`);
        
        if (resposta.ok) {
            const veiculos = await resposta.json();
            const corpoTabela = document.querySelector('#tabela-veiculos tbody');
            corpoTabela.innerHTML = ''; 

            veiculos.forEach(veiculo => {
                const linha = document.createElement('tr');
                linha.innerHTML = `
                    <td>${veiculo.id}</td>
                    <td><strong>${veiculo.placa}</strong></td>
                    <td>${veiculo.modelo}</td>
                    <td>${veiculo.cor || 'S/N'}</td>
                    <td>${veiculo.id_cliente}</td>
                    <td>
                        <button onclick="deletarVeiculo(${veiculo.id})" style="color: red; cursor: pointer;">Excluir</button>
                    </td>
                `;
                corpoTabela.appendChild(linha);
            });
        }
    } catch (error) {
        console.error('Erro ao buscar veículos:', error);
    }
}

// --------------------------------------------------------
// 4. EXCLUIR VEÍCULO (DELETE)
// --------------------------------------------------------
async function deletarVeiculo(id) {
    if (!confirm("Tem certeza que deseja excluir este veículo?")) return;

    try {
        // Envia os dados de auditoria pela URL
        const urlComAuditoria = `${API_VEICULOS}/${id}?id_usuario_logado=1&nome_usuario_logado=Admin`;
        const resposta = await fetch(urlComAuditoria, { method: 'DELETE' });

        if (resposta.ok) {
            alert('Veículo excluído com sucesso!');
            carregarVeiculos();
        } else {
            alert('Erro ao excluir veículo.');
        }
    } catch (error) {
        console.error('Erro ao deletar:', error);
    }
}