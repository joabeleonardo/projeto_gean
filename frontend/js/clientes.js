const usuario = iniciarPagina({ pagina: "clientes", titulo: "Clientes" });
const $ = id => document.getElementById(id);
const tbody = $("tbody");
let clientes = [];

/* ------------------------------------------------------------ listagem */
function contato(c) {
    const linha = (tel, whats) => !tel ? "" : `<div>${esc(tel)} ${whats ? `<a class="selo whatsapp" href="${whatsLink(tel)}" target="_blank" rel="noopener" ${dica("Abrir conversa no WhatsApp")}>WhatsApp</a>` : ""}</div>`;
    return (linha(c.telefone, c.telefone_whatsapp) + linha(c.telefone2, c.telefone2_whatsapp)) || "—";
}

function celulaPlano(c) {
    if (!c.planos.length) return `<span class="selo">Horista</span>`;
    return c.planos.map(p => p.tipo_plano === "Premium"
        ? `<span class="selo premium" ${dica("Plano premium: vaga exclusiva do cliente")}>Premium · ${esc(p.categoria)} · vaga ${esc(p.codigo_vaga || "—")}${p.vigente ? "" : ` · a partir de ${dataCurta(p.data_inicio)}`}</span>`
        : `<span class="selo mensalista" ${dica("Plano rotativo: usa a vaga de mensalista que estiver livre")}>Mensalista · ${esc(p.categoria)} · ${p.cotas} cota(s)${p.vigente ? "" : ` · a partir de ${dataCurta(p.data_inicio)}`}</span>`).join(" ");
}

function filtros() {
    return { nome: $("f-nome").value.trim(), documento: $("f-doc").value.trim(), telefone: $("f-tel").value.trim(), placa: $("f-placa").value.trim(),
             tipo: $("f-tipo").value, pais: $("f-pais").value, ordem: $("f-ordem").value };
}

/* só as linhas da página atual são pedidas ao servidor */
async function carregarPagina({ pagina, por_pagina }) {
    const r = await api("/clientes/pagina", { params: { ...filtros(), pagina, por_pagina } });
    clientes = r.itens;
    tbody.innerHTML = r.itens.length ? r.itens.map(c => `<tr data-id="${c.id}">
        <td>${esc(c.nome)}
            ${c.dias_atraso ? `<span class="selo ocupada" ${dica("Tem cobrança vencida e não paga")}>Inadimplente há ${c.dias_atraso} dia(s)</span>` : ""}
            ${c.estrangeiro ? `<span class="selo estrangeiro" ${dica("Cliente de fora do Brasil")}>Estrangeiro · ${esc(c.pais)}</span>` : ""}</td>
        <td><div>${esc(c.cpf)}</div><div class="ajuda">${esc(c.tipo_documento)}${c.tipo_documento === "CNPJ" ? " · pessoa jurídica" : ""}</div></td>
        <td>${contato(c)}</td><td>${celulaPlano(c)}</td>
        <td class="acoes-celula">
            <button class="btn sec pequeno" data-acao="editar" ${dica("Corrigir nome, telefones, país e endereço (CPF/CNPJ não pode ser alterado)")}>Editar</button>
            <button class="btn sec pequeno" data-acao="plano" ${dica("Ver, contratar, alterar cotas ou cancelar o plano de mensalista")}>Plano</button>
            <a class="btn sec pequeno" href="veiculos.html?q=${encodeURIComponent(c.cpf)}" ${dica("Ver os veículos deste cliente")}>Veículos</a>
            <a class="btn sec pequeno" href="cadastro.html?cliente=${c.id}" ${dica("Cadastrar mais um veículo para este cliente")}>Novo veículo</a>
            ${ehAdmin() ? `<button class="btn perigo pequeno" data-acao="excluir" ${dica("Excluir o cliente (só se não tiver veículos nem histórico)")}>Excluir</button>` : ""}
        </td></tr>`).join("")
        : `<tr><td colspan="5" class="vazio">Nenhum cliente encontrado.</td></tr>`;
    return r;
}

