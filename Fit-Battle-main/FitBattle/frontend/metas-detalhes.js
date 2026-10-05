let idMeta = null;
let metaAtual = null;

document.addEventListener('DOMContentLoaded', function () {
  const usuarioLogado = exigirLogin();
  if (!usuarioLogado) return;

  idMeta = new URLSearchParams(window.location.search).get('id');
  if (!idMeta) {
    window.location.href = 'metas.html';
    return;
  }

  document.getElementById('btnEditarMeta').addEventListener('click', editarMeta);
  document.getElementById('btnExcluirMeta').addEventListener('click', excluirMeta);

  carregarMeta();
});

async function carregarMeta() {
  try {
    const resposta = await api('/metas/' + idMeta);
    const meta = await resposta.json();
    if (!resposta.ok) {
      mostrarToast(meta.erro || 'Não foi possível carregar a meta.');
      window.location.href = 'metas.html';
      return;
    }
    metaAtual = meta;
    renderizar(meta);
  } catch (e) {
    mostrarToast('Não foi possível conectar à API.');
  }
}

function unidade(meta) {
  return meta.tipo_metrica === 'carga_maxima' ? 'kg' : 'treinos';
}

function renderizar(meta) {
  document.title = 'FitBattle - ' + meta.titulo;
  const un = unidade(meta);

  const tagsHtml = [
    `<span class="badge">${meta.tipo === 'curto_prazo' ? 'Curto Prazo' : 'Longo Prazo'}</span>`,
    `<span class="badge${meta.status === 'concluida' ? ' badge--sucesso' : ' badge--destaque'}">${meta.status === 'concluida' ? '✓ Concluída' : '● Em Andamento'}</span>`,
  ];
  if (meta.exercicio) tagsHtml.push(`<span class="badge">${esc(meta.exercicio)}</span>`);
  document.getElementById('metaTags').innerHTML = tagsHtml.join('');

  document.getElementById('metaTitulo').textContent = meta.titulo;
  document.getElementById('metaInfo').textContent =
    'Meta criada em ' + formatarData(meta.data_inicio) +
    (meta.data_final ? ' · Prazo limite: ' + formatarData(meta.data_final) : ' · Sem prazo definido');

  document.getElementById('statPartida').textContent = formatarNumero(meta.valor_partida) + ' ' + un;
  document.getElementById('statPartidaLegenda').textContent = formatarData(meta.data_inicio) + ' (Inicial)';

  document.getElementById('statAtualRotulo').textContent = meta.tipo_metrica === 'carga_maxima' ? 'Carga Atual' : 'Treinos Realizados';
  document.getElementById('statAtual').textContent = formatarNumero(meta.valor_atual) + ' ' + un;
  document.getElementById('statAtualLegenda').textContent = 'Calculado agora';

  document.getElementById('statObjetivo').textContent = formatarNumero(meta.valor_objetivo) + ' ' + un;
  document.getElementById('statObjetivoLegenda').textContent =
    meta.tipo_metrica === 'carga_maxima' ? meta.exercicio : 'Meta de frequência de treinos';

  document.getElementById('statFaltam').textContent =
    meta.status === 'concluida' ? '0 ' + un : formatarNumero(meta.faltam) + ' ' + un;
  document.getElementById('statPercentual').textContent = meta.percentual + '% concluído';

  document.getElementById('tituloProgresso').textContent =
    meta.tipo_metrica === 'carga_maxima' ? 'Progresso Geral da Carga' : 'Progresso Geral da Frequência';
  document.getElementById('progressoPercentualTexto').textContent = meta.percentual + '% concluído';
  document.getElementById('barraProgresso').style.width = meta.percentual + '%';
  document.getElementById('legendaInicio').textContent = formatarNumero(meta.valor_partida) + ' ' + un + ' (Inicial)';
  document.getElementById('legendaAtual').textContent = formatarNumero(meta.valor_atual) + ' ' + un + ' (Atual)';
  document.getElementById('legendaMeta').textContent = '🏁 ' + formatarNumero(meta.valor_objetivo) + ' ' + un + ' (Meta)';

  const progresso = meta.valor_atual - meta.valor_partida;
  document.getElementById('calloutProgresso').textContent = progresso > 0
    ? `+${formatarNumero(progresso)} ${un} progredidos desde a criação da meta em ${formatarData(meta.data_inicio)}.`
    : `Nenhum progresso registrado ainda desde a criação da meta em ${formatarData(meta.data_inicio)}.`;

  renderizarHistorico(meta);

  document.getElementById('infoMeta').innerHTML = `
    <div><dt>Tipo de Métrica</dt><dd>${meta.tipo_metrica === 'carga_maxima' ? 'Carga Máxima Individual' : 'Frequência de Treinos'}</dd></div>
    ${meta.exercicio ? `<div><dt>Exercício</dt><dd>${esc(meta.exercicio)}</dd></div>` : ''}
    <div><dt>Categoria</dt><dd>${meta.tipo === 'curto_prazo' ? 'Curto Prazo' : 'Longo Prazo'}</dd></div>
    <div><dt>Status</dt><dd>${meta.status === 'concluida' ? 'Concluída' : 'Ativa'}</dd></div>
    ${meta.dias_restantes != null ? `<div><dt>Dias Restantes</dt><dd>${meta.dias_restantes >= 0 ? meta.dias_restantes + ' dias' : 'Prazo encerrado'}</dd></div>` : ''}
  `;
}

