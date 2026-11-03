const usuario = iniciarPagina({ pagina: "relatorios", titulo: "Relatórios", apenasAdmin: true });
const $ = id => document.getElementById(id);

/* ---------- ajudantes para montar as colunas */
const T = (rotulo, fn, num = false) => ({ rotulo, num, html: l => esc(fn(l)), csv: fn });                       // coluna de texto simples
const H = (rotulo, html, csv, num = false) => ({ rotulo, num, html, csv });                                       // coluna com HTML próprio
const dinheiroCsv = v => (v === null || v === undefined ? "" : Number(v).toFixed(2).replace(".", ","));
const rodape = (colunas, mapa) => colunas.map((_, i) => mapa[i] ?? "");
const SIM = v => (v ? "Sim" : "Não");

const colMovimentacoes = [
    H("Placa", l => placaHtml(l.placa), l => l.placa),
    T("Veículo", l => nomeVeiculo(l)),
    T("Cliente", l => l.cliente_nome || "—"),
    T("Vaga", l => l.codigo_vaga),
    T("Entrada", l => dataHora(l.data_entrada)),
    T("Entrada registrada por", l => l.entrada_por || "—"),
    T("Saída", l => l.data_saida ? dataHora(l.data_saida) : "no pátio"),
    T("Saída registrada por", l => l.saida_por || "—"),
    T("Permanência", l => duracao(l.permanencia_minutos), true),
    H("Valor", l => moeda(l.valor_cobrado), l => dinheiroCsv(l.valor_cobrado), true),
    H("Liberação por código", l => l.liberado_por ? `<span class="selo pendente">${esc(l.liberado_por)}</span><div class="ajuda">${esc(l.obs_liberacao || "")}</div>` : "—",
        l => l.liberado_por ? `${l.liberado_por} (${l.obs_liberacao || ""})` : ""),
];
const resumoMov = r => `${r.totais.entradas} entrada(s) · ${r.totais.saidas} saída(s) · ${r.totais.no_patio} ainda no pátio · ${moeda(r.totais.valor_cobrado)} cobrados`;
const rodapeMov = r => rodape(colMovimentacoes, { 0: "Total", 9: moeda(r.totais.valor_cobrado) });

const periodoTexto = (r, dia) => dia ? dataCurta(r) : r.split("-").reverse().join("/");

const colPorVeiculo = [
    H("Placa", l => placaHtml(l.placa), l => l.placa), T("Veículo", l => nomeVeiculo(l)), T("Cliente", l => l.cliente_nome || "—"),
    T("Visitas", l => l.visitas, true), T("Tempo total", l => duracao(l.minutos), true),
    H("Valor pago", l => moeda(l.valor_cobrado), l => dinheiroCsv(l.valor_cobrado), true),
];

function colAgrupado(dia) {
    return [
        T(dia ? "Dia" : "Mês", l => periodoTexto(l.periodo, dia)), T("Entradas", l => l.entradas, true), T("Saídas", l => l.saidas, true),
        H("Receita", l => moeda(l.receita), l => dinheiroCsv(l.receita), true),
    ];
}

const colPagamentos = [
    T("Cliente", l => l.cliente_nome || "—"),
    H("Placa", l => l.placa ? placaHtml(l.placa) : "—", l => l.placa || ""),
    T("Tipo", l => l.tipo_cobranca === "Hora" ? "Por hora" : "Mensal"),
    H("Valor", l => moeda(l.valor_total), l => dinheiroCsv(l.valor_total), true),
    H("Situação", l => `<span class="selo ${l.status === "Pago" ? "pago" : "pendente"}">${esc(l.status)}</span>`, l => l.status),
    T("Forma", l => l.forma_pagamento || "—"),
    H("Dinheiro entregue", l => l.valor_recebido != null ? moeda(l.valor_recebido) : "—", l => dinheiroCsv(l.valor_recebido), true),
    H("Troco", l => l.troco != null ? moeda(l.troco) : "—", l => dinheiroCsv(l.troco), true),
    T("Vencimento", l => dataCurta(l.data_vencimento)), T("Pago em", l => dataHora(l.data_pagamento)),
    T("Recebido por", l => l.recebido_por || "—"),
];

const colRecebimentos = [
    T("Cliente", l => l.cliente), T("Pagamentos", l => l.pagamentos, true),
    H("Total pago", l => moeda(l.total_pago), l => dinheiroCsv(l.total_pago), true), T("Formas", l => l.formas), T("Último pagamento", l => dataHora(l.ultimo_pagamento)),
];

