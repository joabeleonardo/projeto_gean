const usuario = iniciarPagina({ pagina: "painel", titulo: "Painel" });
const $ = id => document.getElementById(id);

let entradaRapida = null;

function numero(rotulo, valor, classe = "", extra = "") {
    return `<div class="numero ${classe}"><div class="valor">${valor}</div><div class="rotulo">${rotulo}</div>${extra}</div>`;
}

function desenharNumeros(r) {
    const v = r.vagas, inad = r.inadimplentes;
    const horista = v.por_tipo.Horista || { total: 0, ocupadas: 0 };
    const mensalista = v.por_tipo.Mensalista || { total: 0, ocupadas: 0 };
    const cotas = (v.mensalistas || []).reduce((s, m) => s + m.cotas_contratadas, 0);
    const vagasMensal = (v.mensalistas || []).reduce((s, m) => s + m.vagas_mensalista, 0);
    $("numeros").innerHTML =
        numero("vagas no total", v.total) +
        numero("vagas livres", v.livres, "livre") +
        numero("vagas ocupadas", v.ocupadas, "ocupada") +
        numero("vagas de horista ocupadas", `${horista.ocupadas}<small> / ${horista.total}</small>`, "horista") +
        numero("vagas de mensalista ocupadas", `${mensalista.ocupadas}<small> / ${mensalista.total}</small>`, "mensalista") +
        numero("cotas de mensalista contratadas", `${cotas}<small> / ${vagasMensal}</small>`, "mensalista", `<div class="rotulo">${Math.max(0, vagasMensal - cotas)} livre(s) para novos planos</div>`) +
        (v.inativas ? numero("vagas inativas", v.inativas, "", `<div class="rotulo">fora da contagem</div>`) : "") +
        `<a class="numero-link" href="inadimplencia.html" ${dica("Ver os clientes inadimplentes")}>${numero("clientes inadimplentes", inad.quantidade, inad.quantidade ? "alerta" : "", `<div class="rotulo">${moeda(inad.valor_em_aberto)} em aberto</div>`)}</a>` +
        numero("entradas hoje", r.hoje.entradas, "", `<div class="rotulo">${r.hoje.saidas} saída(s)</div>`) +
        (r.receita ? numero("recebido hoje", moeda(r.receita.hoje), "", `<div class="rotulo">${moeda(r.receita.mes)} no mês</div>`) : "");
}

function desenharBaias(mapa) {
    const alvo = $("baias");
    if (!mapa.length) {
        alvo.innerHTML = `<div class="vazio" style="grid-column:1/-1;color:#c3ccd6">Nenhuma vaga cadastrada. ${ehAdmin() ? `Cadastre em <a href="vagas.html" style="color:var(--faixa)">Vagas</a>.` : "Peça a um administrador para cadastrar as vagas."}</div>`;
        return;
    }
    alvo.innerHTML = mapa.map(v => {
        if (!v.ativa) return `<div class="baia inativa" title="Vaga inativa (indisponível)"><span class="cod">${esc(v.codigo)}</span><span class="livre-txt">inativa</span></div>`;
        const tags = `<span class="tags">${v.tipo === "Premium" ? `<span class="tipo premium" title="Vaga premium (exclusiva)">P</span>` : ""}${v.tipo === "Mensalista" ? `<span class="tipo" title="Vaga de mensalista">M</span>` : ""}${v.categoria === "Moto" ? `<span class="tipo moto" title="Vaga de moto">MOTO</span>` : ""}</span>`;
        if (v.status === "Ocupada") {
            const veic = [v.marca, v.modelo].filter(Boolean).join(" ");
            return `<button type="button" class="baia ocupada" data-mov="${v.id_movimentacao}" title="Entrou ${esc(dataHora(v.data_entrada))} — clique para registrar a saída">
                <span class="cod">${esc(v.codigo)}${tags}</span>${placaHtml(v.placa || "—")}
                <span class="marca-veiculo">${esc(veic)}</span><span class="tempo">${duracao(v.permanencia_minutos)}</span></button>`;
        }
        return `<div class="baia livre ${v.tipo === "Premium" ? "premium" : ""}"><span class="cod">${esc(v.codigo)}${tags}</span><span class="livre-txt">livre</span>${v.reservada_para ? `<span class="reservada" title="Reservada para ${esc(v.reservada_para)}">${esc(v.reservada_para)}</span>` : ""}</div>`;
    }).join("");
}