const paginador = criarPaginador($("paginador"), carregarPagina);
const filtrar = debounce(() => paginador.primeira(), 350);
["f-nome", "f-doc", "f-tel", "f-placa"].forEach(id => $(id).addEventListener("input", filtrar));
["f-tipo", "f-pais", "f-ordem"].forEach(id => $(id).addEventListener("change", () => paginador.primeira()));
$("btn-limpar").addEventListener("click", () => { ["f-nome", "f-doc", "f-tel", "f-placa"].forEach(id => { $(id).value = ""; }); $("f-tipo").value = $("f-pais").value = ""; $("f-ordem").value = "nome"; paginador.primeira(); });

/* -------------------------------------------------- diálogo: editar cadastro */
async function abrirEdicao(id) {
    let r;
    try { r = await api(`/cadastro/cliente/${id}`); } catch (e) { erroAviso(e); return; }
    const e = r.endereco || {}, c = r.cliente;
    const dlg = document.createElement("dialog");
    dlg.className = "largo";
    dlg.innerHTML = `<form class="dialogo-corpo" novalidate>
        <h2>Editar cadastro de ${esc(c.nome)}</h2>
        <div class="form-grid">
            <h3 class="sub-titulo">Cliente</h3>
            <div class="campo largo"><label for="ed-nome">Nome completo (ou razão social)</label><input id="ed-nome" value="${esc(c.nome)}" maxlength="100"></div>
            <div class="campo"><label for="ed-doc">${esc(c.tipo_documento)} <span class="dica-campo">(não editável)</span></label>
                <input id="ed-doc" class="somente-leitura" value="${esc(c.cpf)}" readonly disabled ${dica("O CPF/CNPJ não pode ser alterado pelo sistema. Se estiver errado, a correção é feita direto no banco de dados.")}></div>
            <div class="campo"><label for="ed-pais">País</label><input id="ed-pais" maxlength="60" value="${esc(c.pais || "Brasil")}"></div>
            <div class="campo"><label for="ed-tel">Telefone</label><input id="ed-tel" data-mascara="telefone" value="${esc(c.telefone || "")}"></div>
            <div class="campo"><label class="campo-check"><input type="checkbox" id="ed-wa" ${c.telefone_whatsapp ? "checked" : ""}> Telefone é WhatsApp</label></div>
            <div class="campo"><label for="ed-tel2">Telefone 2</label><input id="ed-tel2" data-mascara="telefone" value="${esc(c.telefone2 || "")}"></div>
            <div class="campo"><label class="campo-check"><input type="checkbox" id="ed-wa2" ${c.telefone2_whatsapp ? "checked" : ""}> Telefone 2 é WhatsApp</label></div>
            <h3 class="sub-titulo">Endereço <span class="ajuda">(digite o CEP para preencher sozinho)</span></h3>
            <div class="campo"><label for="ed-cep">CEP</label><input id="ed-cep" data-mascara="cep" value="${esc(e.cep || "")}"></div>
            <div class="campo largo"><label for="ed-logradouro">Rua / avenida</label><input id="ed-logradouro" maxlength="150" value="${esc(e.logradouro || "")}"></div>
            <div class="campo"><label for="ed-numero">Número</label><input id="ed-numero" maxlength="10" value="${esc(e.numero || "")}"></div>
            <div class="campo"><label for="ed-complemento">Complemento (opcional)</label><input id="ed-complemento" maxlength="50" value="${esc(e.complemento || "")}"></div>
            <div class="campo"><label for="ed-bairro">Bairro</label><input id="ed-bairro" maxlength="50" value="${esc(e.bairro || "")}"></div>
            <div class="campo"><label for="ed-cidade">Cidade</label><input id="ed-cidade" maxlength="50" value="${esc(e.cidade || "")}"></div>
            <div class="campo"><label for="ed-estado">UF</label><input id="ed-estado" maxlength="2" style="text-transform:uppercase" value="${esc(e.estado || "")}"></div>
        </div>
        <div class="acoes"><button class="btn" type="submit">Salvar alterações</button><button class="btn sec" type="button" data-fechar>Cancelar</button></div>
    </form>`;
    document.body.appendChild(dlg);
    dlg.addEventListener("close", () => dlg.remove());
    dlg.querySelector("[data-fechar]").addEventListener("click", () => dlg.close());
    ativarMascaras(dlg);
    ligarBuscaCep({ cep: "ed-cep", logradouro: "ed-logradouro", bairro: "ed-bairro", cidade: "ed-cidade", estado: "ed-estado", numero: "ed-numero" });

    const form = dlg.querySelector("form");
    const telCompleto = v => v.startsWith("+") ? digitos(v).length >= 8 : digitos(v).length >= 10;
    ativarSequencia(form, [
        { depende: null, campos: [
            { id: "ed-nome", validar: v => VALIDAR.nome(v, c.tipo_documento), julgar: v => v.length >= 3 },
            { id: "ed-pais", validar: VALIDAR.texto("o país") },
            { id: "ed-tel", opcional: true, validar: VALIDAR.telefone, julgar: telCompleto },
            { id: "ed-wa", opcional: true },
            { id: "ed-tel2", opcional: true, validar: VALIDAR.telefone, julgar: telCompleto },
            { id: "ed-wa2", opcional: true },
        ] },
        { depende: 0, campos: [
            { id: "ed-cep", opcional: true, validar: VALIDAR.cep, julgar: v => digitos(v).length >= 8 },
            { id: "ed-logradouro", opcional: true, validar: VALIDAR.texto("a rua") },
            { id: "ed-numero", opcional: true }, { id: "ed-complemento", opcional: true },
            { id: "ed-bairro", opcional: true }, { id: "ed-cidade", opcional: true },
            { id: "ed-estado", opcional: true, validar: VALIDAR.uf, julgar: v => v.length >= 2 },
        ] },
    ], () => {
        if (!digitos(form.querySelector("#ed-tel").value)) { form.querySelector("#ed-wa").checked = false; form.querySelector("#ed-wa").disabled = true; form.querySelector("#ed-tel2").disabled = true; form.querySelector("#ed-wa2").disabled = true; }
        else if (!form.querySelector("#ed-tel2").value.trim()) { form.querySelector("#ed-wa2").checked = false; form.querySelector("#ed-wa2").disabled = true; }
    });

    form.addEventListener("submit", async ev => {
        ev.preventDefault();
        const v = i => form.querySelector(`#ed-${i}`).value.trim();
        const falha = VALIDAR.nome(v("nome"), c.tipo_documento) || (v("pais").length < 2 ? "Preencha o país." : null) || VALIDAR.telefone(v("tel"))
            || (v("tel2") && !v("tel") ? "Informe o telefone principal antes do segundo telefone." : null) || VALIDAR.telefone(v("tel2"));
        if (falha) { aviso(falha, "erro"); return; }
        const corpo = { cliente: { nome: v("nome"), pais: v("pais"), telefone: v("tel") || null, telefone_whatsapp: form.querySelector("#ed-wa").checked,
                                   telefone2: v("tel2") || null, telefone2_whatsapp: form.querySelector("#ed-wa2").checked } };
        const end = { cep: v("cep"), logradouro: v("logradouro"), numero: v("numero"), complemento: v("complemento") || null,
                      bairro: v("bairro"), cidade: v("cidade"), estado: v("estado").toUpperCase() };
        if (end.cep || end.logradouro || end.numero || end.bairro || end.cidade || end.estado) {
            if (!(end.cep && end.logradouro && end.numero && end.bairro && end.cidade && end.estado)) { aviso("Endereço incompleto: preencha CEP, rua, número, bairro, cidade e UF.", "erro"); return; }
            if (VALIDAR.cep(end.cep)) { aviso(VALIDAR.cep(end.cep), "erro"); return; }
            corpo.endereco = end;
        }
        try {
            await api(`/cadastro/cliente/${id}`, { metodo: "PUT", corpo });
            dlg.close();
            aviso("Cadastro atualizado.");
            paginador.recarregar();
        } catch (er) { erroAviso(er); }
    });
    dlg.showModal();
}

