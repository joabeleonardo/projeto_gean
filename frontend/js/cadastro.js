const usuario = iniciarPagina({ pagina: "cadastro", titulo: "Novo cadastro" });
const $ = id => document.getElementById(id);

ligarBuscaCep({ cep: "e-cep", logradouro: "e-logradouro", bairro: "e-bairro", cidade: "e-cidade", estado: "e-estado", numero: "e-numero" });

let clienteAtual = null;   // cliente recém-cadastrado (ou escolhido pela URL)
let veiculosDoCliente = [];
let precos = [], capacidade = [], vagasPremium = [];

/* ---------------------------------------------------------------- plano */
const precoPlano = (tipo, cat) => (precos.find(p => p.categoria === cat && p.tipo_cobranca === (tipo === "Premium" ? "Premium" : "Mensalista")) || {}).valor;
function valorDoPlano() {
    const p = precoPlano($("m-tipo").value, $("m-categoria").value);
    const cotas = $("m-tipo").value === "Premium" ? 1 : (Number($("m-cotas").value) || 1);
    return p ? p * cotas : null;
}

function atualizarPlano() {
    const premium = $("m-tipo").value === "Premium";
    const cat = $("m-categoria").value;
    $("m-campo-cotas").hidden = premium;
    $("m-campo-vaga").hidden = !premium;
    if (premium) {
        const livres = vagasPremium.filter(v => v.categoria === cat && v.ativa && !v.reservada_para);
        const atual = $("m-vaga").value;
        $("m-vaga").innerHTML = `<option value="">${livres.length ? "Selecione a vaga..." : "Nenhuma vaga premium livre"}</option>` +
            livres.map(v => `<option value="${v.id}">${esc(v.codigo_vaga)}</option>`).join("");
        if (livres.some(v => String(v.id) === atual)) $("m-vaga").value = atual;
    }
    const pago = $("m-situacao").value === "Pago";
    const dinheiro = pago && $("m-forma").value === "Dinheiro";
    $("m-campo-forma").hidden = !pago;
    $("m-campo-recebido").hidden = !dinheiro;
    $("m-campo-troco").hidden = !dinheiro;
    const valor = valorDoPlano();
    if (dinheiro && valor !== null && $("m-recebido").value !== "") {
        const t = Number($("m-recebido").value) - valor;
        $("m-troco").value = t >= 0 ? moeda(t) : "valor insuficiente";
    } else $("m-troco").value = "—";
    const cap = capacidade.find(c => c.categoria === cat);
    $("m-info").innerHTML =
        `Valor da mensalidade: <strong>${valor !== null ? moeda(valor) : "preço não definido (peça ao administrador)"}</strong>. A vigência começa na data de adesão.` +
        (cap ? (premium
            ? `<br>Vagas premium (${cat.toLowerCase()}): <strong>${cap.vagas_premium}</strong> · reservadas: <strong>${cap.premium_atribuidas}</strong> · livres: <strong>${cap.premium_livres}</strong>.`
            : `<br>Vagas de mensalista (${cat.toLowerCase()}): <strong>${cap.vagas_mensalista}</strong> · cotas contratadas: <strong>${cap.cotas_contratadas}</strong> · livres: <strong>${cap.cotas_livres}</strong>.`) : "");
}

/* ------------------------------------------- sequência dos campos do formulário */
const tipoDoc = () => $("c-tipo-doc").value;
const docCompleto = v => { const t = tipoDoc(), d = digitos(v); return t === "CNPJ" ? d.length >= 14 : t === "Passaporte" ? v.length >= 5 : d.length >= 11; };
const telCompleto = v => v.startsWith("+") ? digitos(v).length >= 8 : digitos(v).length >= 10;

