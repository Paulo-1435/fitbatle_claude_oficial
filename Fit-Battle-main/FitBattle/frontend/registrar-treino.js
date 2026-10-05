const BONUS_MUSCULACAO = 20;
const PONTOS_MINIMOS = 10;

let usuarioLogado = null;
let passoAtual = 1;
let exercicioSelecionado = null;
let pesoAtual = 40;
let repeticoesAtual = 6;
let duracaoAtual = 40;
const recordesPorExercicio = {};

document.addEventListener('DOMContentLoaded', function () {
  usuarioLogado = exigirLogin();
  if (!usuarioLogado) return;

  ligarAvisosEmBreve();
  configurarExercicios();
  configurarPeso();
  configurarContadores();
  configurarNavegacao();
  configurarSubmissao();

  atualizarPeso();
  atualizarRecompensaEstimada();
  carregarHistoricoDoUsuario();
});

function ligarAvisosEmBreve() {
  document.body.addEventListener('click', function (evento) {
    const alvo = evento.target.closest('[data-em-breve]');
    if (!alvo) return;
    mostrarToast(alvo.getAttribute('data-em-breve') + ' estará disponível em breve.');
  });
}

async function carregarHistoricoDoUsuario() {
  try {
    const resposta = await api(`/usuarios/${usuarioLogado.id}/atividades`);
    if (!resposta.ok) return;
    const treinos = await resposta.json();
    treinos.forEach(function (treino) {
      if (treino.tipo !== 'musculacao' || !treino.titulo || treino.carga_kg == null) return;
      const chave = treino.titulo.trim().toLowerCase();
      if (recordesPorExercicio[chave] == null || treino.carga_kg > recordesPorExercicio[chave]) {
        recordesPorExercicio[chave] = treino.carga_kg;
      }
    });
    atualizarPainelRecorde();
  } catch (e) {}
}

function configurarExercicios() {
  document.querySelectorAll('.rt-exercicio').forEach(function (botao) {
    botao.addEventListener('click', function () { selecionarExercicio(botao); });
  });

  document.getElementById('exercicioCustom').addEventListener('input', function () {
    exercicioSelecionado = this.value.trim();
    atualizarPainelRecorde();
  });
}

function selecionarExercicio(botao) {
  document.querySelectorAll('.rt-exercicio').forEach(function (b) { b.classList.remove('rt-exercicio--ativa'); });
  botao.classList.add('rt-exercicio--ativa');

  const valor = botao.getAttribute('data-exercicio');
  const campoOutro = document.getElementById('campoOutroExercicio');

  if (valor === '') {
    campoOutro.hidden = false;
    const custom = document.getElementById('exercicioCustom');
    custom.focus();
    exercicioSelecionado = custom.value.trim();
  } else {
    campoOutro.hidden = true;
    exercicioSelecionado = valor;
  }

  document.getElementById('erroEtapa1').textContent = '';
  atualizarPainelRecorde();
}

function configurarPeso() {
  document.querySelectorAll('[data-ajuste]').forEach(function (botao) {
    botao.addEventListener('click', function () {
      const delta = parseInt(botao.getAttribute('data-ajuste'), 10);
      pesoAtual = Math.max(0, pesoAtual + delta);
      atualizarPeso();
    });
  });
}

function atualizarPeso() {
  document.getElementById('pesoValor').textContent = formatarNumero(pesoAtual);
  atualizarRecompensaEstimada();
  atualizarPainelRecorde();
}

function configurarContadores() {
  document.querySelectorAll('[data-contador]').forEach(function (botao) {
    botao.addEventListener('click', function () {
      const alvo = botao.getAttribute('data-contador');
      const delta = parseInt(botao.getAttribute('data-delta'), 10);
      if (alvo === 'repeticoes') {
        repeticoesAtual = Math.max(1, repeticoesAtual + delta);
        document.getElementById('repeticoesValor').textContent = repeticoesAtual;
      } else {
        duracaoAtual = Math.max(5, duracaoAtual + delta);
        document.getElementById('duracaoValor').textContent = duracaoAtual;
      }
      atualizarRecompensaEstimada();
    });
  });
}

function atualizarPainelRecorde() {
  const painel = document.getElementById('painelRecorde');
  const texto = document.getElementById('textoRecorde');
  const lateralRecorde = document.getElementById('lateralRecordeAtual');
  const lateralCarga = document.getElementById('lateralCargaAtual');

  lateralCarga.textContent = formatarNumero(pesoAtual) + ' kg';

  if (!exercicioSelecionado) {
    texto.textContent = 'Selecione um exercício para ver seu recorde pessoal.';
    painel.classList.remove('rt-recorde--pr');
    lateralRecorde.textContent = '—';
    return;
  }

  const recordeAnterior = recordesPorExercicio[exercicioSelecionado.toLowerCase()];
  lateralRecorde.textContent = recordeAnterior != null ? formatarNumero(recordeAnterior) + ' kg' : 'Ainda sem registro';

  if (recordeAnterior == null) {
    texto.textContent = 'Primeira vez registrando ' + exercicioSelecionado + '! Isso já vira seu recorde pessoal.';
    painel.classList.add('rt-recorde--pr');
  } else if (pesoAtual > recordeAnterior) {
    texto.textContent = 'Novo recorde pessoal! Seu anterior em ' + exercicioSelecionado + ' era ' + formatarNumero(recordeAnterior) + ' kg.';
    painel.classList.add('rt-recorde--pr');
  } else {
    texto.textContent = 'Seu recorde em ' + exercicioSelecionado + ' é ' + formatarNumero(recordeAnterior) + ' kg.';
    painel.classList.remove('rt-recorde--pr');
  }
}

