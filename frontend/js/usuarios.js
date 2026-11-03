const usuario = iniciarPagina({ pagina: "usuarios", titulo: "Usuários", apenasAdmin: true });
const $ = id => document.getElementById(id);
const tbody = $("tbody");
let editando = null;   // id do usuário em edição

async function carregar() {
    try {
        const lista = await api("/usuarios/");
        tbody.innerHTML = lista.map(u => `<tr data-id="${u.id}">
            <td>${esc(u.nome)}</td><td>${esc(u.login)}</td>
            <td><span class="selo ${u.perfil === "Administrador" ? "mensalista" : ""}">${esc(u.perfil)}</span></td>
            <td class="acoes-celula"><button class="btn sec pequeno" data-editar="${u.id}" ${dica("Alterar nome, login, perfil, senha ou código de liberação")}>Editar</button>
            ${u.id !== usuario.id ? `<button class="btn perigo pequeno" data-excluir="${u.id}" data-nome="${esc(u.nome)}" ${dica("Apagar o usuário (não dá para excluir a si mesmo)")}>Excluir</button>` : ""}</td></tr>`).join("");
        tbody.dataset.usuarios = JSON.stringify(Object.fromEntries(lista.map(u => [u.id, u])));
    } catch (e) { erroAviso(e); }
}

function modoEdicao(u) {
    editando = u ? u.id : null;
    $("titulo-form").textContent = u ? `Editar usuário: ${u.nome}` : "Novo usuário";
    $("u-nome").value = u ? u.nome : "";
    $("u-login").value = u ? u.login : "";
    $("u-perfil").value = u ? u.perfil : "Operador";
    $("u-senha").value = "";
    $("u-senha").required = !u;
    $("u-codigo").value = "";
    $("rot-codigo").textContent = u ? "Novo código de liberação (deixe em branco para manter)" : "Código de liberação (PIN de 4 a 20 caracteres)";
    mostrarCampoCodigo();
    $("rot-senha").textContent = u ? "Nova senha (deixe em branco para manter)" : "Senha";
    $("campo-cancelar").hidden = !u;
    $("u-nome").focus();
}

tbody.addEventListener("click", async ev => {
    const ed = ev.target.closest("[data-editar]"), ex = ev.target.closest("[data-excluir]");
    if (ed) { modoEdicao(JSON.parse(tbody.dataset.usuarios)[ed.dataset.editar]); return; }
    if (ex && await confirmar(`Excluir o usuário ${ex.dataset.nome}?`, { titulo: "Excluir usuário", sim: "Excluir", perigo: true })) {
        try { await api(`/usuarios/${ex.dataset.excluir}`, { metodo: "DELETE" }); aviso("Usuário excluído."); carregar(); }
        catch (e) { erroAviso(e); }
    }
});

$("btn-cancelar").addEventListener("click", () => modoEdicao(null));

/* o código de liberação só existe para administradores */
function mostrarCampoCodigo() { $("campo-codigo").hidden = $("u-perfil").value !== "Administrador"; }
$("u-perfil").addEventListener("change", mostrarCampoCodigo);

$("form-usuario").addEventListener("submit", async ev => {
    ev.preventDefault();
    const corpo = { nome: $("u-nome").value.trim(), login: $("u-login").value.trim(), perfil: $("u-perfil").value };
    if ($("u-senha").value) corpo.senha = $("u-senha").value;
    if ($("u-codigo").value && corpo.perfil === "Administrador") corpo.codigo_liberacao = $("u-codigo").value;
    try {
        if (editando) await api(`/usuarios/${editando}`, { metodo: "PUT", corpo });
        else await api("/usuarios/", { metodo: "POST", corpo });
        aviso("Usuário salvo.");
        modoEdicao(null);
        carregar();
    } catch (e) { erroAviso(e); }
});

if (usuario) carregar();