const grupos = [
    { depende: null, campos: [
        { id: "c-nome", validar: v => VALIDAR.nome(v, tipoDoc()), julgar: v => v.length >= 3 },
        { id: "c-tipo-doc" },
        { id: "c-doc", validar: v => VALIDAR.documento(tipoDoc(), v), julgar: docCompleto },
        { id: "c-pais", validar: VALIDAR.texto("o país") },
        { id: "c-tel", opcional: true, validar: VALIDAR.telefone, julgar: telCompleto },
        { id: "c-wa", opcional: true },
        { id: "c-tel2", opcional: true, validar: VALIDAR.telefone, julgar: telCompleto },
        { id: "c-wa2", opcional: true },
    ] },
    { depende: 0, campos: [
        { id: "e-cep", validar: VALIDAR.cep, julgar: v => digitos(v).length >= 8 },
        { id: "e-logradouro", validar: VALIDAR.texto("a rua"), julgar: v => v.length >= 2 },
        { id: "e-numero", validar: VALIDAR.texto("o número", 1) },
        { id: "e-complemento", opcional: true },
        { id: "e-bairro", validar: VALIDAR.texto("o bairro") },
        { id: "e-cidade", validar: VALIDAR.texto("a cidade") },
        { id: "e-estado", validar: VALIDAR.uf, julgar: v => v.length >= 2 },
    ] },
    { depende: 0, campos: [
        { id: "v-tipo" },
        { id: "v-placa", validar: VALIDAR.placa, julgar: v => v.replace("-", "").length >= 7 },
        { id: "v-marca", validar: VALIDAR.texto("a marca") },
        { id: "v-modelo", validar: VALIDAR.texto("o modelo") },
        { id: "v-cor", opcional: true },
    ] },
    { depende: 0, campos: [
        { id: "m-aderir", opcional: true },
    ] },
    { depende: 3, campos: [
        { id: "m-tipo" }, { id: "m-categoria" },
        { id: "m-cotas", validar: v => (Number(v) >= 1 && Number(v) <= 20) ? null : "Informe de 1 a 20 cotas." },
        { id: "m-vaga", validar: v => v ? null : "Escolha a vaga premium." },
        { id: "m-inicio", validar: v => v >= hojeISO() ? null : "A data de adesão não pode ser anterior a hoje." },
        { id: "m-situacao" },
        { id: "m-forma", validar: v => v ? null : "Selecione a forma de pagamento." },
        { id: "m-recebido", validar: v => { const t = valorDoPlano(); return t !== null && Number(v) < t ? `O valor recebido é menor que o total (${moeda(t)}).` : null; } },
    ] },
];

function aoMudarFormulario(completo) {
    // WhatsApp e telefone 2 só fazem sentido com o telefone principal preenchido
    const tem = digitos($("c-tel").value).length > 0;
    if (!tem) { $("c-wa").checked = false; $("c-tel2").value = ""; $("c-wa2").checked = false; $("c-wa").disabled = $("c-tel2").disabled = $("c-wa2").disabled = true; }
    else if (!$("c-tel2").value.trim()) { $("c-wa2").checked = false; $("c-wa2").disabled = true; }
    $("bloco-plano").hidden = !$("m-aderir").checked;
    if ($("m-aderir").checked) atualizarPlano();
}

const PLACEHOLDER_DOC = { CPF: "000.000.000-00", CNPJ: "00.000.000/0000-00", Passaporte: "Número do documento" };
$("c-tipo-doc").addEventListener("change", () => { $("c-doc").placeholder = PLACEHOLDER_DOC[tipoDoc()]; });
const recalcular = ativarSequencia($("form-cadastro"), grupos, aoMudarFormulario);
// o bloco do plano abre/fecha com a caixa: recalcula logo depois de o bloco aparecer
$("m-aderir").addEventListener("change", () => { aoMudarFormulario(); recalcular(); });
["m-tipo", "m-categoria", "m-situacao", "m-forma"].forEach(id => $(id).addEventListener("change", () => { atualizarPlano(); recalcular(); }));
$("m-forma").innerHTML = `<option value="">Selecione...</option>${opcoesFormaPagamento()}`;
$("v-tipo").addEventListener("change", () => { $("m-categoria").value = $("v-tipo").value; });

/* o preenchimento do CEP muda vários campos de uma vez: recalcula a sequência */
["e-logradouro", "e-bairro", "e-cidade", "e-estado"].forEach(id => $(id).addEventListener("input", recalcular));
$("e-cep").addEventListener("input", () => setTimeout(recalcular, 700));

relogioPronto.then(() => { $("m-inicio").min = $("m-inicio").value = hojeISO(); recalcular(); });
if (usuario) Promise.all([api("/precos/"), api("/mensalidades/capacidade"), api("/mensalidades/vagas-premium")])
    .then(([p, c, vp]) => { precos = p; capacidade = c; vagasPremium = vp; atualizarPlano(); recalcular(); }).catch(() => { });

