const usuario = iniciarPagina({ pagina: "logs", titulo: "Logs do sistema", apenasAdmin: true });
const $ = id => document.getElementById(id);
const tbody = $("tbody");

const ROTULO_ACAO = { CRIAR: "Cadastro", ALTERAR: "Alteração", EXCLUIR: "Exclusão", ENTRADA: "Entrada", SAIDA: "Saída", PAGAMENTO: "Pagamento", LOGIN: "Login" };

function filtros() {
    return { inicio: $("f-inicio").value, fim: $("f-fim").value, id_usuario: $("f-usuario").value, entidade: $("f-entidade").value,
             acao: $("f-acao").value, q: $("f-q").value.trim() };
}

async function carregarPagina({ pagina, por_pagina }) {
    const r = await api("/logs/", { params: { ...filtros(), pagina, por_pagina } });
    tbody.innerHTML = r.itens.length ? r.itens.map(l => `<tr>
        <td>${dataHora(l.data_hora)}</td><td>${esc(l.usuario)}</td>
        <td><span class="selo ${l.acao === "EXCLUIR" ? "ocupada" : l.acao === "ALTERAR" ? "pendente" : "livre"}">${esc(ROTULO_ACAO[l.acao] || l.acao)}</span></td>
        <td>${esc(l.descricao)}</td></tr>`).join("")
        : `<tr><td colspan="4" class="vazio">Nenhum registro encontrado com esses filtros.</td></tr>`;
    return r;
}

const paginador = criarPaginador($("paginador"), carregarPagina);
const filtrar = debounce(() => paginador.primeira(), 350);
$("f-q").addEventListener("input", filtrar);
["f-inicio", "f-fim", "f-usuario", "f-entidade", "f-acao"].forEach(id => $(id).addEventListener("change", () => paginador.primeira()));
$("btn-limpar").addEventListener("click", () => { ["f-inicio", "f-fim", "f-usuario", "f-entidade", "f-acao", "f-q"].forEach(id => { $(id).value = ""; }); paginador.primeira(); });

$("btn-csv").addEventListener("click", async () => {
    try {
        const r = await api("/logs/", { params: { ...filtros(), pagina: 1, por_pagina: 5000 } });
        baixarCSV("logs-do-sistema.csv", [
            { rotulo: "Data e hora", csv: l => dataHora(l.data_hora) }, { rotulo: "Usuário", chave: "usuario" },
            { rotulo: "Ação", csv: l => ROTULO_ACAO[l.acao] || l.acao }, { rotulo: "Registro", chave: "entidade" },
            { rotulo: "Campo", chave: "campo" }, { rotulo: "Valor antigo", chave: "valor_antigo" }, { rotulo: "Valor novo", chave: "valor_novo" },
            { rotulo: "Descrição", chave: "descricao" },
        ], r.itens);
        if (r.total > r.itens.length) aviso(`Exportados os ${r.itens.length} registros mais recentes de ${r.total}. Refine o período para ver o restante.`);
    } catch (e) { erroAviso(e); }
});

if (usuario) {
    api("/usuarios/").then(us => { $("f-usuario").innerHTML += us.map(u => `<option value="${u.id}">${esc(u.nome)}</option>`).join(""); }).catch(() => { });
    relogioPronto.then(() => { $("f-fim").value = hojeISO(); const d = agoraServidor(); d.setDate(d.getDate() - 7); $("f-inicio").value = isoLocal(d); paginador.recarregar(); });
}
