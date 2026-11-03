/* ==========================================================================
   Entrada e saída reutilizáveis: usadas no painel (registro rápido) e na
   tela "Entrada e saída". Identifica sozinho se o veículo entra como
   mensalista ou horista e trata: cliente inadimplente (código do
   administrador) e mensalista sem cota livre (entrar como horista?).
   ========================================================================== */

const ordemNatural = (a, b) => a.localeCompare(b, "pt-BR", { numeric: true });

/* ------------------------------------------------------------- entrada */
function criarEntradaRapida(raiz, aoConcluir = () => { }) {
    raiz.innerHTML = `
        <form class="form-grid coluna-unica" novalidate>
            <div class="campo"><label>Veículo (placa, marca, modelo ou dono)</label>
                <input class="in-veiculo" id="in-veiculo-${raiz.id}" placeholder="Ex.: ABC-1234" required></div>
            <div class="modo-entrada" hidden></div>
            <div class="campo"><label>Vaga livre</label><select class="in-vaga" required></select></div>
            <div class="campo"><button class="btn" type="submit">Registrar entrada</button></div>
        </form>
        <div class="cotas-aviso" hidden role="alert">
            <strong>COTAS DE MENSALISTA EM USO</strong>
            <p class="cotas-texto"></p>
            <div class="acoes"><button type="button" class="btn cotas-horista">Dar entrada como horista</button>
                <button type="button" class="btn sec cotas-cancelar">Cancelar</button></div>
        </div>
        <div class="bloqueio" hidden role="alert">
            <strong class="bloqueio-titulo">ENTRADA BLOQUEADA</strong>
            <p class="bloqueio-texto"></p>
            <div class="campo"><label>Código do administrador para liberar</label>
                <input class="in-codigo" type="password" inputmode="numeric" autocomplete="off" placeholder="Código de liberação"></div>
            <p class="bloqueio-erro" hidden></p>
            <div class="acoes"><button type="button" class="btn bloqueio-liberar">Liberar entrada</button>
                <button type="button" class="btn sec bloqueio-cancelar">Cancelar</button></div>
        </div>`;

    const form = raiz.querySelector("form");
    const inVeiculo = raiz.querySelector(".in-veiculo");
    const selVaga = raiz.querySelector(".in-vaga");
    const caixaModo = raiz.querySelector(".modo-entrada");
    const avisoCotas = raiz.querySelector(".cotas-aviso");
    const caixa = raiz.querySelector(".bloqueio");
    const inCodigo = raiz.querySelector(".in-codigo");
    const msgErro = raiz.querySelector(".bloqueio-erro");
    let vagas = [];
    let veiculoEscolhido = null;
    let modo = null;              // resposta de /movimentacoes/modo-entrada/{id}
    let comoHorista = false;      // mensalista sem cota livre que aceitou entrar como horista

    /* tipo de vaga que este veículo deve usar */
    function tipoDeVaga() {
        if (!modo) return null;
        if (modo.tem_plano && !modo.esgotado) return modo.modo === "Premium" ? "Premium" : "Mensalista";
        return modo.tem_plano && comoHorista ? "Horista" : (modo.tem_plano ? null : "Horista");
    }

    function preencherVagas() {
        const categoria = veiculoEscolhido ? veiculoEscolhido.dados.tipo_veiculo : null;
        const tipo = tipoDeVaga();
        const livres = vagas.filter(v => v.ativa !== false && v.status === "Livre" && (!categoria || v.categoria === categoria) && (!tipo || v.tipo === tipo)
                && (tipo !== "Premium" || !modo.vaga_premium || v.id === modo.vaga_premium.id))
            .sort((a, b) => ordemNatural(a.codigo_vaga, b.codigo_vaga));
        const anterior = selVaga.value;
        const alvo = [categoria ? categoria.toLowerCase() : "", tipo ? tipo.toLowerCase() : ""].filter(Boolean).join(" ");
        selVaga.innerHTML = livres.length
            ? livres.map(v => `<option value="${v.id}">${esc(v.codigo_vaga)} — ${esc(v.tipo)} · ${esc(v.categoria)}</option>`).join("")
            : `<option value="">${alvo ? `Nenhuma vaga livre (${alvo})` : "Nenhuma vaga livre"}</option>`;
        if (anterior && livres.some(v => String(v.id) === anterior)) selVaga.value = anterior;
    }

    function mostrarModo() {
        if (!modo) { caixaModo.hidden = true; return; }
        caixaModo.hidden = false;
        caixaModo.classList.toggle("horista", !(modo.tem_plano && !modo.esgotado));
        caixaModo.innerHTML = modo.tem_plano && !modo.esgotado
            ? (modo.modo === "Premium"
                ? `<strong>Premium</strong> — ${esc(modo.mensagem)} A vaga é exclusiva deste cliente.`
                : `<strong>Mensalista</strong> — ${esc(modo.mensagem.replace("Mensalista: ", ""))} Usará vaga de mensalista.`)
            : modo.tem_plano && comoHorista ? `<strong>Entrada como horista</strong> — será cobrado por hora.`
            : `<strong>Horista</strong> — ${esc(modo.mensagem)}`;
    }

    async function aoEscolherVeiculo(item) {
        veiculoEscolhido = item;
        modo = null; comoHorista = false;
        avisoCotas.hidden = true;
        caixaModo.hidden = true;
        if (item) {
            try { modo = await api(`/movimentacoes/modo-entrada/${item.id}`); } catch (e) { erroAviso(e); }
            if (modo && modo.tem_plano && modo.esgotado) mostrarCotas(modo);
        }
        mostrarModo();
        preencherVagas();
    }

    const seletor = seletorComBusca(inVeiculo, async termo => {
        const lista = await api("/veiculos/busca", { params: { q: termo } });
        return lista.map(v => ({ id: v.id, rotulo: `${v.placa} · ${nomeVeiculo(v)} (${v.cliente_nome})`, dados: v }));
    }, aoEscolherVeiculo);

    async function carregarVagas() {
        try { vagas = await api("/vagas/"); preencherVagas(); } catch (e) { erroAviso(e); }
    }

    /* ---- mensalista sem cota livre: alerta e pergunta se entra como horista */
    function mostrarCotas(d) {
        const placas = (d.placas_em_uso || []).join(", ") || "outro veículo";
        raiz.querySelector(".cotas-texto").innerHTML =
            `${esc(d.cliente_nome || "O cliente")} é mensalista, mas todas as cotas/vagas (${d.cotas}) estão em uso: <strong>${esc(placas)}</strong> já está no pátio.<br>Deseja dar entrada <strong>como horista</strong> (cobrança por hora)?`;
        avisoCotas.hidden = false;
    }

    raiz.querySelector(".cotas-horista").addEventListener("click", () => {
        comoHorista = true;
        avisoCotas.hidden = true;
        mostrarModo();
        preencherVagas();
    });
    raiz.querySelector(".cotas-cancelar").addEventListener("click", () => { avisoCotas.hidden = true; seletor.limpar(); });

    /* ---- cliente inadimplente: bloqueio com código do administrador */
    function esconderBloqueio() { caixa.hidden = true; inCodigo.value = ""; msgErro.hidden = true; }

    function mostrarBloqueio(d) {
        raiz.querySelector(".bloqueio-texto").innerHTML =
            `${esc(d.mensagem)}<br>${esc(d.cliente)} · ${moeda(d.valor_em_aberto)} em aberto (${d.cobrancas_vencidas} cobrança(s) vencida(s)).`;
        msgErro.hidden = true;
        inCodigo.value = "";
        caixa.hidden = false;
        inCodigo.focus();
    }

    async function enviar(codigoLiberacao = null) {
        const idVeiculo = seletor.valor();
        if (!idVeiculo) { aviso("Escolha o veículo na lista de sugestões.", "erro"); return; }
        if (!avisoCotas.hidden) { aviso("Confirme a entrada como horista ou cancele.", "erro"); return; }
        const idVaga = Number(selVaga.value);
        if (!idVaga) { aviso("Escolha uma vaga livre.", "erro"); return; }
        const corpo = { id_veiculo: idVeiculo, id_vaga: idVaga };
        if (comoHorista) corpo.como_horista = true;
        if (codigoLiberacao) corpo.codigo_liberacao = codigoLiberacao;
        try {
            await api("/movimentacoes/entrada", { metodo: "POST", corpo });
            const placa = veiculoEscolhido ? veiculoEscolhido.dados.placa : "";
            aviso(`Entrada registrada: ${placa} na vaga ${selVaga.selectedOptions[0].text.split(" — ")[0]}.`);
            esconderBloqueio();
            seletor.limpar();
            await carregarVagas();
            aoConcluir();
        } catch (e) {
            const d = e.detalhe;
            if (e.status === 423 && d && d.codigo === "CLIENTE_INADIMPLENTE") mostrarBloqueio(d);
            else if (e.status === 409 && d && d.codigo === "COTAS_ESGOTADAS") mostrarCotas({ ...d, cliente_nome: d.cliente });
            else if (codigoLiberacao) { msgErro.textContent = e.message; msgErro.hidden = false; inCodigo.select(); }
            else erroAviso(e);
        }
    }

    form.addEventListener("submit", ev => { ev.preventDefault(); esconderBloqueio(); enviar(); });
    raiz.querySelector(".bloqueio-liberar").addEventListener("click", () => {
        const codigo = inCodigo.value.trim();
        if (!codigo) { msgErro.textContent = "Digite o código do administrador."; msgErro.hidden = false; return; }
        enviar(codigo);
    });
    inCodigo.addEventListener("keydown", ev => { if (ev.key === "Enter") { ev.preventDefault(); raiz.querySelector(".bloqueio-liberar").click(); } });
    raiz.querySelector(".bloqueio-cancelar").addEventListener("click", esconderBloqueio);

    carregarVagas();
    return {
        recarregar: carregarVagas,
        escolherVeiculo(id, rotulo, dados) { seletor.definir(id, rotulo, { id, rotulo, dados }); },
    };
}