const colCaixa = [
    T("Recebido por", l => l.recebido_por), T("Forma de pagamento", l => l.forma), T("Pagamentos", l => l.pagamentos, true),
    H("Total", l => moeda(l.total), l => dinheiroCsv(l.total), true),
    H("Dinheiro entregue", l => l.forma === "Dinheiro" ? moeda(l.entregue) : "—", l => l.forma === "Dinheiro" ? dinheiroCsv(l.entregue) : "", true),
    H("Troco devolvido", l => l.forma === "Dinheiro" ? moeda(l.troco) : "—", l => l.forma === "Dinheiro" ? dinheiroCsv(l.troco) : "", true),
];

const colInadimplentes = [
    T("Cliente", l => l.nome), T("Documento", l => l.cpf), T("Telefone", l => l.telefone || "—"),
    H("Dias em atraso", l => `<span class="dias">${l.dias_atraso}</span>`, l => l.dias_atraso, true),
    H("Valor em aberto", l => moeda(l.valor_em_aberto), l => dinheiroCsv(l.valor_em_aberto), true), T("Cobranças vencidas", l => l.cobrancas_vencidas, true),
];

const colClientes = [
    T("Nome", l => l.nome), T("Documento", l => l.documento), T("Tipo", l => l.tipo_documento), T("País", l => l.pais + (l.estrangeiro ? " (estrangeiro)" : "")),
    T("Telefone", l => (l.telefone || "—") + (l.telefone_whatsapp ? " (WhatsApp)" : "")), T("Telefone 2", l => l.telefone2 ? l.telefone2 + (l.telefone2_whatsapp ? " (WhatsApp)" : "") : "—"),
    T("Plano", l => l.plano), T("Veículos", l => l.veiculos || "—"), T("Cidade", l => l.cidade || "—"),
    T("Inadimplente", l => l.dias_atraso ? `há ${l.dias_atraso} dia(s)` : "Não"),
];

const colVeiculosCad = [
    H("Placa", l => placaHtml(l.placa), l => l.placa), T("Tipo", l => l.tipo_veiculo), T("Marca / modelo", l => nomeVeiculo(l)), T("Cor", l => l.cor || "—"),
    T("Proprietário", l => l.cliente_nome), T("Documento", l => l.cliente_cpf), T("No pátio", l => SIM(l.no_patio)),
];

/* ---------- relatórios disponíveis */
const OPCOES_CAD = {
    clientes: [["", "Todos os clientes"], ["mensalista", "Só mensalistas"], ["premium", "Só premium"], ["horista", "Só horistas"], ["inadimplente", "Só inadimplentes"]],
    veiculos: [["", "Carros e motos"], ["Carro", "Só carros"], ["Moto", "Só motos"]],
};

const seletorVeiculo = seletorComBusca($("f-veic-busca"), async termo => {
    const lista = await api("/veiculos/busca", { params: { q: termo } });
    return lista.map(v => ({ id: v.id, rotulo: `${v.placa} · ${nomeVeiculo(v)} (${v.cliente_nome})` }));
});

