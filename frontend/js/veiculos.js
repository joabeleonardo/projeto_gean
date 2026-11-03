<<<<<<< HEAD
const usuario = iniciarPagina({ pagina: "veiculos", titulo: "Veículos" });
const $ = id => document.getElementById(id);
const tbody = $("tbody");
let veiculos = [];
let recalcularForm = () => { };

const seletorCliente = seletorComBusca($("cliente-busca"), async termo => {
    const lista = await api("/clientes/busca", { params: { q: termo } });
    return lista.map(c => ({ id: c.id, rotulo: `${c.nome} · ${c.cpf}` }));
}, () => recalcularForm());

/* ------------------------------------------------------------ listagem */
function filtros() {
    return { placa: $("f-placa").value.trim(), veiculo: $("f-veiculo").value.trim(), proprietario: $("f-dono").value.trim(),
             documento: $("f-doc").value.trim(), tipo: $("f-tipo").value, ordem: $("f-ordem").value };
}

async function carregarPagina({ pagina, por_pagina }) {
    const r = await api("/veiculos/pagina", { params: { ...filtros(), pagina, por_pagina } });
    veiculos = r.itens;
    tbody.innerHTML = r.itens.length ? r.itens.map(v => `<tr>
        <td>${placaHtml(v.placa)} ${v.no_patio ? `<span class="selo ocupada" ${dica("Este veículo está no pátio agora")}>no pátio</span>` : ""}</td>
        <td>${esc(v.tipo_veiculo || "Carro")}</td><td>${esc(nomeVeiculo(v))}</td><td>${esc(v.cor || "—")}</td>
        <td>${esc(v.cliente_nome)}<div class="ajuda">${esc(v.cliente_cpf)}</div></td>
        <td class="acoes-celula">
            <a class="btn pequeno" href="movimentacao.html?veiculo=${v.id}" ${dica("Ir para Entrada e saída com este veículo já escolhido")}>Registrar entrada</a>
            <button class="btn sec pequeno" data-editar="${v.id}" ${dica("Corrigir placa, marca, modelo, cor ou tipo do veículo")}>Editar</button>
            ${ehAdmin() ? `<button class="btn perigo pequeno" data-excluir="${v.id}" data-placa="${esc(v.placa)}" ${dica("Excluir o veículo (só se não tiver histórico de entradas)")}>Excluir</button>` : ""}
        </td></tr>`).join("")
        : `<tr><td colspan="6" class="vazio">Nenhum veículo encontrado.</td></tr>`;
    return r;
}

const paginador = criarPaginador($("paginador"), carregarPagina);
const filtrar = debounce(() => paginador.primeira(), 350);
["f-placa", "f-veiculo", "f-dono", "f-doc"].forEach(id => $(id).addEventListener("input", filtrar));
["f-tipo", "f-ordem"].forEach(id => $(id).addEventListener("change", () => paginador.primeira()));
$("btn-limpar").addEventListener("click", () => { ["f-placa", "f-veiculo", "f-dono", "f-doc"].forEach(id => { $(id).value = ""; }); $("f-tipo").value = ""; $("f-ordem").value = "placa"; paginador.primeira(); });

