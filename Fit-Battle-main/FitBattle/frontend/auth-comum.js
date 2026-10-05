function ligarSenhasVisiveis() {
  document.querySelectorAll('[data-alternar-senha]').forEach(function (botao) {
    const campo = document.getElementById(botao.getAttribute('data-alternar-senha'));
    if (!campo) return;
    botao.addEventListener('click', function () {
      const mostrar = campo.type === 'password';
      campo.type = mostrar ? 'text' : 'password';
      botao.setAttribute('aria-pressed', mostrar ? 'true' : 'false');
      botao.setAttribute('aria-label', mostrar ? 'Ocultar senha' : 'Mostrar senha');
    });
  });
}

function ligarAvisosEmBreve() {
  document.querySelectorAll('[data-em-breve]').forEach(function (elemento) {
    elemento.addEventListener('click', function (evento) {
      evento.preventDefault();
      mostrarToast(elemento.getAttribute('data-em-breve') + ' estará disponível em breve.');
    });
  });
}

function limparErroAoEditar(form, mensagem) {
  form.addEventListener('input', function () {
    if (!mensagem.classList.contains('mensagem-form--ok')) mostrarMensagemForm(mensagem, '', false);
  });
}

function mostrarMensagemForm(elemento, texto, sucesso) {
  elemento.textContent = texto;
  elemento.classList.toggle('mensagem-form--ok', !!sucesso);
}

document.addEventListener('DOMContentLoaded', function () {
  ligarSenhasVisiveis();
  ligarAvisosEmBreve();
});