function definicao(tipo, p) {
    const periodo = { inicio: p.inicio, fim: p.fim };
    switch (tipo) {
        case "movimentacoes":
            return { titulo: "Entradas e saídas", rota: "/relatorios/movimentacoes", params: { ...periodo, placa: p.placa, id_veiculo: p.idVeiculo }, colunas: colMovimentacoes, resumo: resumoMov, rodape: rodapeMov };
        case "veiculo":
            if (p.idVeiculo) return { titulo: `Histórico do veículo ${p.rotuloVeiculo}`, rota: "/relatorios/movimentacoes", params: { ...periodo, id_veiculo: p.idVeiculo }, colunas: colMovimentacoes, resumo: resumoMov, rodape: rodapeMov };
            return { titulo: "Resumo por veículo", rota: "/relatorios/por-veiculo", params: periodo, colunas: colPorVeiculo,
                resumo: r => `${r.itens.length} veículo(s) no período`,
                rodape: r => rodape(colPorVeiculo, { 0: "Total", 3: r.itens.reduce((s, i) => s + i.visitas, 0), 5: moeda(r.itens.reduce((s, i) => s + i.valor_cobrado, 0)) }) };
        case "dia": case "mes": {
            const dia = tipo === "dia", c = colAgrupado(dia);
            return { titulo: dia ? "Resumo por dia" : "Resumo por mês", rota: "/relatorios/agrupado", params: { ...periodo, periodo: tipo }, colunas: c,
                resumo: r => `${r.totais.entradas} entrada(s) · ${r.totais.saidas} saída(s) · ${moeda(r.totais.receita)} de receita`,
                rodape: r => rodape(c, { 0: "Total", 1: r.totais.entradas, 2: r.totais.saidas, 3: moeda(r.totais.receita) }) };
        }
        case "pagamentos":
            return { titulo: "Pagamentos", rota: "/relatorios/pagamentos", params: { ...periodo, status_pagamento: p.status, tipo: p.tipoPag, forma: p.forma, cliente: p.cliente }, colunas: colPagamentos,
                resumo: r => `${r.totais.quantidade} lançamento(s) · recebido ${moeda(r.totais.total_pago)} · pendente ${moeda(r.totais.total_pendente)}` +
                    (Object.keys(r.totais.por_forma).length ? " · por forma: " + Object.entries(r.totais.por_forma).map(([f, v]) => `${f} ${moeda(v)}`).join(", ") : "") +
                    (r.totais.dinheiro_liquido ? ` · dinheiro em caixa ${moeda(r.totais.dinheiro_liquido)} (troco devolvido ${moeda(r.totais.troco_devolvido)})` : ""),
                rodape: r => rodape(colPagamentos, { 0: "Recebido", 3: moeda(r.totais.total_pago), 7: moeda(r.totais.troco_devolvido) }) };
        case "recebimentos":
            return { titulo: "Recebimentos por cliente", rota: "/relatorios/recebimentos-por-cliente", params: periodo, colunas: colRecebimentos,
                resumo: r => `${r.totais.clientes} cliente(s) pagaram ${moeda(r.totais.total_pago)}`,
                rodape: r => rodape(colRecebimentos, { 0: "Total", 2: moeda(r.totais.total_pago) }) };
        case "caixa":
            return { titulo: "Fechamento de caixa", rota: "/relatorios/caixa", params: periodo, colunas: colCaixa,
                resumo: r => `Entrou ${moeda(r.totais.total_geral)} · em dinheiro: entregue ${moeda(r.totais.dinheiro_entregue)}, troco devolvido ${moeda(r.totais.troco_devolvido)}, saldo em espécie ${moeda(r.totais.dinheiro_liquido)}`,
                rodape: r => rodape(colCaixa, { 0: "Total", 3: moeda(r.totais.total_geral), 4: moeda(r.totais.dinheiro_entregue), 5: moeda(r.totais.troco_devolvido) }) };
        case "inadimplentes":
            return { titulo: "Clientes inadimplentes", rota: "/relatorios/inadimplentes", params: {}, colunas: colInadimplentes, semPeriodo: true,
                resumo: r => `${r.totais.clientes} cliente(s) · ${moeda(r.totais.valor_em_aberto)} em aberto`,
                rodape: r => rodape(colInadimplentes, { 0: "Total", 4: moeda(r.totais.valor_em_aberto) }) };
        case "clientes":
            return { titulo: "Clientes cadastrados", rota: "/relatorios/clientes", params: { tipo: p.cadTipo, pais: p.pais, nome: p.nome, documento: p.doc }, colunas: colClientes, semPeriodo: true,
                resumo: r => `${r.totais.clientes} cliente(s) · ${r.totais.mensalistas} mensalista(s) · ${r.totais.inadimplentes} inadimplente(s) · ${r.totais.estrangeiros} estrangeiro(s)`, rodape: null };
        case "veiculos":
            return { titulo: "Veículos cadastrados", rota: "/relatorios/veiculos", params: { tipo: p.cadTipo, q: p.q }, colunas: colVeiculosCad, semPeriodo: true,
                resumo: r => `${r.totais.veiculos} veículo(s) · ${r.totais.carros} carro(s) · ${r.totais.motos} moto(s) · ${r.totais.no_patio} no pátio agora`, rodape: null };
    }
}

/* ---------- quais filtros aparecem em cada relatório */
const CONTROLES = {
    movimentacoes: ["inicio", "fim", "veiculo", "placa"], veiculo: ["inicio", "fim", "veiculo"], dia: ["inicio", "fim"], mes: ["inicio", "fim"],
    pagamentos: ["inicio", "fim", "cliente", "status", "tipo", "forma"], recebimentos: ["inicio", "fim"], caixa: ["inicio", "fim"], inadimplentes: [],
    clientes: ["nome", "doc", "cadtipo", "pais"], veiculos: ["cadtipo", "q"],
};
const TODOS = ["inicio", "fim", "veiculo", "placa", "cliente", "status", "tipo", "forma", "nome", "doc", "cadtipo", "pais", "q"];