/* ------------------------------------------------------- editar veículo */
function abrirEdicao(v) {
    const dlg = document.createElement("dialog");
    dlg.innerHTML = `<form class="dialogo-corpo" novalidate>
        <h2>Editar veículo ${esc(v.placa)}</h2>
        <p class="ajuda">Proprietário: ${esc(v.cliente_nome)}</p>
        ${v.no_patio ? `<p class="erro-form">Veículo no pátio: o tipo (carro/moto) só pode ser alterado depois da saída.</p>` : ""}
        <div class="form-grid coluna-unica" style="margin-top:10px">
            <div class="campo"><label for="ev-tipo">Tipo</label><select id="ev-tipo" ${v.no_patio ? "disabled" : ""}><option>Carro</option><option>Moto</option></select></div>
            <div class="campo"><label for="ev-placa">Placa</label><input id="ev-placa" data-mascara="placa" maxlength="8" value="${esc(v.placa)}"></div>
            <div class="campo"><label for="ev-marca">Marca</label><input id="ev-marca" maxlength="50" value="${esc(v.marca || "")}"></div>
            <div class="campo"><label for="ev-modelo">Modelo</label><input id="ev-modelo" maxlength="50" value="${esc(v.modelo)}"></div>
            <div class="campo"><label for="ev-cor">Cor (opcional)</label><input id="ev-cor" maxlength="30" value="${esc(v.cor || "")}"></div>
        </div>
        <div class="acoes"><button class="btn" type="submit">Salvar alterações</button><button class="btn sec" type="button" data-fechar>Cancelar</button></div>
    </form>`;
    document.body.appendChild(dlg);
    dlg.querySelector("#ev-tipo").value = v.tipo_veiculo || "Carro";
    ativarMascaras(dlg);
    dlg.addEventListener("close", () => dlg.remove());
    dlg.querySelector("[data-fechar]").addEventListener("click", () => dlg.close());
    const form = dlg.querySelector("form");
    ativarSequencia(form, [{ depende: null, campos: [
        { id: "ev-tipo" },
        { id: "ev-placa", validar: VALIDAR.placa, julgar: x => x.replace("-", "").length >= 7 },
        { id: "ev-marca", validar: VALIDAR.texto("a marca") },
        { id: "ev-modelo", validar: VALIDAR.texto("o modelo") },
        { id: "ev-cor", opcional: true },
    ] }]);
    form.addEventListener("submit", async ev => {
        ev.preventDefault();
        const g = i => form.querySelector(`#ev-${i}`).value.trim();
        const falha = VALIDAR.placa(g("placa")) || (g("marca").length < 2 ? "Preencha a marca do veículo." : null) || (g("modelo").length < 2 ? "Preencha o modelo do veículo." : null);
        if (falha) { aviso(falha, "erro"); return; }
        try {
            await api(`/veiculos/${v.id}`, { metodo: "PUT", corpo: {
                id_cliente: v.id_cliente, placa: g("placa"), marca: g("marca"), modelo: g("modelo"), cor: g("cor") || null, tipo_veiculo: g("tipo"),
            } });
            dlg.close();
            aviso("Veículo atualizado.");
            paginador.recarregar();
        } catch (e) { erroAviso(e); }
    });
    dlg.showModal();
}

tbody.addEventListener("click", async ev => {
    const editar = ev.target.closest("[data-editar]");
    if (editar) { abrirEdicao(veiculos.find(x => String(x.id) === editar.dataset.editar)); return; }
    const botao = ev.target.closest("[data-excluir]");
    if (!botao || !await confirmar(`Excluir o veículo ${botao.dataset.placa}?`, { titulo: "Excluir veículo", sim: "Excluir", perigo: true })) return;
    try { await api(`/veiculos/${botao.dataset.excluir}`, { metodo: "DELETE" }); aviso("Veículo excluído."); paginador.recarregar(); }
    catch (e) { erroAviso(e); }
});

/* ------------------------------------------------- cadastro avulso (sequencial) */
recalcularForm = ativarSequencia($("form-veiculo"), [{ depende: null, campos: [
    { id: "cliente-busca", validar: () => seletorCliente.valor() ? null : "Escolha o proprietário na lista de sugestões.", julgar: () => false },
    { id: "tipo" },
    { id: "placa", validar: VALIDAR.placa, julgar: v => v.replace("-", "").length >= 7 },
    { id: "marca", validar: VALIDAR.texto("a marca") },
    { id: "modelo", validar: VALIDAR.texto("o modelo") },
    { id: "cor", opcional: true },
] }]);

$("form-veiculo").addEventListener("submit", async ev => {
    ev.preventDefault();
    const idCliente = seletorCliente.valor();
    if (!idCliente) { aviso("Escolha o proprietário na lista de sugestões.", "erro"); return; }
    const v = i => $(i).value.trim();
    const falha = VALIDAR.placa(v("placa")) || (v("marca").length < 2 ? "Preencha a marca do veículo." : null) || (v("modelo").length < 2 ? "Preencha o modelo do veículo." : null);
    if (falha) { aviso(falha, "erro"); return; }
    try {
        await api("/veiculos/", { metodo: "POST", corpo: {
            id_cliente: idCliente, placa: v("placa"), marca: v("marca"), modelo: v("modelo"), tipo_veiculo: $("tipo").value, cor: v("cor") || null } });
        aviso("Veículo cadastrado.");
        ev.target.reset();
        seletorCliente.limpar();
        recalcularForm();
        paginador.recarregar();
    } catch (e) { erroAviso(e); }
});

