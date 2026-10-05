let tipoMetricaAtual = 'carga_maxima';
let prazoAtual = 'curto_prazo';

document.addEventListener('DOMContentLoaded', function () {
  const usuarioLogado = exigirLogin();
  if (!usuarioLogado) return;

  document.getElementById('dataFinal').min = new Date().toISOString().slice(0, 10);

  document.getElementById('tipoMetrica').addEventListener('change', function () {
    tipoMetricaAtual = this.value;
    atualizarCamposPorTipo();
  });

  document.querySelectorAll('#abasPrazo [data-prazo]').forEach(function (botao) {
    botao.addEventListener('click', function () {
      prazoAtual = botao.getAttribute('data-prazo');
      document.querySelectorAll('#abasPrazo [data-prazo]').forEach(function (b) {
        b.classList.toggle('aba--ativa', b === botao);
      });
    });
  });

  document.getElementById('formCriarMeta').addEventListener('submit', enviarFormulario);

  atualizarCamposPorTipo();
});

function atualizarCamposPorTipo() {
  const carga = tipoMetricaAtual === 'carga_maxima';
  document.getElementById('campoExercicio').hidden = !carga;
  document.getElementById('exercicioMeta').required = carga;
  document.getElementById('unidadeObjetivo').textContent = carga ? 'kg' : 'treinos';
  document.getElementById('unidadePartida').textContent = carga ? 'kg' : 'treinos';
}

async function enviarFormulario(evento) {
  evento.preventDefault();
  const erro = document.getElementById('erroCriarMeta');
  erro.textContent = '';
  const botao = document.getElementById('btnSalvarMeta');
  botao.disabled = true;

  const corpo = {
    titulo: document.getElementById('tituloMeta').value.trim(),
    tipo: prazoAtual,
    tipo_metrica: tipoMetricaAtual,
    exercicio: tipoMetricaAtual === 'carga_maxima' ? document.getElementById('exercicioMeta').value.trim() : null,
    valor_objetivo: document.getElementById('valorObjetivo').value,
    valor_partida: document.getElementById('valorPartida').value || null,
    data_final: document.getElementById('dataFinal').value || null
  };

  try {
    const resposta = await api('/metas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(corpo)
    });
    const dados = await resposta.json();
    if (!resposta.ok) {
      erro.textContent = dados.erro || 'Não foi possível criar a meta.';
      return;
    }
    mostrarToast('Meta criada!');
    window.location.href = 'metas-detalhes.html?id=' + dados.meta.id;
  } catch (e) {
    erro.textContent = 'Não foi possível conectar à API.';
  } finally {
    botao.disabled = false;
  }
}
