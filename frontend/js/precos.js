<<<<<<< HEAD
const usuario = iniciarPagina({ pagina: "precos", titulo: "Preços", apenasAdmin: true });
const CATEGORIAS = ["Carro", "Moto"];
const TIPOS = [
    { chave: "Horista", rotulo: "Valor da hora" },
    { chave: "Mensalista", rotulo: "Valor da mensalidade rotativa" },
    { chave: "Premium", rotulo: "Valor da mensalidade premium (vaga exclusiva)" },
];
const precos = {};   // "Carro|Horista" -> registro existente

function montarGrade() {
    document.getElementById("grade-precos").innerHTML = CATEGORIAS.map(cat => `
        <section class="painel"><h2>${cat}</h2>
            ${TIPOS.map(t => `
            <form class="form-grid" data-categoria="${cat}" data-tipo="${t.chave}" style="margin-bottom:14px">
                <div class="numero" style="padding:0"><div class="valor" id="atual-${cat}-${t.chave}">—</div><div class="rotulo">${t.chave === "Horista" ? "por hora" : t.chave === "Premium" ? "por mês, vaga exclusiva" : "por mês, por cota"} (atual)</div></div>
                <div class="campo"><label for="valor-${cat}-${t.chave}">${t.rotulo} (R$)</label>
                    <input id="valor-${cat}-${t.chave}" type="number" step="0.01" min="0.01" required></div>
                ${t.chave === "Horista" ? `
                <div class="campo"><label for="minimo-${cat}">Valor mínimo (R$)</label>
                    <input id="minimo-${cat}" type="number" step="0.01" min="0" value="0"></div>
                <div class="campo"><label for="tempo-${cat}">Mínimo cobre até (minutos)</label>
                    <input id="tempo-${cat}" type="number" step="1" min="0" max="1440" value="0"></div>` : ""}
                <div class="campo"><button class="btn" type="submit">Salvar</button></div>
            </form>`).join("")}
        </section>`).join("");
}

async function carregar() {
    try {
        Object.keys(precos).forEach(k => delete precos[k]);
        document.querySelectorAll("[data-minimo]").forEach(n => n.remove());
        (await api("/precos/")).forEach(p => { precos[`${p.categoria}|${p.tipo_cobranca}`] = p; });
        CATEGORIAS.forEach(cat => TIPOS.forEach(t => {
            const p = precos[`${cat}|${t.chave}`];
            document.getElementById(`atual-${cat}-${t.chave}`).textContent = p ? moeda(p.valor) : "não definido";
            if (t.chave === "Horista") {
                const textoMinimo = p && p.valor_minimo > 0 ? `mín. ${moeda(p.valor_minimo)} até ${p.tempo_minimo_minutos} min` : "";
                document.getElementById(`atual-${cat}-${t.chave}`).insertAdjacentHTML("afterend", textoMinimo ? `<div class="ajuda" data-minimo>${textoMinimo}</div>` : "");
            }
            if (p) document.getElementById(`valor-${cat}-${t.chave}`).value = p.valor;
            if (p && t.chave === "Horista") {
                document.getElementById(`minimo-${cat}`).value = p.valor_minimo || 0;
                document.getElementById(`tempo-${cat}`).value = p.tempo_minimo_minutos || 0;
            }
        }));
    } catch (e) { erroAviso(e); }
}

document.getElementById("grade-precos").addEventListener("submit", async ev => {
    ev.preventDefault();
    const form = ev.target.closest("form");
    const { categoria, tipo } = form.dataset;
    const valor = Number(document.getElementById(`valor-${categoria}-${tipo}`).value);
    if (!(valor > 0)) { aviso("Informe um valor maior que zero.", "erro"); return; }
    try {
        const corpo = { categoria, tipo_cobranca: tipo, valor };
        if (tipo === "Horista") {
            corpo.valor_minimo = Number(document.getElementById(`minimo-${categoria}`).value) || 0;
            corpo.tempo_minimo_minutos = Math.round(Number(document.getElementById(`tempo-${categoria}`).value) || 0);
        }
        const existente = precos[`${categoria}|${tipo}`];
        // já existe preço dessa combinação? então atualiza; senão cria
        if (existente) await api(`/precos/${existente.id}`, { metodo: "PUT", corpo });
        else await api("/precos/", { metodo: "POST", corpo });
        aviso("Preço atualizado.");
        carregar();
    } catch (e) { erroAviso(e); }
});

if (usuario) { montarGrade(); carregar(); }
=======
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
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272
