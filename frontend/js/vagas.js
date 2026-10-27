const API_VAGAS = 'http://127.0.0.1:8000/vagas';

// Carrega os dados assim que a tela abre
document.addEventListener('DOMContentLoaded', carregarVagas);

// --------------------------------------------------------
// 1. CADASTRAR VAGA (POST)
// --------------------------------------------------------
document.getElementById('form-vaga').addEventListener('submit', async function(event) {
    event.preventDefault();

    // Monta o payload conforme os Enums definidos no backend
    const payload = {
        codigo_vaga: document.getElementById('codigo_vaga').value,
        tipo: document.getElementById('tipo').value,
        status: document.getElementById('status').value,
        id_usuario_logado: 1,           // Regra Crítica de Auditoria[cite: 1]
        nome_usuario_logado: "Admin"    // Regra Crítica de Auditoria[cite: 1]
    };

    try {
        const resposta = await fetch(`${API_VAGAS}/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (resposta.ok) {
            alert('Vaga cadastrada com sucesso!');
            document.getElementById('form-vaga').reset();
            carregarVagas(); // Atualiza a tabela
        } else {
            const erro = await resposta.json();
            alert(`Erro ao cadastrar: ${erro.detail}`);
        }
    } catch (error) {
        console.error("Erro de conexão:", error);
    }
});

// --------------------------------------------------------
// 2. LISTAR VAGAS (GET)
// --------------------------------------------------------
async function carregarVagas() {
    try {
        const resposta = await fetch(`${API_VAGAS}/`);
        
        if (resposta.ok) {
            const vagas = await resposta.json();
            const corpoTabela = document.querySelector('#tabela-vagas tbody');
            corpoTabela.innerHTML = ''; 

            vagas.forEach(vaga => {
                // Adiciona cor ao status para facilitar a visualização
                const corStatus = vaga.status === 'Livre' ? 'green' : 'red';

                const linha = document.createElement('tr');
                linha.innerHTML = `
                    <td>${vaga.id}</td>
                    <td><strong>${vaga.codigo_vaga}</strong></td>
                    <td>${vaga.tipo}</td>
                    <td style="color: ${corStatus}; font-weight: bold;">${vaga.status}</td>
                    <td>
                        <button onclick="deletarVaga(${vaga.id})" style="color: red; cursor: pointer; border: none; background: none; font-size: 14px;">Excluir</button>
                    </td>
                `;
                corpoTabela.appendChild(linha);
            });
        }
    } catch (error) {
        console.error('Erro ao buscar vagas:', error);
    }
}

// --------------------------------------------------------
// 3. EXCLUIR VAGA (DELETE)
// --------------------------------------------------------
async function deletarVaga(id) {
    if (!confirm("Tem certeza que deseja excluir esta vaga?")) return;

    try {
        // Envia os dados de auditoria pela URL[cite: 1]
        const urlComAuditoria = `${API_VAGAS}/${id}?id_usuario_logado=1&nome_usuario_logado=Admin`;
        const resposta = await fetch(urlComAuditoria, { method: 'DELETE' });

        if (resposta.ok) {
            alert('Vaga excluída com sucesso!');
            carregarVagas();
        } else {
            alert('Erro ao excluir vaga.');
        }
    } catch (error) {
        console.error('Erro ao deletar:', error);
    }
}