/* --------------------------------------------------------------- saída */
async function abrirSaida(idMovimentacao, aoConcluir = () => { }) {
    let p;
    try { p = await api(`/movimentacoes/${idMovimentacao}/previa-saida`); } catch (e) { erroAviso(e); return; }

    const dlg = document.createElement("dialog");
    const cobra = p.valor_total !== null && p.valor_total > 0;
    dlg.innerHTML = `<div class="dialogo-corpo">
        <h2>Confirmar saída</h2>
        <div class="resumo-saida">
            <div><span>Placa</span><strong>${esc(p.placa)}</strong></div>
            <div><span>Vaga</span><strong>${esc(p.codigo_vaga)} (${esc(p.tipo_vaga)} · ${esc(p.categoria)})</strong></div>
            <div><span>Entrada</span><strong>${dataHora(p.data_entrada)}</strong></div>
            <div><span>Permanência</span><strong>${duracao(p.permanencia_minutos)}</strong></div>
            ${p.valor_total === null
            ? `<div class="total"><span>Mensalista</span><span>sem cobrança por hora</span></div>`
            : `<div><span>Valor da hora</span><strong>${moeda(p.valor_hora)}</strong></div>
                   ${p.valor_minimo > 0 ? `<div><span>Mínimo</span><strong>${moeda(p.valor_minimo)} até ${p.tempo_minimo_minutos} min</strong></div>` : ""}
                   <div class="total"><span>Total</span><strong>${moeda(p.valor_total)}</strong></div>`}
        </div>
        ${p.valor_total !== null ? `<p class="ajuda">Cobrança proporcional ao tempo (por minuto completo), respeitando o valor mínimo.</p>` : ""}
        ${cobra ? `<div class="campo" style="margin-top:12px"><label>Forma de pagamento</label>
            <select class="sel-forma"><option value="">Selecione...</option>${opcoesFormaPagamento()}</select></div>
            <div class="campo dinheiro" style="margin-top:10px" hidden><label>Valor recebido em dinheiro (R$)</label><input class="in-recebido" type="number" step="0.01" min="0"></div>
            <div class="resumo-saida dinheiro" hidden><div class="total"><span>Troco</span><strong class="txt-troco">—</strong></div></div>` : ""}
        <div class="acoes"><button class="btn btn-ok" type="button">Confirmar saída</button><button class="btn sec btn-nao" type="button">Cancelar</button></div>
    </div>`;
    document.body.appendChild(dlg);
    dlg.addEventListener("close", () => dlg.remove());
    dlg.querySelector(".btn-nao").addEventListener("click", () => dlg.close());
    if (cobra) ligarDinheiro(dlg, p.valor_total);
    dlg.querySelector(".btn-ok").addEventListener("click", async () => {
        const forma = cobra ? dlg.querySelector(".sel-forma").value : null;
        if (cobra && !forma) { aviso("Selecione a forma de pagamento.", "erro"); return; }
        const dinheiro = forma === "Dinheiro";
        const recebido = dinheiro ? Number(dlg.querySelector(".in-recebido").value) : null;
        if (dinheiro && !(recebido >= p.valor_total)) { aviso(`Informe o valor recebido em dinheiro (no mínimo ${moeda(p.valor_total)}).`, "erro"); return; }
        try {
            const corpo = forma ? { forma_pagamento: forma, ...(dinheiro ? { valor_recebido: recebido } : {}) } : {};
            const r = await api(`/movimentacoes/${idMovimentacao}/saida`, { metodo: "PUT", corpo });
            dlg.close();
            aviso(r.valor_total ? `Saída registrada. Recebido ${moeda(r.valor_total)} (${forma})${r.troco ? ` · troco ${moeda(r.troco)}` : ""}.` : "Saída registrada.");
            aoConcluir();
        } catch (e) { dlg.close(); erroAviso(e); aoConcluir(); }
    });
    dlg.showModal();
}