const q = new URLSearchParams(location.search).get("q");
if (q) $("f-doc").value = q.replace(/\D/g, "") ? q : "";
if (q && !$("f-doc").value) $("f-veiculo").value = q;
if (usuario) paginador.recarregar();
=======
const API_VEICULOS = 'http://127.0.0.1:8000/veiculos';
const API_CLIENTES = 'http://127.0.0.1:8000/clientes';

// Carrega os dados assim que a tela abre
document.addEventListener('DOMContentLoaded', () => {
    carregarClientesParaSelect();
    carregarVeiculos();
});

// --------------------------------------------------------
// 1. CARREGAR CLIENTES (Para o campo Select)
// --------------------------------------------------------
async function carregarClientesParaSelect() {
    try {
        const resposta = await fetch(`${API_CLIENTES}/`);
        if (resposta.ok) {
            const clientes = await resposta.json();
            const selectCliente = document.getElementById('id_cliente');
            
            // Limpa o select e adiciona a opção padrão
            selectCliente.innerHTML = '<option value="">Selecione um cliente...</option>';
            
            // Preenche com os clientes do banco
            clientes.forEach(cliente => {
                const option = document.createElement('option');
                option.value = cliente.id;
                option.textContent = `${cliente.nome} (CPF: ${cliente.cpf})`;
                selectCliente.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Erro ao buscar clientes:', error);
    }
}

// --------------------------------------------------------
// 2. CADASTRAR VEÍCULO (POST)
// --------------------------------------------------------
document.getElementById('form-veiculo').addEventListener('submit', async function(event) {
    event.preventDefault();

    // Monta o payload conforme a Entidade Veiculo do FastAPI
    const payload = {
        id_cliente: parseInt(document.getElementById('id_cliente').value),
        placa: document.getElementById('placa').value,
        modelo: document.getElementById('modelo').value,
        cor: document.getElementById('cor').value,
        id_usuario_logado: 1,           // Regra Crítica de Auditoria
        nome_usuario_logado: "Admin"    // Regra Crítica de Auditoria
    };

    try {
        const resposta = await fetch(`${API_VEICULOS}/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (resposta.ok) {
            alert('Veículo cadastrado com sucesso!');
            document.getElementById('form-veiculo').reset();
            carregarVeiculos(); // Atualiza a tabela
        } else {
            const erro = await resposta.json();
            alert(`Erro ao cadastrar: ${erro.detail}`);
        }
    } catch (error) {
        console.error("Erro de conexão:", error);
    }
});

// --------------------------------------------------------
// 3. LISTAR VEÍCULOS (GET)
// --------------------------------------------------------
async function carregarVeiculos() {
    try {
        const resposta = await fetch(`${API_VEICULOS}/`);
        
        if (resposta.ok) {
            const veiculos = await resposta.json();
            const corpoTabela = document.querySelector('#tabela-veiculos tbody');
            corpoTabela.innerHTML = ''; 

            veiculos.forEach(veiculo => {
                const linha = document.createElement('tr');
                linha.innerHTML = `
                    <td>${veiculo.id}</td>
                    <td><strong>${veiculo.placa}</strong></td>
                    <td>${veiculo.modelo}</td>
                    <td>${veiculo.cor || 'S/N'}</td>
                    <td>${veiculo.id_cliente}</td>
                    <td>
                        <button onclick="deletarVeiculo(${veiculo.id})" style="color: red; cursor: pointer;">Excluir</button>
                    </td>
                `;
                corpoTabela.appendChild(linha);
            });
        }
    } catch (error) {
        console.error('Erro ao buscar veículos:', error);
    }
}

// --------------------------------------------------------
// 4. EXCLUIR VEÍCULO (DELETE)
// --------------------------------------------------------
async function deletarVeiculo(id) {
    if (!confirm("Tem certeza que deseja excluir este veículo?")) return;

    try {
        // Envia os dados de auditoria pela URL
        const urlComAuditoria = `${API_VEICULOS}/${id}?id_usuario_logado=1&nome_usuario_logado=Admin`;
        const resposta = await fetch(urlComAuditoria, { method: 'DELETE' });

        if (resposta.ok) {
            alert('Veículo excluído com sucesso!');
            carregarVeiculos();
        } else {
            alert('Erro ao excluir veículo.');
        }
    } catch (error) {
        console.error('Erro ao deletar:', error);
    }
}
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272