function renderizarHistorico(meta) {
  const bloco = document.getElementById('blocoHistorico');
  const grade = bloco.closest('.grupos-grade');

  if (meta.tipo_metrica !== 'carga_maxima') {
    bloco.hidden = true;
    if (grade) grade.style.gridTemplateColumns = 'minmax(0, 1fr)';
    return;
  }
  bloco.hidden = false;
  if (grade) grade.style.gridTemplateColumns = '';

  document.getElementById('historicoLegenda').textContent =
    'Sessões de treino de ' + meta.exercicio + ' registradas no sistema que pontuaram para esta meta.';

  const lista = document.getElementById('listaHistorico');
  if (!meta.historico || meta.historico.length === 0) {
    lista.innerHTML = '<li class="estado-vazio">Nenhum treino deste exercício registrado ainda.</li>';
    return;
  }

  lista.innerHTML = meta.historico.map(function (item) {
    return `<li class="meta-historico-item">
      <div>
        <strong>${formatarNumero(item.carga_kg)} kg</strong>
        ${item.repeticoes != null ? `<span class="rotulo-mini"> (${item.repeticoes} repetições)</span>` : ''}
        <div class="meta-historico-item__texto">${formatarDataHora(item.data_registro)}</div>
      </div>
      <div class="meta-historico-item__tags">
        <span class="badge">${esc(item.rotulo)}</span>
        <span class="badge">Sessão #${item.sessao}</span>
      </div>
    </li>`;
  }).join('');
}

async function editarMeta() {
  const novoTitulo = window.prompt('Novo título da meta:', metaAtual.titulo);
  if (novoTitulo === null) return;
  const novoObjetivo = window.prompt('Novo valor objetivo (' + unidade(metaAtual) + '):', metaAtual.valor_objetivo);
  if (novoObjetivo === null) return;

  try {
    const resposta = await api('/metas/' + idMeta, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ titulo: novoTitulo.trim(), valor_objetivo: novoObjetivo })
    });
    const dados = await resposta.json();
    if (!resposta.ok) {
      mostrarToast(dados.erro || 'Não foi possível editar a meta.');
      return;
    }
    mostrarToast('Meta atualizada.');
    carregarMeta();
  } catch (e) {
    mostrarToast('Não foi possível conectar à API.');
  }
}

async function excluirMeta() {
  if (!window.confirm('Tem certeza que deseja excluir esta meta? Essa ação não pode ser desfeita.')) return;

  try {
    const resposta = await api('/metas/' + idMeta, { method: 'DELETE' });
    const dados = await resposta.json();
    if (!resposta.ok) {
      mostrarToast(dados.erro || 'Não foi possível excluir a meta.');
      return;
    }
    mostrarToast('Meta excluída.');
    window.location.href = 'metas.html';
  } catch (e) {
    mostrarToast('Não foi possível conectar à API.');
  }
}

function formatarData(iso) {
  if (!iso) return '—';
  return new Date(iso + (iso.length === 10 ? 'T00:00:00' : '')).toLocaleDateString('pt-BR');
}

function formatarDataHora(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('pt-BR') + ' · ' + new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function formatarNumero(n) {
  return Number(n).toString().replace('.', ',');
}

function esc(s) {
  const div = document.createElement('div');
  div.textContent = s == null ? '' : s;
  return div.innerHTML;
}
