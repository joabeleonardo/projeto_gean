<<<<<<< HEAD
const usuario = iniciarPagina({ pagina: "vagas", titulo: "Vagas" });
const tbody = document.getElementById("tbody");
let vagas = [];
let donos = {};      // id da vaga premium -> nome do cliente que reservou
if (usuario && ehAdmin()) document.getElementById("bloco-form").hidden = false;

const seloTipo = v => v.tipo === "Premium" ? `<span class="selo premium" ${dica("Vaga exclusiva de um cliente com plano premium")}>Premium</span>`
    : v.tipo === "Mensalista" ? `<span class="selo mensalista" ${dica("Vaga rotativa: qualquer mensalista usa a que estiver livre")}>Mensalista</span>`
    : `<span class="selo" ${dica("Vaga para quem paga por hora")}>Horista</span>`;

function situacao(v) {
    if (!v.ativa) return `<span class="selo inativa" ${dica("Fora de uso (ex.: reforma): não recebe entradas")}>Inativa</span>`;
    return `<span class="selo ${v.status === "Livre" ? "livre" : "ocupada"}">${esc(v.status)}</span>`;
}

async function carregar() {
    try {
        const [lista, premium] = await Promise.all([api("/vagas/"), api("/mensalidades/vagas-premium")]);
        donos = Object.fromEntries(premium.filter(p => p.reservada_para).map(p => [p.id, p.reservada_para]));
        vagas = lista.sort((a, b) => a.codigo_vaga.localeCompare(b.codigo_vaga, "pt-BR", { numeric: true }));
        const ativas = vagas.filter(v => v.ativa);
        const livres = ativas.filter(v => v.status === "Livre").length;
        const inativas = vagas.length - ativas.length;
        document.getElementById("contagem").textContent =
            `${ativas.length} ativas · ${livres} livres${inativas ? ` · ${inativas} inativa(s)` : ""}`;
        tbody.innerHTML = vagas.length ? vagas.map(v => `<tr class="${v.ativa ? "" : "linha-inativa"}">
            <td><strong>${esc(v.codigo_vaga)}</strong></td>
            <td>${esc(v.categoria || "Carro")}</td>
            <td>${seloTipo(v)}${donos[v.id] ? `<div class="ajuda">reservada: ${esc(donos[v.id])}</div>` : (v.tipo === "Premium" ? `<div class="ajuda">sem reserva</div>` : "")}</td>
            <td>${situacao(v)}</td>
            <td class="acoes-celula">${ehAdmin() ? `
                <button class="btn sec pequeno" data-editar="${v.id}" ${dica("Mudar código, tipo de uso ou se é para carro/moto")}>Editar</button>
                <button class="btn sec pequeno" data-situacao="${v.id}" data-ativa="${v.ativa ? "0" : "1"}" ${dica(v.ativa ? "Tirar a vaga de uso (ex.: reforma): ela deixa de aparecer como disponível" : "Colocar a vaga de volta em uso")}>${v.ativa ? "Inativar" : "Ativar"}</button>
                <button class="btn perigo pequeno" data-excluir="${v.id}" data-codigo="${esc(v.codigo_vaga)}" ${dica("Apagar a vaga (para reforma, prefira Inativar)")}>Excluir</button>` : ""}</td></tr>`).join("")
            : `<tr><td colspan="5" class="vazio">Nenhuma vaga cadastrada.</td></tr>`;
    } catch (e) { erroAviso(e); }
}

document.getElementById("form-vaga").addEventListener("submit", async ev => {
    ev.preventDefault();
    const codigo = document.getElementById("codigo").value.trim();
    if (!codigo) { aviso("Preencha o código da vaga.", "erro"); return; }
    try {
        await api("/vagas/", { metodo: "POST", corpo: { codigo_vaga: codigo, tipo: document.getElementById("tipo").value, categoria: document.getElementById("categoria").value, status: "Livre" } });
        aviso("Vaga cadastrada.");
        ev.target.reset();
        carregar();
    } catch (e) { erroAviso(e); }
});

