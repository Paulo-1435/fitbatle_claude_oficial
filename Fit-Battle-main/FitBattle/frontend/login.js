// URL base da API Flask
const API_URL = 'http://localhost:5000/api';

document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('loginForm');
  const email = document.getElementById('email');
  const senha = document.getElementById('senha');
  const errorMessage = document.getElementById('errorMessage');
  const botao = form.querySelector('.btn-cadastrar');

  form.addEventListener('submit', async function (event) {
    event.preventDefault();
    limparMensagem();

    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailPattern.test(email.value.trim())) {
      return mostrarErro('Informe um email válido.', email);
    }
    if (senha.value === '') {
      return mostrarErro('Informe sua senha.', senha);
    }

    botao.disabled = true;
    botao.textContent = 'ENTRANDO...';

    try {
      const resposta = await fetch(`${API_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.value.trim(),
          senha: senha.value
        })
      });

      const dados = await resposta.json();

      if (!resposta.ok) {
        mostrarErro(dados.erro || 'Não foi possível entrar.');
        return;
      }

      // guarda o usuário logado para as outras telas usarem
      try {
        localStorage.setItem('fitbattle_usuario', JSON.stringify(dados.usuario));
      } catch (e) { /* ignora se o navegador bloquear storage */ }

      mostrarSucesso(`Bem-vindo, ${dados.usuario.nome}! Redirecionando...`);
      setTimeout(function () { window.location.href = 'perfil.html'; }, 900);
    } catch (erro) {
      mostrarErro('Não foi possível conectar à API. Verifique se o backend está rodando (python app.py).');
    } finally {
      botao.disabled = false;
      botao.textContent = 'ENTRAR';
    }
  });

  function limparMensagem() {
    errorMessage.textContent = '';
    errorMessage.style.color = '';
  }

  function mostrarErro(mensagem, campo) {
    errorMessage.style.color = '';
    errorMessage.textContent = mensagem;
    if (campo) campo.focus();
  }

  function mostrarSucesso(mensagem) {
    errorMessage.style.color = '#2ecc71';
    errorMessage.textContent = mensagem;
  }
});
