if (obterToken() && obterUsuario()) location.href = "index.html";

const form = document.getElementById("form-login");
const caixaErro = document.getElementById("erro");

form.addEventListener("submit", async ev => {
    ev.preventDefault();
    caixaErro.hidden = true;
    const botao = document.getElementById("btn-entrar");
    botao.disabled = true;
    try {
        const r = await api("/auth/login", {
            metodo: "POST",
            corpo: { login: document.getElementById("login").value.trim(), senha: document.getElementById("senha").value },
        });
        salvarSessao(r.access_token, r.usuario);
        location.href = "index.html";
    } catch (e) {
        caixaErro.textContent = e.message;
        caixaErro.hidden = false;
        botao.disabled = false;
    }
});
