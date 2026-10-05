document.addEventListener('DOMContentLoaded', function () {
  const usuarioLogado = exigirLogin();
  if (!usuarioLogado) return;

  document.body.addEventListener('click', function (evento) {
    const alvo = evento.target.closest('[data-em-breve]');
    if (!alvo) return;
    mostrarToast(alvo.getAttribute('data-em-breve') + ' estará disponível em breve.');
  });
});
