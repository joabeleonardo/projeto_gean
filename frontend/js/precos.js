const API_PRECOS = 'http://127.0.0.1:8000/precos';

// Carrega a lista de preços assim que a tela abre
document.addEventListener('DOMContentLoaded', carregarPrecos);

// --------------------------------------------------------
// 1. CADASTRAR PREÇO (POST)
// --------------------------------------------------------
document.getElementById('form-preco').addEventListener('submit', async function(event) {
    event.preventDefault();

    // Monta o payload conforme a tabela tb_precos e a regra de auditoria[cite: 1, 2]
    const payload = {
        tipo_cobranca: document.getElementById('tipo_cobranca').value,
        valor: parseFloat(document.getElementById('valor').value), // Converte o texto para número decimal
        id_usuario_logado: 1,           // Regra Crítica de Auditoria[cite: 2]
        nome_usuario_logado: "Admin"    // Regra Crítica de Auditoria[cite: 2]
    };

    try {
        const resposta = await fetch(`${API_PRECOS}/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (resposta.ok) {
            alert('Preço cadastrado com sucesso!');
            document.getElementById('form-preco').reset();
            carregarPrecos(); // Atualiza a tabela imediatamente
        } else {
            const erro = await resposta.json();
            alert(`Erro ao cadastrar: ${erro.detail}`);
        }
    } catch (error) {
        console.error("Erro de conexão:", error);
    }
});

// --------------------------------------------------------
// 2. LISTAR PREÇOS (GET)
// --------------------------------------------------------
async function carregarPrecos() {
    try {
        const resposta = await fetch(`${API_PRECOS}/`);
        
        if (resposta.ok) {
            const precos = await resposta.json();
            const corpoTabela = document.querySelector('#tabela-precos tbody');
            corpoTabela.innerHTML = ''; 

            precos.forEach(preco => {
                // Formata o número para o padrão de moeda do Brasil (R$)
                const valorFormatado = preco.valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

                const linha = document.createElement('tr');
                linha.innerHTML = `
                    <td>${preco.id}</td>
                    <td><strong>${preco.tipo_cobranca}</strong></td>
                    <td style="color: green; font-weight: bold;">${valorFormatado}</td>
                    <td>
                        <button onclick="deletarPreco(${preco.id})" style="color: red; cursor: pointer; border: none; background: none; font-size: 14px;">Excluir</button>
                    </td>
                `;
                corpoTabela.appendChild(linha);
            });
        }
    } catch (error) {
        console.error('Erro ao buscar preços:', error);
    }
}

// --------------------------------------------------------
// 3. EXCLUIR PREÇO (DELETE)
// --------------------------------------------------------
async function deletarPreco(id) {
    if (!confirm("Tem certeza que deseja excluir este preço?")) return;

    try {
        // Envia os dados de auditoria pela URL, como exige o backend[cite: 2]
        const urlComAuditoria = `${API_PRECOS}/${id}?id_usuario_logado=1&nome_usuario_logado=Admin`;
        const resposta = await fetch(urlComAuditoria, { method: 'DELETE' });

        if (resposta.ok) {
            alert('Preço excluído com sucesso!');
            carregarPrecos();
        } else {
            alert('Erro ao excluir preço.');
        }
    } catch (error) {
        console.error('Erro ao deletar:', error);
    }
}