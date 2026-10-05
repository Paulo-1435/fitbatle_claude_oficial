const PADRAO_EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const ATRASO_REDIRECIONAR_MS = 700;

document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('loginForm');
  const identificador = document.getElementById('email');
  const senha = document.getElementById('senha');
  const lembrar = document.getElementById('lembrar');
  const mensagem = document.getElementById('errorMessage');
  const botao = document.getElementById('btnEntrar');
  const rotuloBotao = botao.querySelector('span');

  limparErroAoEditar(form, mensagem);

  function erro(texto, campo) {
    mostrarMensagemForm(mensagem, texto, false);
    if (campo) campo.focus();
  }

  form.addEventListener('submit', async function (evento) {
    evento.preventDefault();
    mostrarMensagemForm(mensagem, '', false);

    const valor = identificador.value.trim();
    if (valor.charAt(0) === '@' || (valor !== '' && valor.indexOf('@') === -1)) {
      return erro('O login por @usuário ainda não está disponível. Use o seu e-mail.', identificador);
    }
    if (!PADRAO_EMAIL.test(valor)) {
      return erro('Informe um e-mail válido.', identificador);
    }
    if (senha.value === '') {
      return erro('Informe sua senha.', senha);
    }

    botao.disabled = true;
    rotuloBotao.textContent = 'Entrando...';

    try {
      const resposta = await fetch(API_URL + '/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: valor, senha: senha.value })
      });
      const dados = await resposta.json().catch(function () { return {}; });

      if (!resposta.ok) {
        return erro(dados.erro || 'Não foi possível entrar.');
      }

      salvarSessao(dados.token, dados.usuario, lembrar.checked);
      mostrarMensagemForm(mensagem, 'Bem-vindo, ' + dados.usuario.nome + '! Redirecionando...', true);
      setTimeout(function () { window.location.href = PAGINA_INICIAL; }, ATRASO_REDIRECIONAR_MS);
    } catch (e) {
      erro('Não foi possível conectar à API. Verifique se o backend está rodando (python app.py).');
    } finally {
      botao.disabled = false;
      rotuloBotao.textContent = 'Entrar no FitBattle';
    }
  });
});