/* ----------------------------------------------------------- após salvar */
function mostrarContinuacao(titulo, texto) {
    $("bloco-form").hidden = true;
    $("bloco-continuar").hidden = false;
    $("titulo-continuar").textContent = titulo;
    $("texto-continuar").textContent = texto;
    desenharChips();
    $("o-placa").focus();
}

function desenharChips() {
    $("chips-veiculos").innerHTML = veiculosDoCliente.map(v => `<span>${placaHtml(v.placa)} <span class="ajuda">${esc(nomeVeiculo(v))}</span>
        <a class="btn sec pequeno" href="movimentacao.html?veiculo=${v.id}" ${dica("Ir para Entrada e saída com este veículo já escolhido")}>Registrar entrada</a></span>`).join("");
}

function voltarAoFormulario() {
    clienteAtual = null;
    veiculosDoCliente = [];
    $("bloco-continuar").hidden = true;
    $("bloco-form").hidden = false;
    $("form-cadastro").reset();
    $("c-pais").value = "Brasil";
    $("m-aderir").checked = false;
    $("m-inicio").value = hojeISO();
    history.replaceState(null, "", "cadastro.html");
    aoMudarFormulario();
    recalcular();
    $("c-nome").focus();
}
$("form-cadastro").addEventListener("reset", () => setTimeout(() => { $("c-pais").value = "Brasil"; $("m-inicio").value = hojeISO(); aoMudarFormulario(); recalcular(); }, 0));

/* ------------------------------------------------------------- salvar */
$("form-cadastro").addEventListener("submit", async ev => {
    ev.preventDefault();
    const v = id => $(id).value.trim();
    const erro = m => { aviso(m, "erro"); return true; };

    if (VALIDAR.nome(v("c-nome"), tipoDoc())) return erro(VALIDAR.nome(v("c-nome"), tipoDoc()));
    if (VALIDAR.documento(tipoDoc(), v("c-doc"))) return erro(VALIDAR.documento(tipoDoc(), v("c-doc")));
    if (v("c-pais").length < 2) return erro("Preencha o país.");
    if (VALIDAR.telefone(v("c-tel"))) return erro(VALIDAR.telefone(v("c-tel")));
    if (v("c-tel2") && !v("c-tel")) return erro("Informe o telefone principal antes do segundo telefone.");
    if (VALIDAR.telefone(v("c-tel2"))) return erro(VALIDAR.telefone(v("c-tel2")));

    const corpo = { cliente: {
        nome: v("c-nome"), tipo_documento: tipoDoc(), cpf: v("c-doc"), pais: v("c-pais"),
        telefone: v("c-tel") || null, telefone_whatsapp: $("c-wa").checked,
        telefone2: v("c-tel2") || null, telefone2_whatsapp: $("c-wa2").checked,
    } };

    const end = { cep: v("e-cep"), logradouro: v("e-logradouro"), numero: v("e-numero"), complemento: v("e-complemento") || null,
                  bairro: v("e-bairro"), cidade: v("e-cidade"), estado: v("e-estado").toUpperCase() };
    if (end.cep || end.logradouro || end.numero || end.bairro || end.cidade || end.estado) {
        if (!(end.cep && end.logradouro && end.numero && end.bairro && end.cidade && end.estado))
            return erro("Endereço incompleto: preencha CEP, rua, número, bairro, cidade e UF (ou deixe tudo em branco).");
        if (VALIDAR.cep(end.cep)) return erro(VALIDAR.cep(end.cep));
        corpo.endereco = end;
    }

    if (v("v-placa") || v("v-marca") || v("v-modelo")) {
        if (VALIDAR.placa(v("v-placa"))) return erro(VALIDAR.placa(v("v-placa")));
        if (v("v-marca").length < 2) return erro("Preencha a marca do veículo.");
        if (v("v-modelo").length < 2) return erro("Preencha o modelo do veículo.");
        corpo.veiculo = { placa: v("v-placa"), marca: v("v-marca"), modelo: v("v-modelo"), cor: v("v-cor") || null, tipo_veiculo: $("v-tipo").value };
    }

    if ($("m-aderir").checked) {
        const premium = $("m-tipo").value === "Premium", pago = $("m-situacao").value === "Pago";
        if (premium && !$("m-vaga").value) return erro("Plano premium: escolha a vaga exclusiva do cliente.");
        if (!premium && !(Number($("m-cotas").value) >= 1)) return erro("Informe a quantidade de cotas do plano.");
        if ($("m-inicio").value < hojeISO()) return erro("A data de adesão não pode ser anterior a hoje.");
        if (pago && !$("m-forma").value) return erro("Selecione a forma de pagamento da 1ª mensalidade.");
        const dinheiro = pago && $("m-forma").value === "Dinheiro", total = valorDoPlano();
        if (dinheiro && (!$("m-recebido").value || (total !== null && Number($("m-recebido").value) < total)))
            return erro(`Informe o valor recebido em dinheiro (no mínimo ${moeda(total)}).`);
        corpo.mensalidade = {
            tipo_plano: $("m-tipo").value, categoria: $("m-categoria").value, cotas: premium ? 1 : Number($("m-cotas").value),
            id_vaga: premium ? Number($("m-vaga").value) : null, data_inicio: $("m-inicio").value || null,
            status_primeira_cobranca: $("m-situacao").value, forma_pagamento: pago ? $("m-forma").value : null,
            valor_recebido: dinheiro ? Number($("m-recebido").value) : null,
        };
    }

    try {
        const r = await api("/cadastro/completo", { metodo: "POST", corpo });
        clienteAtual = r.cliente;
        veiculosDoCliente = r.veiculo ? [r.veiculo] : [];
        aviso("Cadastro salvo.");
        const m = r.mensalidade;
        const plano = m ? ` Plano ${m.tipo_plano.toLowerCase()} (${m.categoria}) com início em ${dataCurta(m.data_inicio)}.` : "";
        mostrarContinuacao(`Cliente cadastrado: ${r.cliente.nome}`,
            (r.veiculo ? "Você pode cadastrar outros veículos deste cliente agora." : "Nenhum veículo foi cadastrado ainda. Adicione o primeiro abaixo.") + plano);
    } catch (e) { erroAviso(e); }
});