/* Saída rápida: escolhe o veículo que está no pátio e abre a confirmação. */
function criarSaidaRapida(raiz, aoConcluir = () => { }) {
    raiz.innerHTML = `
        <form class="form-grid coluna-unica" novalidate>
            <div class="campo"><label>Veículo no pátio (digite a placa)</label>
                <input class="in-saida" id="in-saida-${raiz.id}" placeholder="Ex.: ABC-1234" required></div>
            <div class="campo"><button class="btn" type="submit">Registrar saída</button></div>
        </form>`;
    const seletor = seletorComBusca(raiz.querySelector(".in-saida"), async termo => {
        const t = termo.toUpperCase().replace(/[^A-Z0-9]/g, "");
        const patio = await api("/movimentacoes/patio");
        return patio
            .filter(m => !t || m.placa.replace("-", "").includes(t) || (m.cliente_nome || "").toUpperCase().includes(termo.toUpperCase()))
            .map(m => ({ id: m.id, rotulo: `${m.placa} · ${nomeVeiculo(m)} · vaga ${m.codigo_vaga}` }));
    });
    raiz.querySelector("form").addEventListener("submit", ev => {
        ev.preventDefault();
        const id = seletor.valor();
        if (!id) { aviso("Escolha o veículo na lista de sugestões.", "erro"); return; }
        abrirSaida(id, () => { seletor.limpar(); aoConcluir(); });
    });
}