function abrirEdicao(v) {
    const ocupada = v.status === "Ocupada";
    const dlg = document.createElement("dialog");
    dlg.innerHTML = `<form class="dialogo-corpo" novalidate>
        <h2>Editar vaga ${esc(v.codigo_vaga)}</h2>
        ${ocupada ? `<p class="erro-form">Vaga ocupada: só o código pode ser alterado agora. Para mudar o tipo ou o veículo, registre a saída antes.</p>` : ""}
        ${donos[v.id] ? `<p class="caixa-info">Vaga premium reservada para ${esc(donos[v.id])}: o tipo só muda depois de cancelar o plano.</p>` : ""}
        <div class="form-grid coluna-unica" style="margin-top:10px">
            <div class="campo"><label for="ev-codigo">Código da vaga</label><input id="ev-codigo" maxlength="10" value="${esc(v.codigo_vaga)}"></div>
            <div class="campo"><label for="ev-cat">Para qual veículo?</label><select id="ev-cat" ${ocupada || donos[v.id] ? "disabled" : ""}><option>Carro</option><option>Moto</option></select></div>
            <div class="campo"><label for="ev-tipo">Tipo de uso</label><select id="ev-tipo" ${ocupada || donos[v.id] ? "disabled" : ""}><option value="Horista">Horista</option><option value="Mensalista">Mensalista rotativa</option><option value="Premium">Premium (exclusiva)</option></select></div>
        </div>
        <div class="acoes"><button class="btn" type="submit">Salvar alterações</button><button class="btn sec" type="button" data-fechar>Cancelar</button></div>
    </form>`;
    document.body.appendChild(dlg);
    dlg.querySelector("#ev-cat").value = v.categoria || "Carro";
    dlg.querySelector("#ev-tipo").value = v.tipo;
    dlg.addEventListener("close", () => dlg.remove());
    dlg.querySelector("[data-fechar]").addEventListener("click", () => dlg.close());
    dlg.querySelector("form").addEventListener("submit", async ev => {
        ev.preventDefault();
        const codigo = dlg.querySelector("#ev-codigo").value.trim();
        if (!codigo) { aviso("Preencha o código da vaga.", "erro"); return; }
        const corpo = { codigo_vaga: codigo, categoria: ocupada || donos[v.id] ? v.categoria : dlg.querySelector("#ev-cat").value, tipo: ocupada || donos[v.id] ? v.tipo : dlg.querySelector("#ev-tipo").value };
        try {
            await api(`/vagas/${v.id}`, { metodo: "PUT", corpo });
            dlg.close();
            aviso("Vaga atualizada.");
            carregar();
        } catch (e) { erroAviso(e); }
    });
    dlg.showModal();
}

tbody.addEventListener("click", async ev => {
    const editar = ev.target.closest("[data-editar]"), sit = ev.target.closest("[data-situacao]"), ex = ev.target.closest("[data-excluir]");
    try {
        if (editar) abrirEdicao(vagas.find(v => String(v.id) === editar.dataset.editar));
        else if (sit) {
            const ativar = sit.dataset.ativa === "1";
            if (!ativar && !await confirmar("Ela deixa de aparecer como disponível e não recebe entradas até ser ativada de novo.", { titulo: "Inativar esta vaga?", sim: "Inativar", perigo: true })) return;
            await api(`/vagas/${sit.dataset.situacao}/situacao`, { metodo: "PUT", corpo: { ativa: ativar } });
            aviso(ativar ? "Vaga ativada." : "Vaga inativada.");
            carregar();
        } else if (ex && await confirmar("Para uma vaga em reforma, prefira Inativar. Excluir apaga a vaga de vez.", { titulo: `Excluir a vaga ${ex.dataset.codigo}?`, sim: "Excluir", perigo: true })) {
            await api(`/vagas/${ex.dataset.excluir}`, { metodo: "DELETE" });
            aviso("Vaga excluída.");
            carregar();
        }
    } catch (e) { erroAviso(e); }
});

if (usuario) carregar();
=======
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
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272