function ajustarControles() {
    const tipo = $("tipo-rel").value, mostrar = CONTROLES[tipo];
    TODOS.forEach(c => { $(`campo-${c}`).hidden = !mostrar.includes(c); });
    $("atalhos").hidden = !mostrar.includes("inicio");
    if (OPCOES_CAD[tipo]) $("f-cadtipo").innerHTML = OPCOES_CAD[tipo].map(([v, r]) => `<option value="${v}">${r}</option>`).join("");
}
$("tipo-rel").addEventListener("change", ajustarControles);

/* ---------- período (sempre pela data do SERVIDOR) */
const definirPeriodo = (a, b) => { $("inicio").value = a; $("fim").value = b; };
document.querySelectorAll("[data-atalho]").forEach(b => b.addEventListener("click", () => {
    const h = agoraServidor();
    if (b.dataset.atalho === "hoje") definirPeriodo(isoLocal(h), isoLocal(h));
    else if (b.dataset.atalho === "mes") definirPeriodo(isoLocal(new Date(h.getFullYear(), h.getMonth(), 1)), isoLocal(h));
    else definirPeriodo(isoLocal(new Date(h.getFullYear(), h.getMonth() - 1, 1)), isoLocal(new Date(h.getFullYear(), h.getMonth(), 0)));
}));

/* ---------- gerar e desenhar */
let atual = null;

$("form-rel").addEventListener("submit", async ev => {
    ev.preventDefault();
    const tipo = $("tipo-rel").value;
    if (CONTROLES[tipo].includes("inicio") && (!$("inicio").value || !$("fim").value)) { aviso("Informe o período do relatório (data inicial e final).", "erro"); return; }
    if ($("inicio").value > $("fim").value) { aviso("A data inicial não pode ser maior que a final.", "erro"); return; }
    if ($("f-veic-busca").value.trim() && !seletorVeiculo.valor()) { aviso("Escolha o veículo na lista de sugestões (ou apague o campo para ver todos).", "erro"); return; }
    const p = {
        inicio: $("inicio").value, fim: $("fim").value, placa: $("f-placa").value, idVeiculo: seletorVeiculo.valor(), rotuloVeiculo: $("f-veic-busca").value.split(" · ")[0],
        cliente: $("f-cliente").value, status: $("f-status").value, tipoPag: $("f-tipo").value, forma: $("f-forma").value,
        nome: $("f-nome").value, doc: $("f-doc").value, cadTipo: $("f-cadtipo").value, pais: $("f-pais").value, q: $("f-q").value,
    };
    const def = definicao(tipo, p);
    try {
        atual = { def, dados: await api(def.rota, { params: def.params }), tipo };
        desenhar();
    } catch (e) { erroAviso(e); }
});

function desenhar() {
    const { def, dados, tipo } = atual;
    $("resultado").hidden = false;
    $("titulo-rel").textContent = def.semPeriodo || !dados.inicio ? `${def.titulo} — posição de hoje` : `${def.titulo} — ${dataCurta(dados.inicio)} a ${dataCurta(dados.fim)}`;
    $("resumo-rel").textContent = def.resumo(dados);
    $("thead-rel").innerHTML = `<tr>${def.colunas.map(c => `<th class="${c.num ? "num" : ""}">${c.rotulo}</th>`).join("")}</tr>`;
    $("tbody-rel").innerHTML = dados.itens.length
        ? dados.itens.map(l => `<tr>${def.colunas.map(c => `<td class="${c.num ? "num" : ""}">${c.html(l)}</td>`).join("")}</tr>`).join("")
        : `<tr><td colspan="${def.colunas.length}" class="vazio">Nada encontrado com esses filtros.</td></tr>`;
    $("tfoot-rel").innerHTML = def.rodape && dados.itens.length
        ? `<tr>${def.rodape(dados).map((c, i) => `<td class="${def.colunas[i].num ? "num" : ""}">${c}</td>`).join("")}</tr>` : "";
}

$("btn-csv").addEventListener("click", () => {
    if (!atual) return;
    baixarCSV(`relatorio-${atual.tipo}-${hojeISO()}.csv`, atual.def.colunas, atual.dados.itens);
});
$("btn-imprimir").addEventListener("click", () => window.print());

if (usuario) {
    $("f-forma").innerHTML = `<option value="">Todas</option>${opcoesFormaPagamento()}`;
    ajustarControles();
    relogioPronto.then(() => { const h = agoraServidor(); definirPeriodo(isoLocal(new Date(h.getFullYear(), h.getMonth(), 1)), isoLocal(h)); });
}