function calcularPontosEstimados() {
  const pontos = duracaoAtual * 1 + (pesoAtual * repeticoesAtual) / 100 + BONUS_MUSCULACAO;
  return Math.max(PONTOS_MINIMOS, Math.round(pontos));
}

function atualizarRecompensaEstimada() {
  document.getElementById('recompensaEstimada').textContent = '≈ +' + calcularPontosEstimados() + ' xp';
}

function ehNovoRecorde() {
  if (!exercicioSelecionado) return false;
  const recordeAnterior = recordesPorExercicio[exercicioSelecionado.toLowerCase()];
  return recordeAnterior == null || pesoAtual > recordeAnterior;
}

function configurarNavegacao() {
  document.getElementById('btnProximo').addEventListener('click', avancar);
  document.getElementById('btnVoltar').addEventListener('click', function () { irParaPasso(passoAtual - 1); });
}

function avancar() {
  if (passoAtual === 1) {
    if (!exercicioSelecionado) {
      document.getElementById('erroEtapa1').textContent = 'Escolha um exercício ou digite o nome dele.';
      return;
    }
  }
  if (passoAtual === 2) {
    if (!pesoAtual || pesoAtual <= 0) {
      document.getElementById('erroEtapa2').textContent = 'Informe a carga levantada.';
      return;
    }
    if (!duracaoAtual || duracaoAtual <= 0) {
      document.getElementById('erroEtapa2').textContent = 'Informe a duração do treino.';
      return;
    }
    document.getElementById('erroEtapa2').textContent = '';
    preencherResumo();
  }
  irParaPasso(passoAtual + 1);
}

function preencherResumo() {
  document.getElementById('resumoExercicio').textContent = exercicioSelecionado || '—';
  document.getElementById('resumoCarga').textContent = formatarNumero(pesoAtual) + ' kg';
  document.getElementById('resumoReps').textContent = repeticoesAtual;
  document.getElementById('resumoDuracao').textContent = duracaoAtual + ' min';

  const pontos = calcularPontosEstimados();
  const recorde = ehNovoRecorde();
  document.getElementById('textoBotaoSalvar').textContent =
    'Salvar e Compartilhar Treino (+' + pontos + ' Pontos)' + (recorde ? ' 🏆' : '');
}

function irParaPasso(numero) {
  passoAtual = numero;

  ['etapa1', 'etapa2', 'etapa3'].forEach(function (id, indice) {
    document.getElementById(id).classList.toggle('rt-etapa--visivel', indice + 1 === numero);
  });

  [1, 2, 3].forEach(function (n) {
    const indicador = document.getElementById('indicadorPasso' + n);
    indicador.classList.toggle('rt-passo--ativo', n === numero);
    indicador.classList.toggle('rt-passo--feito', n < numero);
  });

  document.getElementById('btnVoltar').hidden = numero === 1;
  document.getElementById('btnProximo').hidden = numero === 3;
  document.getElementById('btnSalvar').hidden = numero !== 3;

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function configurarSubmissao() {
  document.getElementById('formRegistrarTreino').addEventListener('submit', async function (evento) {
    evento.preventDefault();

    const erro = document.getElementById('erroEtapa3');
    erro.textContent = '';
    const botao = document.getElementById('btnSalvar');
    botao.disabled = true;

    const recorde = ehNovoRecorde();
    let descricao = document.getElementById('treinoDescricao').value.trim();
    if (recorde) descricao = ('🏆 Novo recorde pessoal! ' + descricao).trim();

    const corpo = {
      tipo: 'musculacao',
      titulo: exercicioSelecionado,
      descricao: descricao,
      tempo_min: duracaoAtual,
      carga_kg: pesoAtual,
      repeticoes: repeticoesAtual,
      distancia_km: null
    };

    try {
      const resposta = await api(`/usuarios/${usuarioLogado.id}/atividades`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corpo)
      });
      const dados = await resposta.json();
      if (!resposta.ok) {
        erro.textContent = dados.erro || 'Não foi possível registrar o treino.';
        return;
      }

      const textoCompartilhar = 'Registrei ' + formatarNumero(pesoAtual) + 'kg no ' + exercicioSelecionado + ' no FitBattle! 💪 #FitBattle';
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(textoCompartilhar).catch(function () {});
      }

      mostrarToast(
        'Treino registrado! +' + dados.pontuacao_ganha + ' xp' +
        (recorde ? ' 🏆 Novo recorde pessoal!' : '') +
        ' Texto para compartilhar copiado.'
      );
      setTimeout(function () { window.location.href = 'feed.html'; }, 1400);
    } catch (e) {
      erro.textContent = 'Não foi possível conectar à API.';
    } finally {
      botao.disabled = false;
    }
  });
}

function formatarNumero(n) {
  return Number(n).toString().replace('.', ',');
}
