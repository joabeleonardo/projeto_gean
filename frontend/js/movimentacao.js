const API_MOVIMENTACAO = 'http://127.0.0.1:8000/movimentacoes';
const API_VEICULOS = 'http://127.0.0.1:8000/veiculos';
const API_VAGAS = 'http://127.0.0.1:8000/vagas';

// Executa as funções de carregamento assim que a tela abre
document.addEventListener('DOMContentLoaded', () => {
    carregarVeiculos();
    carregarVagasLivres();
    carregarMovimentacoes();
});

// --------------------------------------------------------
// 1. CARREGAR VEÍCULOS (Para o Select)
// --------------------------------------------------------
async function carregarVeiculos() {
    try {
        const resposta = await fetch(`${API_VEICULOS}/`);
        if (resposta.ok) {
            const veiculos = await resposta.json();
            const selectVeiculo = document.getElementById('id_veiculo');
            
            selectVeiculo.innerHTML = '<option value="">Selecione o veículo...</option>';
            
            veiculos.forEach(veiculo => {
                const option = document.createElement('option');
                option.value = veiculo.id;
                option.textContent = `${veiculo.placa} - ${veiculo.modelo}`;
                selectVeiculo.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Erro ao buscar veículos:', error);
    }
}

// --------------------------------------------------------
// 2. CARREGAR VAGAS LIVRES (Para o Select)
// --------------------------------------------------------
async function carregarVagasLivres() {
    try {
        const resposta = await fetch(`${API_VAGAS}/`);
        if (resposta.ok) {
            const vagas = await resposta.json();
            const selectVaga = document.getElementById('id_vaga');
            
            selectVaga.innerHTML = '<option value="">Selecione uma vaga livre...</option>';
            
            // Filtra apenas as vagas com status 'Livre'
            const vagasLivres = vagas.filter(vaga => vaga.status === 'Livre');

            vagasLivres.forEach(vaga => {
                const option = document.createElement('option');
                option.value = vaga.id;
                option.textContent = `Vaga: ${vaga.codigo_vaga} (${vaga.tipo})`;
                selectVaga.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Erro ao buscar vagas:', error);
    }
}

// --------------------------------------------------------
// 3. REGISTRAR ENTRADA (POST)
// --------------------------------------------------------
document.getElementById('form-entrada').addEventListener('submit', async function(event) {
    event.preventDefault();

    // Monta o payload conforme o schema MovimentacaoEntradaCreate
    const payload = {
        id_veiculo: parseInt(document.getElementById('id_veiculo').value),
        id_vaga: parseInt(document.getElementById('id_vaga').value),
        id_usuario_entrada: 1,          // Operador que registrou a entrada[cite: 4]
        id_usuario_logado: 1,           // Regra de Auditoria[cite: 4]
        nome_usuario_logado: "Admin"    // Regra de Auditoria[cite: 4]
    };

    try {
        const resposta = await fetch(`${API_MOVIMENTACAO}/entrada`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (resposta.ok) {
            alert('Entrada registrada com sucesso!');
            document.getElementById('form-entrada').reset();
            // Atualiza todas as listas da tela
            carregarVagasLivres(); 
            carregarMovimentacoes();
        } else {
            const erro = await resposta.json();
            alert(`Erro ao registrar entrada: ${erro.detail}`);
        }
    } catch (error) {
        console.error("Erro de conexão:", error);
    }
});

// --------------------------------------------------------
// 4. LISTAR VEÍCULOS ESTACIONADOS (GET)
// --------------------------------------------------------
async function carregarMovimentacoes() {
    try {
        const resposta = await fetch(`${API_MOVIMENTACAO}/`);
        
        if (resposta.ok) {
            const movimentacoes = await resposta.json();
            const corpoTabela = document.querySelector('#tabela-movimentacao tbody');
            corpoTabela.innerHTML = ''; 

            // Filtra para exibir apenas os veículos que ainda estão no pátio (sem data_saida)
            const veiculosNoPatio = movimentacoes.filter(mov => mov.data_saida === null);

            veiculosNoPatio.forEach(mov => {
                const dataFormatada = new Date(mov.data_entrada).toLocaleString('pt-BR');

                const linha = document.createElement('tr');
                linha.innerHTML = `
                    <td>${mov.id}</td>
                    <td>Veículo ID: ${mov.id_veiculo}</td>
                    <td>Vaga ID: ${mov.id_vaga}</td>
                    <td>${dataFormatada}</td>
                    <td>
                        <button class="btn-saida" onclick="registrarSaida(${mov.id})">Registrar Saída</button>
                    </td>
                `;
                corpoTabela.appendChild(linha);
            });
        }
    } catch (error) {
        console.error('Erro ao buscar movimentações:', error);
    }
}

// --------------------------------------------------------
// 5. REGISTRAR SAÍDA (PUT)
// --------------------------------------------------------
async function registrarSaida(id_movimentacao) {
    if (!confirm("Confirmar a saída deste veículo e liberação da vaga?")) return;

    // Payload de saída exigido pelo backend MovimentacaoSaidaUpdate[cite: 1, 4]
    const payloadSaida = {
        id_usuario_saida: 1,         // Operador que registrou a saída[cite: 4]
        id_usuario_logado: 1,        // Regra de Auditoria[cite: 4]
        nome_usuario_logado: "Admin" // Regra de Auditoria[cite: 4]
    };

    try {
        const resposta = await fetch(`${API_MOVIMENTACAO}/${id_movimentacao}/saida`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payloadSaida)
        });

        if (resposta.ok) {
            alert('Saída registrada com sucesso! A vaga está livre novamente.');
            // Atualiza as listas refletindo a saída do veículo e a nova vaga livre
            carregarVagasLivres();
            carregarMovimentacoes();
        } else {
            const erro = await resposta.json();
            alert(`Erro ao registrar saída: ${erro.detail}`);
        }
    } catch (error) {
        console.error('Erro ao registrar saída:', error);
    }
}