function desenharMatriz(v) {
    const linhas = v.matriz.map(m => {
        const pct = m.total ? Math.round(100 * m.ocupadas / m.total) : 0;
        return `<tr><td>${esc(m.categoria)}</td><td><span class="selo ${m.tipo === "Mensalista" ? "mensalista" : m.tipo === "Premium" ? "premium" : ""}">${esc(m.tipo)}</span></td>
            <td class="num">${m.total}</td><td class="num">${m.ocupadas}</td><td class="num"><strong>${m.livres}</strong></td>
            <td><div class="barra" title="${pct}% ocupada"><i style="width:${pct}%"></i></div></td></tr>`;
    });
    $("tbody-matriz").innerHTML = linhas.length
        ? linhas.join("") + `<tr><td colspan="2"><strong>Total</strong></td><td class="num"><strong>${v.total}</strong></td><td class="num"><strong>${v.ocupadas}</strong></td><td class="num"><strong>${v.livres}</strong></td><td></td></tr>`
        : `<tr><td colspan="6" class="vazio">Nenhuma vaga cadastrada.</td></tr>`;
}

function desenharFeed(itens) {
    const hoje = hojeISO();
    $("feed").innerHTML = itens.length ? itens.map(e => {
        const d = new Date(e.quando);
        const hora = d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
        const dia = e.quando.slice(0, 10) === hoje ? "" : `<span class="quando-dia">${d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })}</span>`;
        return `<li><span class="hora">${hora}${dia}</span>
            <span><span class="selo ${e.tipo === "Entrada" ? "livre" : ""}">${e.tipo}</span></span>
            <span>${placaHtml(e.placa)} <span class="ajuda">${esc(e.veiculo)}</span></span><span class="ajuda">vaga ${esc(e.vaga)}</span></li>`;
    }).join("") : `<li class="vazio" style="display:block">Nenhuma entrada ou saída nos últimos 7 dias.</li>`;
}

function desenharPrecos(precos) {
    const valor = (cat, tipo) => {
        const p = precos.find(x => x.categoria === cat && x.tipo_cobranca === tipo);
        if (!p) return `<span class="indefinido">não definido</span>`;
        const minimo = tipo === "Horista" && p.valor_minimo > 0 ? `<div class="indefinido">mín. ${moeda(p.valor_minimo)} até ${p.tempo_minimo_minutos} min</div>` : "";
        return moeda(p.valor) + minimo;
    };
    $("tbody-precos").innerHTML = ["Carro", "Moto"].map(c =>
        `<tr><td>${c}</td><td>${valor(c, "Horista")}</td><td>${valor(c, "Mensalista")}</td></tr>`).join("");
}

function desenharInadimplentes(inad) {
    $("inadimplentes").innerHTML = inad.quantidade === 0
        ? `<p class="ajuda">Nenhum cliente inadimplente.</p>`
        : `<div class="alerta-numero">${inad.quantidade} <span class="ajuda" style="font-size:.95rem">cliente(s) · ${moeda(inad.valor_em_aberto)} em aberto</span></div>
           <ul class="lista-inad">${inad.itens.map(i => `<li><span>${esc(i.nome)}<div class="ajuda">${esc(i.telefone || i.cpf)} · ${moeda(i.valor_em_aberto)}</div></span><span class="dias">${i.dias_atraso} dia(s)</span></li>`).join("")}</ul>
           ${inad.quantidade > inad.itens.length ? `<p class="ajuda" style="margin-top:6px">e mais ${inad.quantidade - inad.itens.length}…</p>` : ""}`;
}

