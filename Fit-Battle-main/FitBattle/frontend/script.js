// URL base da API Flask (backend/app.py roda na porta 5000)
const API_URL = 'http://localhost:5000/api';

document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('registerForm');
  const usuario = document.getElementById('usuario');
  const email = document.getElementById('email');
  const idade = document.getElementById('idade');
  const senha = document.getElementById('senha');
  const confirmaSenha = document.getElementById('confirmaSenha');
  const aceiteTermos = document.getElementById('aceiteTermos');
  const errorMessage = document.getElementById('errorMessage');
  const botao = form.querySelector('.btn-cadastrar');

  // Campos do responsável legal (aparecem só para 13 a 17 anos)
  const responsavelBox = document.getElementById('responsavelBox');
  const responsavelNome = document.getElementById('responsavelNome');
  const responsavelEmail = document.getElementById('responsavelEmail');
  const autorizacaoResponsavel = document.getElementById('autorizacaoResponsavel');

  function atualizarResponsavel() {
    const n = Number(idade.value);
    const menor = idade.value !== '' && n >= 13 && n < 18;
    responsavelBox.hidden = !menor;
  }
  idade.addEventListener('input', atualizarResponsavel);
  atualizarResponsavel();

  form.addEventListener('submit', async function (event) {
    event.preventDefault();
    limparMensagem();

    // ---------- Validações no navegador ----------
    if (usuario.value.trim().length < 3) {
      return mostrarErro('Informe um nome com pelo menos 3 caracteres.', usuario);
    }

    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailPattern.test(email.value.trim())) {
      return mostrarErro('Por favor, informe um email válido.', email);
    }

    const idadeNum = Number(idade.value);
    if (!idade.value || idadeNum < 1 || idadeNum > 120) {
      return mostrarErro('Informe uma idade válida (1 a 120).', idade);
    }

    if (idadeNum < 13) {
      return mostrarErro('O cadastro não é permitido para menores de 13 anos (art. 14 da LGPD).', idade);
    }

    // Autorização do responsável legal para 13 a 17 anos
    let responsavel = null;
    if (idadeNum >= 13 && idadeNum < 18) {
      if (responsavelNome.value.trim().length < 3) {
        return mostrarErro('Informe o nome completo do responsável legal.', responsavelNome);
      }
      if (!emailPattern.test(responsavelEmail.value.trim())) {
        return mostrarErro('Informe um e-mail válido do responsável legal.', responsavelEmail);
      }
      if (!autorizacaoResponsavel.checked) {
        return mostrarErro('É necessária a autorização do responsável legal.', autorizacaoResponsavel);
      }
      responsavel = {
        nome: responsavelNome.value.trim(),
        email: responsavelEmail.value.trim()
      };
    }

    if (senha.value.length < 8) {
      return mostrarErro('A senha deve ter no mínimo 8 caracteres.', senha);
    }

    if (senha.value !== confirmaSenha.value) {
      return mostrarErro('As senhas não coincidem.', confirmaSenha);
    }

    if (!aceiteTermos.checked) {
      return mostrarErro('Você precisa ler e aceitar o Termo de Uso e o Termo de Consentimento.', aceiteTermos);
    }

    // Consentimentos opcionais que ficaram marcados na caixa
    const consentimentos = {};
    document.querySelectorAll('input[name="consent"]').forEach(function (cb) {
      consentimentos[cb.value] = cb.checked;
    });

    // ---------- Envio para o backend ----------
    botao.disabled = true;
    botao.textContent = 'ENVIANDO...';
    let sucesso = false;

    try {
      const resposta = await fetch(`${API_URL}/usuarios`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nome: usuario.value.trim(),
          email: email.value.trim(),
          idade: idadeNum,
          senha: senha.value,
          aceite_termos: true,
          consentimentos: consentimentos,
          responsavel: responsavel,
          autorizacao_responsavel: responsavel !== null
        })
      });

      const dados = await resposta.json();

      if (!resposta.ok) {
        mostrarErro(dados.erro || 'Não foi possível concluir o cadastro.');
        return;
      }

      sucesso = true;
      mostrarSucesso((dados.mensagem || 'Cadastro realizado com sucesso!') + ' Redirecionando para o login...');
      form.reset();
      atualizarResponsavel();
      botao.textContent = 'REDIRECIONANDO...';
      setTimeout(function () { window.location.href = 'login.html'; }, 1500);
    } catch (erro) {
      mostrarErro('Não foi possível conectar à API. Verifique se o backend está rodando (python app.py).');
    } finally {
      if (!sucesso) {
        botao.disabled = false;
        botao.textContent = 'CADASTRE-SE';
      }
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