/* Pagamento em dinheiro: mostra o campo "valor recebido" e calcula o troco na hora. */
function ligarDinheiro(dlg, total) {
    const forma = dlg.querySelector(".sel-forma"), recebido = dlg.querySelector(".in-recebido"), troco = dlg.querySelector(".txt-troco");
    const atualizar = () => {
        const dinheiro = forma.value === "Dinheiro";
        dlg.querySelectorAll(".dinheiro").forEach(el => { el.hidden = !dinheiro; });
        const v = Number(recebido.value);
        troco.textContent = recebido.value === "" ? "—" : (v >= total ? moeda(v - total) : "valor insuficiente");
    };
    forma.addEventListener("change", () => { atualizar(); if (forma.value === "Dinheiro") recebido.focus(); });
    recebido.addEventListener("input", atualizar);
}

/* Dar baixa em uma cobrança pendente (usada em Pagamentos e em Inadimplência). */
function abrirBaixa(id, valor, aoConcluir = () => { }) {
    const total = Number(valor);
    const dlg = document.createElement("dialog");
    dlg.innerHTML = `<div class="dialogo-corpo"><h2>Dar baixa no pagamento</h2>
        <p class="ajuda">Valor a receber: <strong>${moeda(total)}</strong></p>
        <div class="campo" style="margin-top:12px"><label>Forma de pagamento</label>
            <select class="sel-forma"><option value="">Selecione...</option>${opcoesFormaPagamento()}</select></div>
        <div class="campo dinheiro" style="margin-top:10px" hidden><label>Valor recebido em dinheiro (R$)</label><input class="in-recebido" type="number" step="0.01" min="0"></div>
        <div class="resumo-saida dinheiro" hidden><div class="total"><span>Troco</span><strong class="txt-troco">—</strong></div></div>
        <div class="acoes"><button class="btn btn-ok" type="button">Confirmar recebimento</button><button class="btn sec btn-nao" type="button">Cancelar</button></div></div>`;
    document.body.appendChild(dlg);
    dlg.addEventListener("close", () => dlg.remove());
    dlg.querySelector(".btn-nao").addEventListener("click", () => dlg.close());
    ligarDinheiro(dlg, total);
    dlg.querySelector(".btn-ok").addEventListener("click", async () => {
        const forma = dlg.querySelector(".sel-forma").value;
        if (!forma) { aviso("Selecione a forma de pagamento.", "erro"); return; }
        const dinheiro = forma === "Dinheiro", recebido = Number(dlg.querySelector(".in-recebido").value);
        if (dinheiro && !(recebido >= total)) { aviso(`Informe o valor recebido em dinheiro (no mínimo ${moeda(total)}).`, "erro"); return; }
        try {
            await api(`/pagamentos/${id}/baixa`, { metodo: "PUT", corpo: { forma_pagamento: forma, ...(dinheiro ? { valor_recebido: recebido } : {}) } });
            dlg.close();
            aviso(dinheiro && recebido > total ? `Pagamento recebido. Troco: ${moeda(recebido - total)}.` : "Pagamento recebido.");
            aoConcluir();
        } catch (e) { erroAviso(e); }
    });
    dlg.showModal();
}