/* Gráfico de barras simples em SVG (sem bibliotecas externas, funciona offline). */
function graficoBarras(alvo, dias, series, formatar, vazio) {
    if (!dias.some(d => series.some(s => (s.valor(d) || 0) > 0))) { alvo.innerHTML = `<p class="vazio">${vazio}</p>`; return; }
    const L = 560, A = 210, mEsq = 8, mBase = 28, mTopo = 22;
    const maximo = Math.max(1, ...series.flatMap(s => dias.map(d => s.valor(d) || 0)));
    const largGrupo = (L - mEsq) / dias.length;
    const largBarra = Math.min(28, (largGrupo - 14) / series.length);
    let svg = `<svg viewBox="0 0 ${L} ${A}" role="img" aria-label="Gráfico dos últimos 7 dias">`;
    svg += `<line x1="${mEsq}" y1="${A - mBase}" x2="${L}" y2="${A - mBase}" stroke="#d3d9df"/>`;
    dias.forEach((d, i) => {
        const x0 = mEsq + i * largGrupo + (largGrupo - largBarra * series.length) / 2;
        series.forEach((s, j) => {
            const v = s.valor(d) || 0;
            const h = (A - mBase - mTopo) * (v / maximo);
            const x = x0 + j * largBarra, y = A - mBase - h;
            svg += `<rect x="${x}" y="${y}" width="${largBarra - 2}" height="${Math.max(h, 0)}" fill="${s.cor}" rx="2"><title>${s.nome}: ${formatar(v)}</title></rect>`;
            if (v > 0) svg += `<text class="valor-barra" x="${x + (largBarra - 2) / 2}" y="${y - 4}" text-anchor="middle">${formatar(v)}</text>`;
        });
        const [, mes, dia] = d.data.split("-");
        svg += `<text x="${mEsq + i * largGrupo + largGrupo / 2}" y="${A - 8}" text-anchor="middle">${dia}/${mes}</text>`;
    });
    alvo.innerHTML = svg + "</svg>";
}

async function carregar() {
    try {
        const r = await api("/dashboard/resumo");
        desenharNumeros(r);
        desenharBaias(r.mapa_vagas);
        desenharMatriz(r.vagas);
        desenharFeed(r.ultimas_movimentacoes);
        desenharPrecos(r.precos);
        desenharInadimplentes(r.inadimplentes);
        graficoBarras($("grafico-fluxo"), r.ultimos_7_dias,
            [{ nome: "Entradas", cor: "#3b4552", valor: d => d.entradas }, { nome: "Saídas", cor: "#f2b705", valor: d => d.saidas }],
            v => v, "Sem entradas ou saídas nos últimos 7 dias.");
        if (r.receita) {
            $("painel-receita").hidden = false;
            graficoBarras($("grafico-receita"), r.ultimos_7_dias,
                [{ nome: "Receita", cor: "#16916a", valor: d => d.receita }], v => Math.round(v), "Nenhum recebimento nos últimos 7 dias.");
            $("texto-pendencias").textContent = r.receita.pendentes_qtd
                ? `${r.receita.pendentes_qtd} cobrança(s) pendente(s) somando ${moeda(r.receita.pendentes_valor)}.`
                : "Nenhuma cobrança pendente.";
        }
        if (entradaRapida) entradaRapida.recarregar();
    } catch (e) { erroAviso(e); }
}

/* clicar numa vaga ocupada abre a confirmação de saída */
$("baias").addEventListener("click", ev => {
    const b = ev.target.closest("[data-mov]");
    if (b) abrirSaida(b.dataset.mov, carregar);
});

/* abas do registro rápido */
document.querySelectorAll(".aba").forEach(aba => aba.addEventListener("click", () => {
    document.querySelectorAll(".aba").forEach(a => a.setAttribute("aria-selected", String(a === aba)));
    $("aba-entrada").hidden = aba.dataset.aba !== "entrada";
    $("aba-saida").hidden = aba.dataset.aba !== "saida";
}));

if (usuario) {
    entradaRapida = criarEntradaRapida($("aba-entrada"), carregar);
    criarSaidaRapida($("aba-saida"), carregar);
    carregar();
    setInterval(carregar, 30000);
}
