let usuarioLogado = null;
let todasAsMetas = [];
let abaAtual = 'em_andamento';

document.addEventListener('DOMContentLoaded', function () {
  usuarioLogado = exigirLogin();
  if (!usuarioLogado) return;

  document.getElementById('btnCriarMeta').addEventListener('click', function () {
    window.location.href = 'metas-criar.html';
  });
  document.getElementById('btnCriarPrimeiraMeta').addEventListener('click', function () {
    window.location.href = 'metas-criar.html';
  });
  document.getElementById('abaEmAndamento').addEventListener('click', function () { selecionarAba('em_andamento'); });
  document.getElementById('abaConcluidas').addEventListener('click', function () { selecionarAba('concluida'); });

  carregarMetas();
});

async function carregarMetas() {
  const grade = document.getElementById('metasGrade');
  grade.innerHTML = '<p class="estado-vazio">Carregando suas metas...</p>';

  try {
    const resposta = await api('/metas');
    const metas = await resposta.json();
    if (!resposta.ok) {
      grade.innerHTML = '<p class="estado-vazio">Não foi possível carregar suas metas.</p>';
      return;
    }
    todasAsMetas = metas;
    atualizarResumo();
    renderizarAba();
    renderizarRecentes();
  } catch (e) {
    grade.innerHTML = '<p class="estado-vazio">Não foi possível conectar à API.</p>';
  }
}

function atualizarResumo() {
  const ativas = todasAsMetas.filter(function (m) { return m.status === 'em_andamento'; });
  const concluidas = todasAsMetas.filter(function (m) { return m.status === 'concluida'; });
  const curtas = ativas.filter(function (m) { return m.tipo === 'curto_prazo'; }).length;
  const longas = ativas.length - curtas;

  document.getElementById('totalAtivas').textContent = ativas.length;
  document.getElementById('detalheAtivas').textContent =
    ativas.length ? curtas + ' curto prazo · ' + longas + ' longo prazo' : 'Nenhuma meta em andamento';
  document.getElementById('contadorEmAndamento').textContent = ativas.length;

  document.getElementById('totalConcluidas').textContent = concluidas.length;
  document.getElementById('contadorConcluidasAba').textContent = concluidas.length;
  if (concluidas.length) {
    const ultima = concluidas.slice().sort(function (a, b) {
      return new Date(b.concluida_em) - new Date(a.concluida_em);
    })[0];
    document.getElementById('detalheConcluidas').textContent = 'Última em ' + formatarData(ultima.concluida_em);
  } else {
    document.getElementById('detalheConcluidas').textContent = 'Nenhuma meta concluída ainda';
  }
}

function selecionarAba(aba) {
  abaAtual = aba;
  document.getElementById('abaEmAndamento').classList.toggle('aba--ativa', aba === 'em_andamento');
  document.getElementById('abaConcluidas').classList.toggle('aba--ativa', aba === 'concluida');
  renderizarAba();
}

function renderizarAba() {
  const grade = document.getElementById('metasGrade');
  const vazio = document.getElementById('estadoVazioMetas');
  const filtradas = todasAsMetas.filter(function (m) { return m.status === abaAtual; });

  if (todasAsMetas.length === 0) {
    grade.hidden = true;
    vazio.hidden = false;
    return;
  }
  vazio.hidden = true;
  grade.hidden = false;

  if (filtradas.length === 0) {
    grade.innerHTML = '<p class="estado-vazio">' +
      (abaAtual === 'em_andamento' ? 'Nenhuma meta em andamento.' : 'Nenhuma meta concluída ainda.') +
      '</p>';
    return;
  }

  grade.innerHTML = filtradas.map(htmlCartaoMeta).join('');
}

function unidade(meta) {
  return meta.tipo_metrica === 'carga_maxima' ? 'kg' : 'treinos';
}

function htmlCartaoMeta(meta) {
  const un = unidade(meta);
  const tipoLabel = meta.tipo === 'curto_prazo' ? 'Curto Prazo' : 'Longo Prazo';
  const metricaLabel = meta.tipo_metrica === 'carga_maxima' ? 'Carga Máxima' : 'Frequência';
  const prazo = meta.data_final ? 'Prazo: ' + formatarData(meta.data_final) : 'Sem prazo definido';

  return `<article class="card meta-cartao">
    <div class="meta-cartao__tags">
      <span class="badge">${esc(tipoLabel)}</span>
      <span class="meta-cartao__exercicio">${esc(metricaLabel)}</span>
    </div>
    ${meta.exercicio ? `<span class="rotulo-mini">${esc(meta.exercicio.toUpperCase())}</span>` : ''}
    <div class="meta-cartao__titulo">${esc(meta.titulo)}</div>
    <div class="meta-cartao__linha">
      <span class="rotulo-mini">Atual</span>
      <span class="rotulo-mini">Objetivo</span>
    </div>
    <div class="meta-cartao__linha">
      <strong>${formatarNumero(meta.valor_atual)} ${un}</strong>
      <strong>${formatarNumero(meta.valor_objetivo)} ${un}</strong>
    </div>
    <div class="barra"><div class="barra__preenchimento" style="width:${meta.percentual}%"></div></div>
    <div class="meta-cartao__progresso-topo">
      <span>${meta.status === 'concluida' ? 'Meta concluída' : 'Faltam ' + formatarNumero(meta.faltam) + ' ' + un}</span>
      <span>${meta.percentual}%</span>
    </div>
    <div class="meta-cartao__rodape">
      <span class="meta-cartao__prazo">${esc(prazo)}</span>
    </div>
    <a class="btn btn--secundario btn--pequeno btn--bloco" href="metas-detalhes.html?id=${meta.id}">Ver Detalhes</a>
  </article>`;
}

function renderizarRecentes() {
  const secao = document.getElementById('secaoRecentes');
  const lista = document.getElementById('listaRecentes');
  const concluidas = todasAsMetas
    .filter(function (m) { return m.status === 'concluida'; })
    .sort(function (a, b) { return new Date(b.concluida_em) - new Date(a.concluida_em); })
    .slice(0, 5);

  if (concluidas.length === 0) {
    secao.hidden = true;
    return;
  }
  secao.hidden = false;

  lista.innerHTML = concluidas.map(function (meta) {
    const un = unidade(meta);
    return `<li class="card meta-recente-item">
      <div class="meta-recente-item__texto">
        <span class="meta-recente-item__titulo">${esc(meta.titulo)}</span>
        <span class="meta-recente-item__detalhe">Concluída em ${formatarData(meta.concluida_em)} · 100% atingido (${formatarNumero(meta.valor_atual)} ${un} de ${formatarNumero(meta.valor_objetivo)} ${un})</span>
      </div>
      <a class="btn btn--secundario btn--pequeno" href="metas-detalhes.html?id=${meta.id}">Ver</a>
    </li>`;
  }).join('');
}

function formatarData(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('pt-BR');
}

function formatarNumero(n) {
  return Number(n).toString().replace('.', ',');
}

function esc(s) {
  const div = document.createElement('div');
  div.textContent = s == null ? '' : s;
  return div.innerHTML;
}
