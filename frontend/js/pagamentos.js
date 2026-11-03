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
