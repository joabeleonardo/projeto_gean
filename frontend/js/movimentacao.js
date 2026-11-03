const usuario = iniciarPagina({ pagina: "movimentacao", titulo: "Entrada e saída" });
let entrada = null;

async function carregarPatio() {
    try {
        const itens = await api("/movimentacoes/patio");
        document.getElementById("contagem-patio").textContent = `${itens.length} veículo(s)`;
        document.getElementById("tbody-patio").innerHTML = itens.length ? itens.map(m => `<tr>
            <td>${placaHtml(m.placa)}</td><td>${esc(nomeVeiculo(m))}<div class="ajuda">${esc(m.categoria)}</div></td><td>${esc(m.cliente_nome || "—")}</td>
            <td>${esc(m.codigo_vaga)} <span class="selo ${m.tipo_vaga === "Mensalista" ? "mensalista" : ""}">${esc(m.tipo_vaga)}</span></td>
            <td>${dataHora(m.data_entrada)}</td><td>${duracao(m.permanencia_minutos)}</td>
            <td><button class="btn pequeno" data-saida="${m.id}">Registrar saída</button></td></tr>`).join("")
            : `<tr><td colspan="7" class="vazio">Nenhum veículo no pátio.</td></tr>`;
    } catch (e) { erroAviso(e); }
}

async function atualizar() {
    await carregarPatio();
    if (entrada) entrada.recarregar();
}

document.getElementById("tbody-patio").addEventListener("click", ev => {
    const botao = ev.target.closest("[data-saida]");
    if (botao) abrirSaida(botao.dataset.saida, atualizar);
});

if (usuario) {
    entrada = criarEntradaRapida(document.getElementById("entrada-mov"), carregarPatio);
    carregarPatio();
    setInterval(() => carregarPatio(), 60000);
    // veiculos.html?... -> "Registrar entrada" já chega com o veículo escolhido
    const idUrl = new URLSearchParams(location.search).get("veiculo");
    if (idUrl) api(`/veiculos/${idUrl}`).then(v => entrada.escolherVeiculo(v.id, `${v.placa} · ${nomeVeiculo(v)}`, v)).catch(() => { });
}