/* --------------------------------------------- outro veículo do mesmo cliente */
ativarSequencia($("form-outro-veiculo"), [{ depende: null, campos: [
    { id: "o-tipo" },
    { id: "o-placa", validar: VALIDAR.placa, julgar: v => v.replace("-", "").length >= 7 },
    { id: "o-marca", validar: VALIDAR.texto("a marca") },
    { id: "o-modelo", validar: VALIDAR.texto("o modelo") },
    { id: "o-cor", opcional: true },
] }]);

$("form-outro-veiculo").addEventListener("submit", async ev => {
    ev.preventDefault();
    if (!clienteAtual) return;
    const v = id => $(id).value.trim();
    const msg = VALIDAR.placa(v("o-placa")) || (v("o-marca").length < 2 ? "Preencha a marca do veículo." : null) || (v("o-modelo").length < 2 ? "Preencha o modelo do veículo." : null);
    if (msg) { aviso(msg, "erro"); return; }
    try {
        const nv = await api("/veiculos/", { metodo: "POST", corpo: {
            id_cliente: clienteAtual.id, placa: v("o-placa"), marca: v("o-marca"), modelo: v("o-modelo"), cor: v("o-cor") || null, tipo_veiculo: $("o-tipo").value } });
        veiculosDoCliente.push(nv);
        desenharChips();
        ev.target.reset();
        ev.target.dispatchEvent(new Event("input", { bubbles: true }));
        aviso("Veículo adicionado.");
        $("o-placa").focus();
    } catch (e) { erroAviso(e); }
});

$("btn-novo-cliente").addEventListener("click", voltarAoFormulario);

/* cadastro.html?cliente=ID: adicionar veículo a um cliente que já existe */
const idUrl = new URLSearchParams(location.search).get("cliente");
if (usuario && idUrl) {
    (async () => {
        try {
            clienteAtual = await api(`/clientes/${idUrl}`);
            const lista = await api("/veiculos/busca", { params: { q: clienteAtual.cpf } });
            veiculosDoCliente = lista.filter(x => x.id_cliente === clienteAtual.id);
            mostrarContinuacao(`Adicionar veículo para ${clienteAtual.nome}`,
                veiculosDoCliente.length ? "Veículos já cadastrados deste cliente:" : "Este cliente ainda não tem veículos.");
        } catch (e) { erroAviso(e); }
    })();
}