/* ------------------------------------------------- diálogo: plano de mensalista */
async function abrirPlano(cliente) {
    let dados, capacidade, precos, premium;
    try {
        [dados, capacidade, precos, premium] = await Promise.all([api(`/cadastro/cliente/${cliente.id}`), api("/mensalidades/capacidade"), api("/precos/"), api("/mensalidades/vagas-premium")]);
    } catch (e) { erroAviso(e); return; }
    const preco = (cat, tipo) => (precos.find(p => p.categoria === cat && p.tipo_cobranca === (tipo === "Premium" ? "Premium" : "Mensalista")) || {}).valor;
    const dlg = document.createElement("dialog");
    dlg.className = "largo";

    function desenharDialogo() {
        const lista = dados.mensalidades;
        dlg.innerHTML = `<div class="dialogo-corpo">
            <h2>Plano de mensalista — ${esc(cliente.nome)}</h2>
            <h3 class="sub-titulo">Planos ativos</h3>
            ${lista.length ? lista.map(p => `<div class="plano-item">
                <div><strong>${p.tipo_plano === "Premium" ? `Premium · vaga ${esc(p.codigo_vaga || "—")}` : `Rotativo · ${p.cotas} cota(s)`} · ${esc(p.categoria)}</strong>
                    <div class="ajuda">${p.vigente ? "Em vigor" : "Começa"} desde ${dataCurta(p.data_inicio)} · ${p.valor_mensal !== null ? moeda(p.valor_mensal) + "/mês" : "preço não definido"} · ${p.em_uso} em uso agora</div></div>
                ${ehAdmin() ? `<div class="acoes">${p.tipo_plano === "Premium" ? "" : `<button class="btn sec pequeno" data-cotas="${p.id}" data-atual="${p.cotas}" ${dica("Mudar a quantidade de veículos que o cliente pode ter no pátio ao mesmo tempo")}>Alterar cotas</button>`}
                    <button class="btn perigo pequeno" data-cancelar="${p.id}" ${dica("Encerrar o plano: o cliente volta a ser horista")}>Cancelar plano</button></div>` : ""}</div>`).join("")
                : `<p class="ajuda">Este cliente é horista (sem plano de mensalista).</p>`}
            <h3 class="sub-titulo" style="margin-top:14px">Aderir a um novo plano</h3>
            <form id="form-adesao" class="form-grid" novalidate>
                <div class="campo"><label for="pl-tipo">Tipo de plano</label><select id="pl-tipo"><option value="Rotativo">Rotativo (vaga que estiver livre)</option><option value="Premium">Premium (vaga exclusiva)</option></select></div>
                <div class="campo"><label for="pl-cat">Veículo do plano</label><select id="pl-cat"><option>Carro</option><option>Moto</option></select></div>
                <div class="campo" id="pl-campo-cotas"><label for="pl-cotas">Cotas (veículos ao mesmo tempo)</label><input id="pl-cotas" type="number" min="1" max="20" value="1"></div>
                <div class="campo" id="pl-campo-vaga" hidden><label for="pl-vaga">Vaga premium</label><select id="pl-vaga"></select></div>
                <div class="campo"><label for="pl-inicio">Data de adesão (início)</label><input id="pl-inicio" type="date" min="${hojeISO()}" value="${hojeISO()}"></div>
                <div class="campo"><label for="pl-sit">1ª mensalidade</label><select id="pl-sit"><option value="Pendente">Pendente (a receber)</option><option value="Pago">Paga agora</option></select></div>
                <div class="campo" id="pl-campo-forma" hidden><label for="pl-forma">Forma de pagamento</label><select id="pl-forma"><option value="">Selecione...</option>${opcoesFormaPagamento()}</select></div>
                <div class="campo" id="pl-campo-recebido" hidden><label for="pl-recebido">Valor recebido (R$)</label><input id="pl-recebido" type="number" step="0.01" min="0"></div>
                <div class="campo" id="pl-campo-troco" hidden><label>Troco</label><input id="pl-troco" class="somente-leitura" readonly value="—"></div>
                <div class="campo"><button class="btn" type="submit">Aderir ao plano</button></div>
            </form>
            <div class="caixa-info" id="pl-info"></div>
            <div class="acoes"><button class="btn sec" data-fechar type="button">Fechar</button></div>
        </div>`;
        const g = s => dlg.querySelector(s);
        const valor = () => { const p = preco(g("#pl-cat").value, g("#pl-tipo").value); return p ? p * (g("#pl-tipo").value === "Premium" ? 1 : (Number(g("#pl-cotas").value) || 1)) : null; };
        const atualizar = () => {
            const prem = g("#pl-tipo").value === "Premium", cat = g("#pl-cat").value;
            g("#pl-campo-cotas").hidden = prem; g("#pl-campo-vaga").hidden = !prem;
            if (prem) {
                const livres = premium.filter(v => v.categoria === cat && v.ativa && !v.reservada_para);
                const atual = g("#pl-vaga").value;
                g("#pl-vaga").innerHTML = `<option value="">${livres.length ? "Selecione a vaga..." : "Nenhuma vaga premium livre"}</option>` + livres.map(v => `<option value="${v.id}">${esc(v.codigo_vaga)}</option>`).join("");
                if (livres.some(v => String(v.id) === atual)) g("#pl-vaga").value = atual;
            }
            const pago = g("#pl-sit").value === "Pago", dinheiro = pago && g("#pl-forma").value === "Dinheiro";
            g("#pl-campo-forma").hidden = !pago; g("#pl-campo-recebido").hidden = !dinheiro; g("#pl-campo-troco").hidden = !dinheiro;
            const total = valor();
            g("#pl-troco").value = dinheiro && total !== null && g("#pl-recebido").value !== "" ? (Number(g("#pl-recebido").value) >= total ? moeda(Number(g("#pl-recebido").value) - total) : "valor insuficiente") : "—";
            const cap = capacidade.find(x => x.categoria === cat);
            g("#pl-info").innerHTML = `Valor da mensalidade: <strong>${total !== null ? moeda(total) : "preço não definido"}</strong> (a vigência começa na data de adesão).<br>` +
                (prem ? `Vagas premium (${cat.toLowerCase()}): <strong>${cap.vagas_premium}</strong> · reservadas: <strong>${cap.premium_atribuidas}</strong> · livres: <strong>${cap.premium_livres}</strong>.`
                      : `Vagas de mensalista (${cat.toLowerCase()}): <strong>${cap.vagas_mensalista}</strong> · cotas contratadas: <strong>${cap.cotas_contratadas}</strong> · livres: <strong>${cap.cotas_livres}</strong>.`);
        };
        ["#pl-tipo", "#pl-cat", "#pl-cotas", "#pl-sit", "#pl-forma", "#pl-recebido", "#pl-vaga"].forEach(s => g(s).addEventListener("input", atualizar));
        atualizar();
        g("[data-fechar]").addEventListener("click", () => dlg.close());
        ativarSequencia(g("#form-adesao"), [{ depende: null, campos: [
            { id: "pl-tipo" }, { id: "pl-cat" },
            { id: "pl-cotas", validar: v => (Number(v) >= 1 && Number(v) <= 20) ? null : "Informe de 1 a 20 cotas." },
            { id: "pl-vaga", validar: v => v ? null : "Escolha a vaga premium." },
            { id: "pl-inicio", validar: v => v >= hojeISO() ? null : "A data de adesão não pode ser anterior a hoje." },
            { id: "pl-sit" },
            { id: "pl-forma", validar: v => v ? null : "Selecione a forma de pagamento." },
            { id: "pl-recebido", validar: v => { const t = valor(); return t !== null && Number(v) < t ? `O valor recebido é menor que o total (${moeda(t)}).` : null; } },
        ] }]);
    }

    async function recarregarDialogo() {
        [dados, capacidade, premium] = await Promise.all([api(`/cadastro/cliente/${cliente.id}`), api("/mensalidades/capacidade"), api("/mensalidades/vagas-premium")]);
        desenharDialogo();
        paginador.recarregar();
    }

    dlg.addEventListener("click", async ev => {
        const cotasBtn = ev.target.closest("[data-cotas]"), cancelarBtn = ev.target.closest("[data-cancelar]");
        try {
            if (cotasBtn) {
                const nova = await perguntarNumero("Nova quantidade de cotas:", cotasBtn.dataset.atual, { titulo: "Alterar cotas", min: 1, max: 20 });
                if (!nova) return;
                await api(`/mensalidades/${cotasBtn.dataset.cotas}/cotas`, { metodo: "PUT", corpo: { cotas: nova } });
                aviso("Cotas atualizadas.");
                await recarregarDialogo();
            } else if (cancelarBtn && await confirmar("O cliente volta a ser horista; cobranças pendentes continuam em aberto.", { titulo: "Cancelar este plano?", sim: "Cancelar plano", nao: "Voltar", perigo: true })) {
                await api(`/mensalidades/${cancelarBtn.dataset.cancelar}/cancelar`, { metodo: "PUT" });
                aviso("Plano cancelado.");
                await recarregarDialogo();
            }
        } catch (e) { erroAviso(e); }
    });

    dlg.addEventListener("submit", async ev => {
        if (ev.target.id !== "form-adesao") return;
        ev.preventDefault();
        const g = s => dlg.querySelector(s);
        const prem = g("#pl-tipo").value === "Premium", pago = g("#pl-sit").value === "Pago", dinheiro = pago && g("#pl-forma").value === "Dinheiro";
        if (prem && !g("#pl-vaga").value) { aviso("Plano premium: escolha a vaga exclusiva do cliente.", "erro"); return; }
        if (g("#pl-inicio").value < hojeISO()) { aviso("A data de adesão não pode ser anterior a hoje.", "erro"); return; }
        if (pago && !g("#pl-forma").value) { aviso("Selecione a forma de pagamento da 1ª mensalidade.", "erro"); return; }
        if (dinheiro && !g("#pl-recebido").value) { aviso("Informe o valor recebido em dinheiro.", "erro"); return; }
        try {
            await api("/mensalidades/", { metodo: "POST", corpo: {
                id_cliente: cliente.id, tipo_plano: g("#pl-tipo").value, categoria: g("#pl-cat").value, cotas: prem ? 1 : Number(g("#pl-cotas").value),
                id_vaga: prem ? Number(g("#pl-vaga").value) : null, data_inicio: g("#pl-inicio").value || null,
                status_primeira_cobranca: g("#pl-sit").value, forma_pagamento: pago ? g("#pl-forma").value : null,
                valor_recebido: dinheiro ? Number(g("#pl-recebido").value) : null,
            } });
            aviso("Plano de mensalista criado.");
            await recarregarDialogo();
        } catch (e) { erroAviso(e); }
    });

    desenharDialogo();
    document.body.appendChild(dlg);
    dlg.addEventListener("close", () => dlg.remove());
    dlg.showModal();
}

tbody.addEventListener("click", async ev => {
    const botao = ev.target.closest("[data-acao]");
    if (!botao) return;
    const cliente = clientes.find(c => String(c.id) === botao.closest("tr").dataset.id);
    if (botao.dataset.acao === "editar") abrirEdicao(cliente.id);
    else if (botao.dataset.acao === "plano") abrirPlano(cliente);
    else if (botao.dataset.acao === "excluir") {
        if (!await confirmar(`Excluir o cliente ${cliente.nome}? Só é possível se ele não tiver veículos ou histórico.`, { titulo: "Excluir cliente", sim: "Excluir", perigo: true })) return;
        try { await api(`/clientes/${cliente.id}`, { metodo: "DELETE" }); aviso("Cliente excluído."); paginador.recarregar(); }
        catch (e) { erroAviso(e); }
    }
});

if (usuario) paginador.recarregar();
