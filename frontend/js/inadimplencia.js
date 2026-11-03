const usuario = iniciarPagina({ pagina: "inadimplencia", titulo: "Inadimplência" });
const $ = id => document.getElementById(id);
const tbody = $("tbody");
let lista = [];

const contato = c => (c.telefone ? `<div>${esc(c.telefone)} <a class="selo whatsapp" href="${whatsLink(c.telefone)}" target="_blank" rel="noopener" ${dica("Abrir conversa no WhatsApp para cobrar")}>WhatsApp</a></div>` : "—");

async function carregarPagina({ pagina, por_pagina }) {
    const r = await api("/clientes/inadimplentes/pagina", { params: { nome: $("f-nome").value.trim(), documento: $("f-doc").value.trim(), pagina, por_pagina } });
    lista = r.itens;
    $("resumo-inad").textContent = r.total ? `${r.total} cliente(s) · ${moeda(r.valor_em_aberto)} em aberto` : "";
    tbody.innerHTML = r.itens.length ? r.itens.map(i => `<tr data-id="${i.id}">
        <td><strong>${esc(i.nome)}</strong></td><td>${esc(i.cpf)}</td><td>${contato(i)}</td>
        <td class="num"><span class="dias">${i.dias_atraso} dia(s)</span></td>
        <td class="num">${moeda(i.valor_em_aberto)} <span class="ajuda">(${i.cobrancas_vencidas})</span></td>
        <td class="acoes-celula"><button class="btn pequeno" data-cobrancas="${i.id}" ${dica("Ver as cobranças pendentes deste cliente e dar baixa quando ele pagar")}>Cobranças / receber</button></td></tr>`).join("")
        : `<tr><td colspan="6" class="vazio">Nenhum cliente inadimplente. 🎉</td></tr>`;
    return r;
}

const paginador = criarPaginador($("paginador"), carregarPagina);
const filtrar = debounce(() => paginador.primeira(), 350);
["f-nome", "f-doc"].forEach(id => $(id).addEventListener("input", filtrar));
$("btn-limpar").addEventListener("click", () => { $("f-nome").value = $("f-doc").value = ""; paginador.primeira(); });

async function abrirCobrancas(cliente) {
    let itens;
    try { itens = await api(`/clientes/${cliente.id}/cobrancas-pendentes`); } catch (e) { erroAviso(e); return; }
    const dlg = document.createElement("dialog");
    dlg.className = "largo";
    dlg.innerHTML = `<div class="dialogo-corpo"><h2>Cobranças pendentes — ${esc(cliente.nome)}</h2>
        <div class="tabela-rolagem"><table><thead><tr><th>Vencimento</th><th class="num">Valor</th><th class="num">Atraso</th><th></th></tr></thead><tbody>
        ${itens.map(c => `<tr><td>${dataCurta(c.data_vencimento)}</td><td class="num">${moeda(c.valor_total)}</td>
            <td class="num">${c.dias_atraso ? `<span class="dias">${c.dias_atraso} dia(s)</span>` : "em dia"}</td>
            <td><button class="btn pequeno" data-baixa="${c.id}" data-valor="${c.valor_total}" ${dica("Registrar o pagamento desta cobrança")}>Dar baixa</button></td></tr>`).join("") || `<tr><td colspan="4" class="vazio">Sem cobranças pendentes.</td></tr>`}
        </tbody></table></div>
        <div class="acoes"><button class="btn sec" data-fechar type="button">Fechar</button></div></div>`;
    document.body.appendChild(dlg);
    dlg.addEventListener("close", () => dlg.remove());
    dlg.querySelector("[data-fechar]").addEventListener("click", () => dlg.close());
    dlg.addEventListener("click", ev => {
        const b = ev.target.closest("[data-baixa]");
        if (b) abrirBaixa(b.dataset.baixa, b.dataset.valor, () => { dlg.close(); paginador.recarregar(); });
    });
    dlg.showModal();
}

tbody.addEventListener("click", ev => {
    const b = ev.target.closest("[data-cobrancas]");
    if (b) abrirCobrancas(lista.find(i => String(i.id) === b.dataset.cobrancas));
});

if (usuario) paginador.recarregar();
