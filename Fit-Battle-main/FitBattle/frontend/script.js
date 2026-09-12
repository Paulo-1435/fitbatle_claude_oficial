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

  const responsavelBox = document.getElementById('responsavelBox');
  const responsavelNome = document.getElementById('responsavelNome');
  const responsavelEmail = document.getElementById('responsavelEmail');
  const autorizacaoResponsavel = document.getElementById('autorizacaoResponsavel');

  const overlayTermo = document.getElementById('overlayTermo');
  const painelConsentimento = document.getElementById('painelConsentimento');
  const painelLeitura = document.getElementById('painelLeitura');
  const closeTermo = document.getElementById('closeTermo');
  const linkLerTermoCompleto = document.getElementById('linkLerTermoCompleto');
  const btnVoltarConsentimento = document.getElementById('btnVoltarConsentimento');
  const btnCancelarTermo = document.getElementById('btnCancelarTermo');
  const btnConfirmarCadastro = document.getElementById('btnConfirmarCadastro');
  const erroModalTermo = document.getElementById('erroModalTermo');
  const iframeTermo = document.getElementById('iframeTermo');

  let dadosCadastroPendente = null;

  function atualizarResponsavel() {
    const n = Number(idade.value);
    const menor = idade.value !== '' && n >= 13 && n < 18;
    responsavelBox.hidden = !menor;
  }
  idade.addEventListener('input', atualizarResponsavel);
  atualizarResponsavel();

  function abrirModalConsentimento() {
    painelLeitura.hidden = true;
    painelConsentimento.hidden = false;
    erroModalTermo.textContent = '';
    overlayTermo.classList.add('aberto');
  }

  function abrirModalLeitura(ancora, vindoDoConsentimento) {
    iframeTermo.src = 'termos.html#' + ancora;
    painelConsentimento.hidden = true;
    painelLeitura.hidden = false;
    btnVoltarConsentimento.hidden = !vindoDoConsentimento;
    overlayTermo.classList.add('aberto');
  }

  function fecharModalTermo() {
    overlayTermo.classList.remove('aberto');
    dadosCadastroPendente = null;
  }

  document.querySelectorAll('[data-abrir-termo]').forEach(function (link) {
    link.addEventListener('click', function (event) {
      event.preventDefault();
      abrirModalLeitura(link.getAttribute('data-abrir-termo'), false);
    });
  });

  linkLerTermoCompleto.addEventListener('click', function (event) {
    event.preventDefault();
    abrirModalLeitura('termo-uso', true);
  });

  btnVoltarConsentimento.addEventListener('click', function () {
    painelLeitura.hidden = true;
    painelConsentimento.hidden = false;
  });

  closeTermo.addEventListener('click', fecharModalTermo);
  btnCancelarTermo.addEventListener('click', fecharModalTermo);

  overlayTermo.addEventListener('click', function (event) {
    if (event.target === overlayTermo) fecharModalTermo();
  });

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    limparMensagem();

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

    dadosCadastroPendente = {
      nome: usuario.value.trim(),
      email: email.value.trim(),
      idade: idadeNum,
      senha: senha.value,
      responsavel: responsavel
    };

    abrirModalConsentimento();
  });

  btnConfirmarCadastro.addEventListener('click', async function () {
    if (!dadosCadastroPendente) return;

    if (!aceiteTermos.checked) {
      erroModalTermo.textContent = 'Você precisa ler e aceitar o Termo de Uso e o Termo de Consentimento.';
      return;
    }

    const consentimentos = {};
    document.querySelectorAll('input[name="consent"]').forEach(function (cb) {
      consentimentos[cb.value] = cb.checked;
    });

    btnConfirmarCadastro.disabled = true;
    btnConfirmarCadastro.textContent = 'ENVIANDO...';
    erroModalTermo.textContent = '';

    try {
      const resposta = await fetch(`${API_URL}/usuarios`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nome: dadosCadastroPendente.nome,
          email: dadosCadastroPendente.email,
          idade: dadosCadastroPendente.idade,
          senha: dadosCadastroPendente.senha,
          aceite_termos: true,
          consentimentos: consentimentos,
          responsavel: dadosCadastroPendente.responsavel,
          autorizacao_responsavel: dadosCadastroPendente.responsavel !== null
        })
      });

      const dados = await resposta.json();

      if (!resposta.ok) {
        erroModalTermo.textContent = dados.erro || 'Não foi possível concluir o cadastro.';
        return;
      }

      fecharModalTermo();
      mostrarSucesso((dados.mensagem || 'Cadastro realizado com sucesso!') + ' Redirecionando para o login...');
      form.reset();
      atualizarResponsavel();
      setTimeout(function () { window.location.href = 'login.html'; }, 1500);
    } catch (erro) {
      erroModalTermo.textContent = 'Não foi possível conectar à API. Verifique se o backend está rodando (python app.py).';
    } finally {
      btnConfirmarCadastro.disabled = false;
      btnConfirmarCadastro.textContent = 'Confirmar cadastro';
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
