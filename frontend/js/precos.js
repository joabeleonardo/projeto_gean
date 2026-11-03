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
