// URL base definida no seu FastAPI para a rota de clientes
const API_URL = "http://127.0.0.1:8000/clientes";

// Executa a função de listar assim que a página carrega
document.addEventListener("DOMContentLoaded", listarClientes);

// Captura o evento de 'submit' (envio) do formulário
document.getElementById("form-cliente").addEventListener("submit", async function(event) {
    event.preventDefault(); // Impede a página de recarregar

    // Captura os valores digitados
    const nome = document.getElementById("nome").value;
    const cpf = document.getElementById("cpf").value;
    const telefone = document.getElementById("telefone").value;

    // Monta o objeto de dados. 
    // Obrigatório incluir os campos de auditoria definidos no seu Schema do FastAPI
    const payload = {
        nome: nome,
        cpf: cpf,
        telefone: telefone,
        id_usuario_logado: 1,              // ID fixo simulando o usuário logado
        nome_usuario_logado: "Admin Sistema" // Nome fixo simulando o usuário logado
    };

    try {
        // Envia requisição POST para salvar no banco
        const resposta = await fetch(`${API_URL}/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        if (resposta.ok) {
            alert("Cliente salvo com sucesso!");
            document.getElementById("form-cliente").reset(); // Limpa o formulário
            listarClientes(); // Atualiza a tabela
        } else {
            const erro = await resposta.json();
            alert("Erro ao salvar: " + erro.detail);
        }
    } catch (error) {
        console.error("Erro na comunicação com a API:", error);
    }
});

// Função para buscar os clientes e montar a tabela
async function listarClientes() {
    try {
        // Envia requisição GET para buscar a lista
        const resposta = await fetch(`${API_URL}/`);
        const clientes = await resposta.json();

        const tbody = document.querySelector("#tabela-clientes tbody");
        tbody.innerHTML = ""; // Limpa a tabela antes de preencher

        // Percorre cada cliente retornado pelo banco e cria uma linha (tr)
        clientes.forEach(cliente => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${cliente.id}</td>
                <td>${cliente.nome}</td>
                <td>${cliente.cpf}</td>
                <td>${cliente.telefone || "S/N"}</td>
                <td>
                    <button class="btn-excluir" onclick="deletarCliente(${cliente.id})">Excluir</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error("Erro ao carregar clientes:", error);
    }
}

// Função para excluir cliente
async function deletarCliente(id) {
    if (!confirm("Deseja realmente excluir este cliente?")) return;

    try {
        // Envia requisição DELETE passando as credenciais de auditoria na URL (Query Params)
        const resposta = await fetch(`${API_URL}/${id}?id_usuario_logado=1&nome_usuario_logado=Admin`, {
            method: "DELETE"
        });

        if (resposta.ok) {
            listarClientes(); // Atualiza a tabela após exclusão
        } else {
            alert("Erro ao excluir cliente.");
        }
    } catch (error) {
        console.error("Erro ao excluir:", error);
    }
}