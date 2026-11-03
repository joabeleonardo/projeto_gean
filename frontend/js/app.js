/* ==========================================================================
   Funções compartilhadas por todas as telas: API, login, menu, máscaras,
   formatação e avisos.
   ========================================================================== */

// Se o frontend for aberto pela própria API (porta 8000) usa o mesmo endereço;
// caso contrário (Live Server, arquivo local) usa o endereço padrão do uvicorn.
const API_BASE = window.API_BASE || (location.port === "8000" ? location.origin : "http://127.0.0.1:8000");

const CHAVE_TOKEN = "est_token";
const CHAVE_USUARIO = "est_usuario";

/* ---------------------------------------------------------------- sessão */
function obterToken() { return localStorage.getItem(CHAVE_TOKEN); }

function obterUsuario() {
    try { return JSON.parse(localStorage.getItem(CHAVE_USUARIO)); } catch { return null; }
}

function salvarSessao(token, usuario) {
    localStorage.setItem(CHAVE_TOKEN, token);
    localStorage.setItem(CHAVE_USUARIO, JSON.stringify(usuario));
}

function sair() {
    localStorage.removeItem(CHAVE_TOKEN);
    localStorage.removeItem(CHAVE_USUARIO);
    location.href = "login.html";
}

function ehAdmin() {
    const u = obterUsuario();
    return !!u && u.perfil === "Administrador";
}

/* ------------------------------------------------------------------- API */
const ROTULOS_CAMPOS = {
    nome: "Nome", cpf: "CPF", telefone: "Telefone", cep: "CEP", logradouro: "Logradouro", numero: "Número",
    bairro: "Bairro", cidade: "Cidade", estado: "Estado", placa: "Placa", modelo: "Modelo", cor: "Cor",
    marca: "Marca", login: "Login", senha: "Senha", codigo_liberacao: "Código de liberação", nova_senha: "Nova senha", valor: "Valor", codigo_vaga: "Código da vaga",
};

function textoDoErro(detalhe) {
    if (!detalhe) return "Erro inesperado.";
    if (typeof detalhe === "string") return detalhe;
    if (!Array.isArray(detalhe) && detalhe.mensagem) return detalhe.mensagem;
    if (Array.isArray(detalhe)) {
        return detalhe.map(e => {
            const campo = e.loc ? e.loc[e.loc.length - 1] : "";
            const rotulo = ROTULOS_CAMPOS[campo] || campo;
            const msg = String(e.msg || "").replace(/^Value error, /, "");
            return rotulo ? `${rotulo}: ${msg}` : msg;
        }).join(" • ");
    }
    return "Erro inesperado.";
}

async function _apiBruta(caminho, { metodo = "GET", corpo = null, params = null } = {}) {
    let url = API_BASE + caminho;
    if (params) {
        const q = new URLSearchParams();
        Object.entries(params).forEach(([k, v]) => { if (v !== null && v !== undefined && v !== "") q.append(k, v); });
        const s = q.toString();
        if (s) url += (url.includes("?") ? "&" : "?") + s;
    }
    const cabecalhos = {};
    const token = obterToken();
    if (token) cabecalhos["Authorization"] = "Bearer " + token;
    if (corpo !== null) cabecalhos["Content-Type"] = "application/json";

    let resposta;
    try {
        resposta = await fetch(url, { method: metodo, headers: cabecalhos, body: corpo !== null ? JSON.stringify(corpo) : undefined });
    } catch {
        throw new Error("Não foi possível conectar à API. Verifique se o servidor está em execução.");
    }
    if (resposta.status === 401 && !location.pathname.endsWith("login.html")) { sair(); throw new Error("Sessão expirada."); }
    if (resposta.status === 204) return null;
    let dados = null;
    try { dados = await resposta.json(); } catch { /* resposta sem corpo */ }
    if (!resposta.ok) {
        const erro = new Error(textoDoErro(dados && dados.detail));
        erro.status = resposta.status;
        erro.detalhe = dados && dados.detail;   // objeto com dados extras, quando houver
        throw erro;
    }
    return dados;
}

/* Gravações idênticas feitas ao mesmo tempo (duplo clique em "Salvar") viram UMA só requisição:
   o servidor não recebe o cadastro duas vezes e a tela não repete a mensagem. */
const _emVoo = new Map();
function api(caminho, opcoes = {}) {
    const metodo = String(opcoes.metodo || "GET").toUpperCase();
    if (metodo === "GET") return _apiBruta(caminho, opcoes);
    const chave = `${metodo}|${caminho}|${JSON.stringify(opcoes.corpo ?? null)}`;
    if (_emVoo.has(chave)) return _emVoo.get(chave);
    const promessa = _apiBruta(caminho, opcoes).finally(() => _emVoo.delete(chave));
    _emVoo.set(chave, promessa);
    return promessa;
}

/* ------------------------------------------------------------- formatação */
function esc(valor) {
    return String(valor ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
const moeda = v => (v === null || v === undefined) ? "—" : Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const dataHora = v => v ? new Date(v).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" }) : "—";
const dataCurta = v => v ? new Date(v.length === 10 ? v + "T00:00:00" : v).toLocaleDateString("pt-BR") : "—";
function duracao(min) {
    if (min === null || min === undefined) return "—";
    const h = Math.floor(min / 60), m = min % 60;
    return h ? `${h}h ${String(m).padStart(2, "0")}min` : `${m}min`;
}
const FORMAS_PAGAMENTO = ["Dinheiro", "Pix", "Cartão de débito", "Cartão de crédito", "Transferência"];
const opcoesFormaPagamento = () => FORMAS_PAGAMENTO.map(f => `<option>${f}</option>`).join("");
const nomeVeiculo = v => [v.marca, v.modelo].filter(Boolean).join(" ");
const placaHtml = p => `<span class="placa">${esc(p)}</span>`;
/* A data e a hora usadas pelas telas vêm do SERVIDOR (não do relógio do computador do usuário):
   mudar o relógio local não altera "hoje" nem as datas padrão. */
let _deslocamentoRelogio = Number(sessionStorage.getItem("est_desloc") || 0);
const agoraServidor = () => new Date(Date.now() + _deslocamentoRelogio);
const pad2 = n => String(n).padStart(2, "0");
const isoLocal = d => `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
const hojeISO = () => isoLocal(agoraServidor());

async function sincronizarRelogio() {
    try {
        const r = await fetch(API_BASE + "/servidor/hora");
        const d = await r.json();
        // "agora" do servidor é um horário sem fuso: lido como horário local, o deslocamento é o que falta no relógio daqui
        _deslocamentoRelogio = new Date(d.agora).getTime() - Date.now();
        sessionStorage.setItem("est_desloc", String(_deslocamentoRelogio));
    } catch { /* sem conexão: mantém o último deslocamento conhecido */ }
}
const relogioPronto = sincronizarRelogio();
setInterval(sincronizarRelogio, 5 * 60 * 1000);
function debounce(fn, ms = 300) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }

/* ---------------------------------------------------------------- avisos */
/* Erros e validações aparecem em um MODAL no centro da tela (um só: se aparecer outro, o texto é trocado,
   nunca empilhado). Confirmações de sucesso usam uma faixa única no topo. */
function _dialogoAviso() {
    let dlg = document.getElementById("modal-aviso");
    if (!dlg) {
        dlg = document.createElement("dialog");
        dlg.id = "modal-aviso";
        dlg.className = "modal-aviso";
        dlg.setAttribute("role", "alertdialog");
        dlg.innerHTML = `<div class="dialogo-corpo"><h2 id="modal-aviso-titulo"></h2><p id="modal-aviso-texto"></p>
            <div class="acoes"><button class="btn" id="modal-aviso-ok" type="button">OK</button></div></div>`;
        document.body.appendChild(dlg);
        dlg.querySelector("#modal-aviso-ok").addEventListener("click", () => dlg.close());
    }
    return dlg;
}

function mostrarModal(texto, titulo = "Atenção") {
    const dlg = _dialogoAviso();
    dlg.querySelector("#modal-aviso-titulo").textContent = titulo;
    dlg.querySelector("#modal-aviso-texto").textContent = texto;
    if (!dlg.open) dlg.showModal();
    dlg.querySelector("#modal-aviso-ok").focus();
}

let _timerFaixa = null;
function mostrarFaixa(texto) {
    let faixa = document.getElementById("faixa-aviso");
    if (!faixa) {
        faixa = document.createElement("div");
        faixa.id = "faixa-aviso";
        faixa.setAttribute("role", "status");
        document.body.appendChild(faixa);
    }
    faixa.textContent = texto;
    faixa.classList.add("visivel");
    clearTimeout(_timerFaixa);
    _timerFaixa = setTimeout(() => faixa.classList.remove("visivel"), 3800);
}

function aviso(mensagem, tipo = "ok") {
    if (tipo === "erro") mostrarModal(mensagem); else mostrarFaixa(mensagem);
}
const erroAviso = e => aviso(e.message || String(e), "erro");

/* Pergunta de confirmação em modal (no lugar do confirm() do navegador). Resolve true/false. */
function confirmar(texto, { titulo = "Confirmar", sim = "Confirmar", nao = "Cancelar", perigo = false } = {}) {
    return new Promise(resolve => {
        const dlg = document.createElement("dialog");
        dlg.className = "modal-aviso";
        dlg.innerHTML = `<div class="dialogo-corpo"><h2>${esc(titulo)}</h2><p>${esc(texto)}</p>
            <div class="acoes"><button class="btn ${perigo ? "perigo" : ""}" data-r="1" type="button">${esc(sim)}</button>
            <button class="btn sec" data-r="0" type="button">${esc(nao)}</button></div></div>`;
        document.body.appendChild(dlg);
        let resposta = false;
        dlg.addEventListener("click", ev => { const b = ev.target.closest("[data-r]"); if (b) { resposta = b.dataset.r === "1"; dlg.close(); } });
        dlg.addEventListener("close", () => { dlg.remove(); resolve(resposta); });
        dlg.showModal();
        dlg.querySelector('[data-r="0"]').focus();
    });
}

/* Pergunta um número em modal (no lugar do prompt()). Resolve o número ou null. */
function perguntarNumero(texto, atual, { titulo = "Informe", min = 1, max = 999 } = {}) {
    return new Promise(resolve => {
        const dlg = document.createElement("dialog");
        dlg.className = "modal-aviso";
        dlg.innerHTML = `<form class="dialogo-corpo" method="dialog"><h2>${esc(titulo)}</h2><div class="campo"><label for="pn-valor">${esc(texto)}</label>
            <input id="pn-valor" type="number" min="${min}" max="${max}" value="${esc(atual)}"></div>
            <div class="acoes"><button class="btn" type="submit">Confirmar</button><button class="btn sec" type="button" data-nao>Cancelar</button></div></form>`;
        document.body.appendChild(dlg);
        let valor = null;
        dlg.querySelector("[data-nao]").addEventListener("click", () => dlg.close());
        dlg.querySelector("form").addEventListener("submit", () => { const n = Number(dlg.querySelector("#pn-valor").value); valor = n >= min && n <= max ? n : null; });
        dlg.addEventListener("close", () => { dlg.remove(); resolve(valor); });
        dlg.showModal();
        dlg.querySelector("#pn-valor").select();
    });
}

/* ---------------------------------------------------- dicas ao passar o mouse */
/* Qualquer elemento com data-dica="texto" mostra uma explicação ao passar o mouse (ou focar com o teclado). */
const dica = texto => `data-dica="${esc(texto)}"`;
(function iniciarDicas() {
    let caixa = null, alvo = null;
    const mostrar = el => {
        if (!caixa) { caixa = document.createElement("div"); caixa.id = "dica"; caixa.setAttribute("role", "tooltip"); document.body.appendChild(caixa); }
        alvo = el;
        caixa.textContent = el.dataset.dica;
        caixa.classList.add("visivel");
        const r = el.getBoundingClientRect(), c = caixa.getBoundingClientRect();
        const x = Math.min(Math.max(8, r.left + r.width / 2 - c.width / 2), window.innerWidth - c.width - 8);
        const acima = r.top - c.height - 8 > 8;
        caixa.style.left = `${x}px`;
        caixa.style.top = `${acima ? r.top - c.height - 8 : r.bottom + 8}px`;
    };
    const esconder = () => { alvo = null; if (caixa) caixa.classList.remove("visivel"); };
    document.addEventListener("mouseover", ev => { const el = ev.target.closest && ev.target.closest("[data-dica]"); if (el && el !== alvo) mostrar(el); else if (!el) esconder(); });
    document.addEventListener("focusin", ev => { const el = ev.target.closest && ev.target.closest("[data-dica]"); if (el) mostrar(el); });
    document.addEventListener("focusout", esconder);
    document.addEventListener("click", esconder);
    window.addEventListener("scroll", esconder, true);
})();

/* --------------------------------------------------------------- máscaras */
const digitos = v => String(v || "").replace(/\D/g, "");

const MASCARAS = {
    cpf(v) {
        const d = digitos(v).slice(0, 11);
        return d.replace(/^(\d{3})(\d)/, "$1.$2").replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3").replace(/\.(\d{3})(\d)/, ".$1-$2");
    },
    cnpj(v) {
        const d = digitos(v).slice(0, 14);
        return d.replace(/^(\d{2})(\d)/, "$1.$2").replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
            .replace(/\.(\d{3})(\d)/, ".$1/$2").replace(/(\d{4})(\d)/, "$1-$2");
    },
    passaporte(v) { return String(v || "").toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 20); },
    telefone(v) {
        const bruto = String(v || "").trim();
        if (bruto.startsWith("+")) return "+" + digitos(bruto).slice(0, 15);      // número do exterior: só + e dígitos
        const d = digitos(bruto).slice(0, 11);
        if (d.length <= 2) return d ? `(${d}` : "";
        if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
        if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
        return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
    },
    cep(v) {
        const d = digitos(v).slice(0, 8);
        return d.length > 5 ? `${d.slice(0, 5)}-${d.slice(5)}` : d;
    },
    placa(v) {
        const p = String(v || "").toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 7);
        // padrão antigo (ABC-1234) tem número na 5ª posição; Mercosul (ABC1D23) tem letra
        return p.length > 3 && /\d/.test(p[4] || "") ? `${p.slice(0, 3)}-${p.slice(3)}` : p;
    },
};

/* data-mascara="cpf|cnpj|telefone|cep|placa"  ou  data-mascara="documento" (segue o select indicado em data-tipo-doc) */
function ativarMascaras(raiz = document) {
    raiz.querySelectorAll("[data-mascara]").forEach(input => {
        if (input.dataset.mascaraAtiva) return;
        input.dataset.mascaraAtiva = "1";
        const aplicar = () => {
            let nome = input.dataset.mascara;
            if (nome === "documento") {
                const tipo = (document.getElementById(input.dataset.tipoDoc) || {}).value || "CPF";
                nome = tipo === "CNPJ" ? "cnpj" : tipo === "Passaporte" ? "passaporte" : "cpf";
            }
            const f = MASCARAS[nome];
            if (f) input.value = f(input.value);
        };
        input.addEventListener("input", aplicar);
        const sel = input.dataset.tipoDoc && document.getElementById(input.dataset.tipoDoc);
        if (sel) sel.addEventListener("change", () => { input.value = ""; input.dispatchEvent(new Event("input", { bubbles: true })); });
        aplicar();
    });
}

function cpfValido(cpf) {
    const d = digitos(cpf);
    if (d.length !== 11 || /^(\d)\1+$/.test(d)) return false;
    for (const t of [9, 10]) {
        let soma = 0;
        for (let i = 0; i < t; i++) soma += Number(d[i]) * (t + 1 - i);
        if (((soma * 10) % 11) % 10 !== Number(d[t])) return false;
    }
    return true;
}

function cnpjValido(cnpj) {
    const d = digitos(cnpj);
    if (d.length !== 14 || /^(\d)\1+$/.test(d)) return false;
    for (const t of [12, 13]) {
        const pesos = t === 12 ? [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] : [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
        let soma = 0;
        for (let i = 0; i < t; i++) soma += Number(d[i]) * pesos[i];
        const resto = soma % 11;
        if ((resto < 2 ? 0 : 11 - resto) !== Number(d[t])) return false;
    }
    return true;
}

const placaValida = p => /^[A-Z]{3}-?\d[A-Z0-9]\d{2}$/.test(String(p).toUpperCase());

/* Validações com a mensagem que o usuário vê (null = válido). */
const VALIDAR = {
    nome(v, tipoDoc = "CPF") {
        const t = String(v || "").trim();
        if (t.length < 3) return "Preencha o nome completo.";
        if (tipoDoc !== "CNPJ" && t.split(/\s+/).length < 2) return "Preencha o nome completo (nome e sobrenome).";
        return null;
    },
    documento(tipo, v) {
        if (tipo === "CNPJ") return cnpjValido(v) ? null : "CNPJ inválido. Confira os números.";
        if (tipo === "Passaporte") return /^[A-Z0-9]{5,20}$/.test(String(v || "").toUpperCase().replace(/[^A-Z0-9]/g, "")) ? null : "Documento estrangeiro inválido: use de 5 a 20 letras e números.";
        return cpfValido(v) ? null : "CPF inválido. Confira os números.";
    },
    telefone(v) {
        const t = String(v || "").trim();
        if (!t) return null;
        const d = digitos(t);
        if (t.startsWith("+")) return d.length >= 8 && d.length <= 15 ? null : "Telefone internacional inválido: use + e o número com DDI.";
        return d.length === 10 || d.length === 11 ? null : "Telefone inválido: informe DDD + número.";
    },
    placa: v => placaValida(v) ? null : "Placa inválida. Use ABC-1234 ou ABC1D23.",
    cep: v => digitos(v).length === 8 ? null : "CEP inválido: informe os 8 dígitos.",
    texto: (rotulo, min = 2) => v => String(v || "").trim().length >= min ? null : `Preencha ${rotulo}.`,
    uf: v => /^[A-Za-z]{2}$/.test(String(v || "").trim()) ? null : "UF inválida: use a sigla com 2 letras.",
};

const whatsLink = tel => {
    const d = digitos(tel);
    if (!tel) return "";
    return `https://wa.me/${String(tel).startsWith("+") ? d : (d.length <= 11 ? "55" + d : d)}`;
};

/* ------------------------------------------------------ preenchimento sequencial */
/* Cada campo só é liberado quando o anterior está preenchido corretamente.
   campos: [{ id, validar(valor)->mensagem|null, opcional, julgar(valor)->bool }]
   * opcional: campo vazio não trava os seguintes (se preenchido, precisa estar correto);
   * julgar: só mostra o erro quando o valor já está "completo o bastante" (ex.: CPF com 11 dígitos);
   * ao sair de um campo inválido, um modal explica o que está errado.
   Devolve true quando todos os campos obrigatórios do grupo estão corretos. */
function sequenciar(campos, liberado = true) {
    let ok = liberado;
    for (const c of campos) {
        const el = document.getElementById(c.id);
        if (!el || el.closest("[hidden]")) continue;     // campo que não se aplica agora (escondido)
        const caixa = el.closest(".campo");
        el.disabled = !ok;
        if (caixa) caixa.classList.toggle("bloqueado", !ok);
        let erro = caixa ? caixa.querySelector(".erro-campo") : null;
        if (!ok) { if (erro) erro.textContent = ""; el.classList.remove("invalido"); continue; }
        const valor = el.type === "checkbox" ? (el.checked ? "1" : "") : String(el.value || "").trim();
        const msg = c.validar && valor !== "" ? c.validar(valor) : null;
        const mostrar = msg && (!c.julgar || c.julgar(valor));
        if (caixa && !erro) { erro = document.createElement("small"); erro.className = "erro-campo"; caixa.appendChild(erro); }
        if (erro) erro.textContent = mostrar ? msg : "";
        el.classList.toggle("invalido", !!mostrar);
        if (msg) ok = false;
        else if (valor === "" && !c.opcional && el.type !== "checkbox") ok = false;
    }
    return ok;
}

/* Liga a sequência a um formulário: recalcula a cada digitação/seleção e avisa em modal ao sair de campo inválido.
   grupos: [{ campos, depende: indice do grupo anterior | null }] — um grupo só abre quando o grupo "depende" está completo. */
function ativarSequencia(raiz, grupos, aoMudar = () => { }) {
    const configs = new Map();
    grupos.forEach(g => g.campos.forEach(c => configs.set(c.id, c)));
    const recalcular = () => {
        const completo = [];
        grupos.forEach((g, i) => { completo[i] = sequenciar(g.campos, g.depende == null ? true : completo[g.depende]); });
        aoMudar(completo);
    };
    raiz.addEventListener("input", recalcular);
    raiz.addEventListener("change", recalcular);
    raiz.addEventListener("focusout", ev => {
        const el = ev.target, c = configs.get(el.id);
        if (!c || !c.validar || el.disabled) return;
        const v = String(el.value || "").trim();
        const msg = v !== "" ? c.validar(v) : null;
        if (msg && el.dataset.avisado !== v) { el.dataset.avisado = v; setTimeout(() => { mostrarModal(msg); }, 0); }
    });
    recalcular();
    return recalcular;
}

/* ------------------------------------------------------------------- paginação */
/* Só pede ao servidor as linhas da página que está na tela (nada de carregar tudo de uma vez).
   O tamanho inicial se ajusta ao que cabe na tela: 10 ou 20 por página. */
function linhasQueCabem() { return window.innerHeight >= 1000 ? 20 : 10; }

function criarPaginador(raiz, carregar) {
    const estado = { pagina: 1, porPagina: linhasQueCabem() };
    raiz.classList.add("paginador");
    raiz.innerHTML = `<span class="pag-total"></span>
        <label>Por página <select class="pag-tam">${[10, 20, 50, 100].map(n => `<option ${n === estado.porPagina ? "selected" : ""}>${n}</option>`).join("")}</select></label>
        <button type="button" class="btn sec pequeno pag-ant" ${dica("Página anterior")}>‹ Anterior</button>
        <span class="pag-pos"></span>
        <button type="button" class="btn sec pequeno pag-prox" ${dica("Próxima página")}>Próxima ›</button>`;
    const q = s => raiz.querySelector(s);
    let ultimo = { paginas: 1 };

    async function recarregar() {
        try {
            ultimo = await carregar({ pagina: estado.pagina, por_pagina: estado.porPagina });
            if (estado.pagina > ultimo.paginas) { estado.pagina = ultimo.paginas; return recarregar(); }
            q(".pag-total").textContent = `${ultimo.total} registro(s)`;
            q(".pag-pos").textContent = `Página ${ultimo.pagina} de ${ultimo.paginas}`;
            q(".pag-ant").disabled = ultimo.pagina <= 1;
            q(".pag-prox").disabled = ultimo.pagina >= ultimo.paginas;
        } catch (e) { erroAviso(e); }
    }
    q(".pag-ant").addEventListener("click", () => { estado.pagina -= 1; recarregar(); });
    q(".pag-prox").addEventListener("click", () => { estado.pagina += 1; recarregar(); });
    q(".pag-tam").addEventListener("change", ev => { estado.porPagina = Number(ev.target.value); estado.pagina = 1; recarregar(); });
    return { recarregar, primeira() { estado.pagina = 1; return recarregar(); }, estado };
}

/* Preenche o endereço a partir do CEP (ViaCEP). Se estiver sem internet, o usuário digita. */
function ligarBuscaCep(campos) {
    const cep = document.getElementById(campos.cep);
    cep.addEventListener("input", async () => {
        const d8 = digitos(cep.value);
        if (d8.length !== 8 || cep.dataset.buscado === d8) return;
        cep.dataset.buscado = d8;
        try {
            const r = await fetch(`https://viacep.com.br/ws/${digitos(cep.value)}/json/`);
            const d = await r.json();
            if (d.erro) { aviso("CEP não encontrado. Preencha o endereço manualmente.", "erro"); return; }
            document.getElementById(campos.logradouro).value = d.logradouro || "";
            document.getElementById(campos.bairro).value = d.bairro || "";
            document.getElementById(campos.cidade).value = d.localidade || "";
            document.getElementById(campos.estado).value = d.uf || "";
            // avisa o formulário (sequência de campos) que vários campos foram preenchidos de uma vez
            document.getElementById(campos.logradouro).dispatchEvent(new Event("input", { bubbles: true }));
            document.getElementById(campos.numero).focus();
        } catch { /* sem internet: preenchimento manual */ }
    });
}

/* ------------------------------------------------------- menu e cabeçalho */
const ITENS_MENU = [
    { id: "painel", href: "index.html", rotulo: "Painel" },
    { id: "movimentacao", href: "movimentacao.html", rotulo: "Entrada e saída" },
    { grupo: "Cadastros" },
    { id: "cadastro", href: "cadastro.html", rotulo: "Novo cadastro" },
    { id: "clientes", href: "clientes.html", rotulo: "Clientes" },
    { id: "veiculos", href: "veiculos.html", rotulo: "Veículos" },
    { id: "vagas", href: "vagas.html", rotulo: "Vagas" },
    { grupo: "Financeiro" },
    { id: "pagamentos", href: "pagamentos.html", rotulo: "Pagamentos" },
    { id: "inadimplencia", href: "inadimplencia.html", rotulo: "Inadimplência" },
    { id: "relatorios", href: "relatorios.html", rotulo: "Relatórios", admin: true },
    { id: "precos", href: "precos.html", rotulo: "Preços", admin: true },
    { grupo: "Administração", admin: true },
    { id: "usuarios", href: "usuarios.html", rotulo: "Usuários", admin: true },
    { id: "logs", href: "logs.html", rotulo: "Logs do sistema", admin: true },
];

/* Chame no início de cada tela. A checagem aqui é só de conveniência:
   quem realmente bloqueia o acesso é a API (token + perfil). */
function iniciarPagina({ pagina, titulo, apenasAdmin = false }) {
    if (!obterToken() || !obterUsuario()) { location.href = "login.html"; return null; }
    const usuario = obterUsuario();
    if (apenasAdmin && usuario.perfil !== "Administrador") { location.href = "index.html"; return null; }

    document.title = `${titulo} · Estacionamento`;
    const menu = document.getElementById("menu");
    if (menu) {
        const links = ITENS_MENU
            .filter(i => !i.admin || usuario.perfil === "Administrador")
            .map(i => i.grupo ? `<div class="grupo">${i.grupo}</div>`
                : `<a href="${i.href}" class="${i.id === pagina ? "ativo" : ""}">${i.rotulo}</a>`).join("");
        menu.innerHTML = `<div class="marca"><span class="marca-sinal">P</span>Estacionamento</div><nav>${links}</nav>`;
    }
    const topo = document.getElementById("topo");
    if (topo) {
        topo.innerHTML = `<h1>${esc(titulo)}</h1>
            <div class="usuario"><span>${esc(usuario.nome)}<small>${esc(usuario.perfil)}</small></span>
            <button class="btn sec pequeno" id="btn-minha-senha" type="button">Minha senha</button>
            <button class="btn sec pequeno" id="btn-sair" type="button">Sair</button></div>`;
        document.getElementById("btn-sair").addEventListener("click", sair);
        document.getElementById("btn-minha-senha").addEventListener("click", abrirTrocaSenha);
    }
    ativarMascaras();
    return usuario;
}

function abrirTrocaSenha() {
    let dlg = document.getElementById("dlg-senha");
    if (!dlg) {
        dlg = document.createElement("dialog");
        dlg.id = "dlg-senha";
        dlg.innerHTML = `<form method="dialog" class="dialogo-corpo" id="form-senha">
            <h2>Alterar minha senha</h2>
            <div class="campo"><label for="senha-atual">Senha atual</label><input type="password" id="senha-atual" required autocomplete="current-password"></div>
            <div class="campo" style="margin-top:12px"><label for="senha-nova">Nova senha (mínimo 6 caracteres)</label><input type="password" id="senha-nova" required minlength="6" autocomplete="new-password"></div>
            <div class="acoes"><button class="btn" type="submit">Salvar nova senha</button><button class="btn sec" type="button" id="senha-cancelar">Cancelar</button></div></form>`;
        document.body.appendChild(dlg);
        dlg.querySelector("#senha-cancelar").addEventListener("click", () => dlg.close());
        dlg.querySelector("form").addEventListener("submit", async ev => {
            ev.preventDefault();
            try {
                await api("/auth/senha", { metodo: "PUT", corpo: { senha_atual: dlg.querySelector("#senha-atual").value, nova_senha: dlg.querySelector("#senha-nova").value } });
                aviso("Senha alterada com sucesso.");
                dlg.close();
                dlg.querySelector("form").reset();
            } catch (e) { erroAviso(e); }
        });
    }
    dlg.showModal();
}

/* Campo com busca: digite parte do texto e escolha na lista (datalist).
   buscar(texto) deve devolver [{ id, rotulo }]. Retorna { valor(), definir(id, rotulo), limpar() }. */
function seletorComBusca(input, buscar, aoEscolher = null) {
    const lista = document.createElement("datalist");
    lista.id = "lista-" + input.id;
    input.setAttribute("list", lista.id);
    input.autocomplete = "off";
    input.after(lista);
    let mapa = new Map();
    let itensPorRotulo = new Map();
    let escolhido = null;

    const carregar = debounce(async () => {
        try {
            const itens = await buscar(input.value.trim());
            mapa = new Map(itens.map(i => [i.rotulo, i.id]));
            itensPorRotulo = new Map(itens.map(i => [i.rotulo, i]));
            lista.innerHTML = itens.map(i => `<option value="${esc(i.rotulo)}"></option>`).join("");
        } catch { /* ignora erros de digitação */ }
    }, 250);

    input.addEventListener("input", () => {
        const anterior = escolhido;
        escolhido = mapa.has(input.value) ? mapa.get(input.value) : null;
        if (aoEscolher && escolhido !== anterior) aoEscolher(escolhido ? itensPorRotulo.get(input.value) : null);
        carregar();
    });
    input.addEventListener("focus", carregar);
    return {
        valor: () => escolhido,
        item: () => (escolhido ? itensPorRotulo.get(input.value) || null : null),
        definir(id, rotulo, item = null) {
            escolhido = id; input.value = rotulo; mapa.set(rotulo, id);
            if (item) itensPorRotulo.set(rotulo, item);
            if (aoEscolher) aoEscolher(item || { id, rotulo });
        },
        limpar() { const tinha = escolhido; escolhido = null; input.value = ""; if (aoEscolher && tinha) aoEscolher(null); },
    };
}

/* Exporta linhas para CSV (abre certo no Excel em português: separador ; e BOM). */
function baixarCSV(nomeArquivo, colunas, linhas) {
    const cel = v => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const texto = [colunas.map(c => cel(c.rotulo)).join(";")]
        .concat(linhas.map(l => colunas.map(c => cel(c.csv ? c.csv(l) : l[c.chave])).join(";"))).join("\r\n");
    const blob = new Blob(["\ufeff" + texto], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = nomeArquivo;
    a.click();
    URL.revokeObjectURL(a.href);
}
