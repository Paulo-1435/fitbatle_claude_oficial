const TAMANHO_MAX_FOTO = 3 * 1024 * 1024;

const FAIXAS_NIVEL = [
  [0, 'iniciante'],
  [1000, 'intermediario'],
  [3000, 'avancado'],
  [7000, 'profissional'],
  [15000, 'elite']
];

const EMOJI_TIPO = {
  musculacao: '🏋️',
  cardio: '🏃',
  yoga: '🧘',
  outro: '💪'
};
const NOME_TIPO = {
  musculacao: 'Musculação',
  cardio: 'Cardio',
  yoga: 'Yoga',
  outro: 'Outro'
};

let usuarioLogado = null;
let fotoSelecionada = null;

document.addEventListener('DOMContentLoaded', function () {
  usuarioLogado = exigirLogin();
  if (!usuarioLogado) return;

  configurarMenu();
  configurarModais();
  configurarAvatar();
  configurarRanking();

  carregarPerfil();
  carregarTreinos();
  carregarRankingLocal();
});

function configurarAvatar() {
  ligar('avatarLarge', 'click', function () {
    if (usuarioLogado && usuarioLogado.foto) {
      document.getElementById('fotoAmpliada').src = urlFoto(usuarioLogado.foto);
      abrirOverlay('overlayFoto');
    } else {
      abrirEditarPerfil();
    }
  });

  ligar('avatarMini', 'click', function () {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  ligar('closeFoto', 'click', function () { fecharOverlay('overlayFoto'); });
  ligar('btnTrocarFoto', 'click', function () {
    fecharOverlay('overlayFoto');
    abrirEditarPerfil();
  });
}

async function carregarPerfil() {
  try {
    const resposta = await api(`/usuarios/${usuarioLogado.id}`);
    if (!resposta.ok) {
      if (resposta.status === 404) return sair();
      throw new Error('falha');
    }
    const u = await resposta.json();
    usuarioLogado = u;
    atualizarUsuarioDaSessao(u);
    preencherPerfil(u);
  } catch (e) {
    mostrarToast('Não foi possível carregar o perfil. A API está rodando?');
  }
}

function preencherPerfil(u) {
  texto('pNome', u.nome);
  texto('pHandle', '@' + (u.email ? u.email.split('@')[0] : 'usuario'));
  texto('pLocal', u.cidade || 'Localização não informada');
  texto('pBio', u.descricao || '');
  texto('pPeso', u.peso ? formatarNumero(u.peso) + ' kg' : '—');
  texto('pAltura', u.altura ? formatarNumero(u.altura) + ' m' : '—');
  texto('pIdade', u.idade != null ? u.idade : '—');

  aplicarFoto('avatarLarge', u.foto);
  aplicarFoto('avatarMini', u.foto);

  const nivel = calcularNivel(u.xp || 0);
  texto('levelNome', nivel.nome);
  document.getElementById('levelBar').style.width = nivel.pct + '%';
  document.getElementById('levelMarker').style.left = nivel.pct + '%';
  document.getElementById('levelFooter').textContent = nivel.falta > 0
    ? `Faltam ${nivel.falta} xp para o próximo nível ↑`
    : 'Nível máximo alcançado 🏆';
}

async function carregarTreinos() {
  try {
    const resposta = await api(`/usuarios/${usuarioLogado.id}/atividades`);
    if (!resposta.ok) throw new Error('falha');
    const treinos = await resposta.json();
    renderizarTreinos(treinos);

    document.getElementById('statTreinos').textContent = treinos.length;
    document.getElementById('statSequencia').textContent = calcularSequencia(treinos) + 'd';
  } catch (e) {
    mostrarToast('Não foi possível carregar os treinos.');
  }
}

async function carregarRankingLocal() {
  try {
    const resposta = await api(`/usuarios/${usuarioLogado.id}/ranking`);
    if (!resposta.ok) return;
    const dados = await resposta.json();
    const pos = dados.regional && dados.regional.posicao;
    document.getElementById('statRanking').textContent = pos ? pos + 'º' : '—';
  } catch (e) {
  }
}

function renderizarTreinos(treinos) {
  const lista = document.getElementById('listaTreinos');
  const vazia = document.getElementById('listaVazia');

  lista.querySelectorAll('.activity-card').forEach(function (el) { el.remove(); });

  if (treinos.length === 0) {
    vazia.hidden = false;
    return;
  }
  vazia.hidden = true;

  treinos.forEach(function (t) {
    lista.insertAdjacentHTML('beforeend', htmlCardTreino(t));
  });

  lista.querySelectorAll('[data-excluir]').forEach(function (botao) {
    botao.addEventListener('click', function () {
      excluirTreino(botao.getAttribute('data-excluir'));
    });
  });

  lista.querySelectorAll('[data-compartilhar]').forEach(function (botao) {
    botao.addEventListener('click', function () {
      compartilhar(botao.getAttribute('data-compartilhar'));
    });
  });
}

function compartilhar(texto) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(texto)
      .then(function () { mostrarToast('Copiado! Agora é só colar onde quiser compartilhar.'); })
      .catch(function () { mostrarToast('Não foi possível copiar o texto.'); });
  } else {
    mostrarToast('Copie: ' + texto);
  }
}

function htmlCardTreino(t) {
  const emoji = EMOJI_TIPO[t.tipo] || '💪';
  const nomeTipo = NOME_TIPO[t.tipo] || capitalizar(t.tipo);
  const titulo = nomeTipo + (t.titulo ? ' — ' + esc(t.titulo).toUpperCase() : '');

  const metricas = [];
  if (t.tempo_min != null) {
    const dur = partesDuracao(t.tempo_min);
    metricas.push(metrica(dur.v, dur.u, 'Duração'));
  }
  if (t.carga_kg != null) metricas.push(metrica(formatarNumero(t.carga_kg), 'kg', 'Carga máx.'));
  if (t.repeticoes != null) metricas.push(metrica(t.repeticoes, '', 'Séries / reps'));
  if (t.distancia_km != null) {
    const dist = partesDistancia(t.distancia_km);
    metricas.push(metrica(dist.v, dist.u, 'Distância'));
  }

  return `
    <div class="activity-card">
      <div class="activity-title">${emoji} ${titulo}
        <span class="activity-time">${dataRelativa(t.data_registro)}</span>
      </div>
      <div class="activity-desc">${esc(t.descricao || '')}</div>
      <div class="activity-metrics">${metricas.join('')}</div>
      <div class="card-actions">
        <button class="action-btn" data-compartilhar="${esc('Registrei um treino de ' + nomeTipo + (t.titulo ? ' (' + t.titulo + ')' : '') + ' no FitBattle! 💪 #FitBattle')}">🔗 Compartilhar</button>
        <button class="action-btn excluir" data-excluir="${t.id}">🗑️ Excluir</button>
      </div>
    </div>`;
}

function metrica(valor, unidade, rotulo) {
  return `<div class="metric-box">
    <div class="m-val">${valor} <span>${unidade}</span></div>
    <div class="m-lbl">${rotulo}</div>
  </div>`;
}

async function excluirTreino(id) {
  if (!confirm('Excluir este treino? A pontuação dele será descontada.')) return;
  try {
    const resposta = await api(`/atividades/${id}`, { method: 'DELETE' });
    if (!resposta.ok) throw new Error('falha');
    mostrarToast('Treino excluído.');
    carregarPerfil();
    carregarTreinos();
    carregarRankingLocal();
  } catch (e) {
    mostrarToast('Não foi possível excluir o treino.');
  }
}

function abrirNovoTreino() {
  document.getElementById('formTreino').reset();
  document.getElementById('erroTreino').textContent = '';
  ajustarCamposTreino();
  abrirOverlay('overlayTreino');
}

function ajustarCamposTreino() {
  const tipo = document.getElementById('treinoTipo').value;
  const mostraForca = (tipo === 'musculacao' || tipo === 'outro');
  const mostraDist = (tipo === 'cardio' || tipo === 'outro');
  document.getElementById('linhaForca').hidden = !mostraForca;
  document.getElementById('campoDist').hidden = !mostraDist;
}

function configurarModais() {
  ligar('btnNovoTreino', 'click', abrirNovoTreino);
  ligar('treinoTipo', 'change', ajustarCamposTreino);
  ligar('closeTreino', 'click', function () { fecharOverlay('overlayTreino'); });
  ligar('btnEditarPerfil', 'click', abrirEditarPerfil);
  ligar('btnEditarPerfilMenu', 'click', abrirEditarPerfil);
  ligar('closePerfil', 'click', function () { fecharOverlay('overlayPerfil'); });

  ligar('fotoBtn', 'click', function () { document.getElementById('fotoInput').click(); });
  ligar('fotoInput', 'change', function () {
    const arquivo = this.files && this.files[0];
    if (!arquivo) return;
    if (arquivo.size > TAMANHO_MAX_FOTO) {
      document.getElementById('erroPerfil').textContent = 'A imagem deve ter no máximo 3 MB.';
      this.value = '';
      return;
    }
    fotoSelecionada = arquivo;
    document.getElementById('erroPerfil').textContent = '';
    document.getElementById('fotoNome').textContent = arquivo.name;
    document.getElementById('avatarPreview').style.backgroundImage =
      'url("' + URL.createObjectURL(arquivo) + '")';
  });

  document.querySelectorAll('.overlay').forEach(function (ov) {
    ov.addEventListener('click', function (e) {
      if (e.target === ov) ov.classList.remove('aberto');
    });
  });

  document.getElementById('formTreino').addEventListener('submit', async function (e) {
    e.preventDefault();
    const erro = document.getElementById('erroTreino');
    erro.textContent = '';

    const titulo = document.getElementById('treinoTitulo').value.trim();

    const horas = numero(document.getElementById('treinoHoras').value) || 0;
    const minutos = numero(document.getElementById('treinoMinutos').value) || 0;
    if (minutos < 0 || minutos > 59) {
      erro.textContent = 'Os minutos devem ser de 0 a 59.';
      return;
    }
    if (horas < 0) { erro.textContent = 'Duração inválida.'; return; }
    const tempoMin = (horas * 60 + minutos) || null;

    const km = numero(document.getElementById('treinoKm').value) || 0;
    const metros = numero(document.getElementById('treinoMetros').value) || 0;
    if (metros < 0 || metros > 999) {
      erro.textContent = 'Os metros devem ser de 0 a 999.';
      return;
    }
    if (km < 0) { erro.textContent = 'Distância inválida.'; return; }
    const distanciaKm = (km + metros / 1000) || null;

    if (titulo === '') { erro.textContent = 'Informe o título do treino.'; return; }
    if (!tempoMin && !distanciaKm) {
      erro.textContent = 'Informe ao menos a duração ou a distância.';
      return;
    }

    const corpo = {
      tipo: document.getElementById('treinoTipo').value,
      titulo: titulo,
      descricao: document.getElementById('treinoDesc').value.trim(),
      tempo_min: tempoMin,
      carga_kg: numero(document.getElementById('treinoCarga').value),
      repeticoes: numero(document.getElementById('treinoReps').value),
      distancia_km: distanciaKm
    };

    try {
      const resposta = await api(`/usuarios/${usuarioLogado.id}/atividades`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corpo)
      });
      const dados = await resposta.json();
      if (!resposta.ok) { erro.textContent = dados.erro || 'Não foi possível registrar.'; return; }

      fecharOverlay('overlayTreino');
      e.target.reset();
      mostrarToast('Treino registrado! +' + dados.pontuacao_ganha + ' xp');
      carregarPerfil();
      carregarTreinos();
      carregarRankingLocal();
    } catch (err) {
      erro.textContent = 'Não foi possível conectar à API.';
    }
  });

  document.getElementById('formPerfil').addEventListener('submit', async function (e) {
    e.preventDefault();
    const erro = document.getElementById('erroPerfil');
    erro.textContent = '';

    const corpo = {
      nome: document.getElementById('editNome').value.trim(),
      email: document.getElementById('editEmail').value.trim(),
      descricao: document.getElementById('editBio').value.trim(),
      idade: document.getElementById('editIdade').value || null,
      cidade: document.getElementById('editCidade').value.trim() || null,
      peso: document.getElementById('editPeso').value || null,
      altura: document.getElementById('editAltura').value || null
    };

    try {
      const resposta = await api(`/usuarios/${usuarioLogado.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corpo)
      });
      const dados = await resposta.json();
      if (!resposta.ok) { erro.textContent = dados.erro || 'Não foi possível salvar.'; return; }

      let usuarioFinal = dados.usuario;

      if (fotoSelecionada) {
        const fd = new FormData();
        fd.append('foto', fotoSelecionada);
        const rFoto = await api(`/usuarios/${usuarioLogado.id}/foto`, {
          method: 'POST',
          body: fd
        });
        const dFoto = await rFoto.json().catch(function () { return {}; });
        if (!rFoto.ok) {
          erro.textContent = dFoto.erro || 'Os dados foram salvos, mas a foto não pôde ser enviada.';
          return;
        }
        usuarioFinal = dFoto.usuario;
      }

      usuarioLogado = usuarioFinal;
      atualizarUsuarioDaSessao(usuarioFinal);
      preencherPerfil(usuarioFinal);
      carregarRankingLocal();
      fotoSelecionada = null;
      fecharOverlay('overlayPerfil');
      mostrarToast('Perfil atualizado.');
    } catch (err) {
      erro.textContent = 'Não foi possível conectar à API.';
    }
  });
}

function abrirEditarPerfil() {
  const u = usuarioLogado;
  document.getElementById('editNome').value = u.nome || '';
  document.getElementById('editEmail').value = u.email || '';
  document.getElementById('editBio').value = u.descricao || '';
  document.getElementById('editIdade').value = u.idade != null ? u.idade : '';
  document.getElementById('editCidade').value = u.cidade || '';
  document.getElementById('editPeso').value = u.peso != null ? u.peso : '';
  document.getElementById('editAltura').value = u.altura != null ? u.altura : '';
  document.getElementById('erroPerfil').textContent = '';

  fotoSelecionada = null;
  document.getElementById('fotoInput').value = '';
  document.getElementById('fotoNome').textContent = 'JPG, PNG ou WEBP (até 3 MB)';
  aplicarFoto('avatarPreview', u.foto);

  abrirOverlay('overlayPerfil');
}

function configurarMenu() {
  const sidebar = document.getElementById('configSidebar');
  const main = document.getElementById('mainContent');

  function abrir() {
    sidebar.classList.remove('escondida');
    main.classList.remove('menu-fechado');
  }
  function fechar() {
    sidebar.classList.add('escondida');
    main.classList.add('menu-fechado');
  }

  fechar();

  document.getElementById('toggleMenuBtn').addEventListener('click', function () {
    if (sidebar.classList.contains('escondida')) abrir();
    else fechar();
  });
  document.getElementById('closeMenuBtn').addEventListener('click', fechar);

  document.querySelectorAll('.menu-em-breve').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      mostrarToast('Essa área ainda está em desenvolvimento.');
    });
  });

  document.getElementById('btnSair').addEventListener('click', sair);

  ligar('btnProgresso', 'click', function () {
    mostrarToast('Relatório de progresso: em breve.');
  });
}

function sair() {
  encerrarSessao();
}

function configurarRanking() {
  ligar('btnRanking', 'click', abrirRanking);
  ligar('closeRanking', 'click', function () { fecharOverlay('overlayRanking'); });

  document.querySelectorAll('.ranking-aba').forEach(function (aba) {
    aba.addEventListener('click', function () {
      document.querySelectorAll('.ranking-aba').forEach(function (a) {
        a.classList.remove('ativa');
      });
      aba.classList.add('ativa');
      carregarRanking(aba.getAttribute('data-escopo'));
    });
  });
}

function abrirRanking() {
  abrirOverlay('overlayRanking');
  const ativa = document.querySelector('.ranking-aba.ativa');
  carregarRanking(ativa ? ativa.getAttribute('data-escopo') : 'regional');
}

async function carregarRanking(escopo) {
  const lista = document.getElementById('rankingLista');
  lista.innerHTML = '<p class="rank-vazio">Carregando...</p>';

  let url;
  if (escopo === 'regional') {
    if (!usuarioLogado.cidade) {
      lista.innerHTML = '<p class="rank-vazio">Informe sua cidade em "Editar perfil" para ver o ranking da sua região.</p>';
      return;
    }
    url = `/ranking/regional?cidade=${encodeURIComponent(usuarioLogado.cidade)}`;
  } else {
    url = '/ranking/global';
  }

  try {
    const resposta = await api(url);
    const dados = await resposta.json();
    if (!resposta.ok) {
      lista.innerHTML = '<p class="rank-vazio">' + esc(dados.erro || 'Não foi possível carregar o ranking.') + '</p>';
      return;
    }
    if (dados.length === 0) {
      lista.innerHTML = '<p class="rank-vazio">Ninguém no ranking ainda.</p>';
      return;
    }
    lista.innerHTML = dados.map(function (r) {
      const eu = r.id_usuario === usuarioLogado.id;
      const cidade = (escopo === 'global' && r.cidade)
        ? '<span class="rank-cidade">' + esc(r.cidade) + '</span>' : '';
      return '<div class="rank-linha' + (eu ? ' eu' : '') + '">' +
        '<span class="rank-pos">' + r.posicao + 'º</span>' +
        '<span class="rank-nome">' + esc(r.nome) + (eu ? ' (você)' : '') + '</span>' +
        cidade +
        '<span class="rank-pts">' + r.pontuacao_total + ' xp</span>' +
        '</div>';
    }).join('');
  } catch (e) {
    lista.innerHTML = '<p class="rank-vazio">Não foi possível conectar à API.</p>';
  }
}

function calcularNivel(xp) {
  let indice = 0;
  for (let i = 0; i < FAIXAS_NIVEL.length; i++) {
    if (xp >= FAIXAS_NIVEL[i][0]) indice = i;
  }
  const base = FAIXAS_NIVEL[indice][0];
  const nome = FAIXAS_NIVEL[indice][1];

  if (indice === FAIXAS_NIVEL.length - 1) {
    return { nome: nome, pct: 100, falta: 0 };
  }
  const proximo = FAIXAS_NIVEL[indice + 1][0];
  const pct = Math.round(((xp - base) / (proximo - base)) * 100);
  return { nome: nome, pct: Math.min(100, Math.max(0, pct)), falta: proximo - xp };
}

function calcularSequencia(treinos) {
  if (treinos.length === 0) return 0;

  const dias = new Set();
  treinos.forEach(function (t) {
    if (t.data_registro) dias.add(diaLocal(new Date(t.data_registro)));
  });

  const hoje = new Date();
  const ontem = new Date();
  ontem.setDate(hoje.getDate() - 1);

  let cursor;
  if (dias.has(diaLocal(hoje))) cursor = hoje;
  else if (dias.has(diaLocal(ontem))) cursor = ontem;
  else return 0;

  let sequencia = 0;
  while (dias.has(diaLocal(cursor))) {
    sequencia++;
    cursor.setDate(cursor.getDate() - 1);
  }
  return sequencia;
}

function texto(id, valor) {
  document.getElementById(id).textContent = valor;
}

function ligar(id, evento, fn) {
  const el = document.getElementById(id);
  if (el) el.addEventListener(evento, fn);
}

function urlFoto(caminho) {
  if (!caminho) return null;
  return caminho.indexOf('http') === 0 ? caminho : ORIGEM_API + caminho;
}

function aplicarFoto(id, url) {
  const el = document.getElementById(id);
  if (!el) return;
  const src = urlFoto(url);
  el.style.backgroundImage = src ? `url("${src}")` : 'none';
}

function abrirOverlay(id) { document.getElementById(id).classList.add('aberto'); }
function fecharOverlay(id) { document.getElementById(id).classList.remove('aberto'); }

function mostrarToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('mostrar');
  clearTimeout(mostrarToast._timer);
  mostrarToast._timer = setTimeout(function () { t.classList.remove('mostrar'); }, 2600);
}

function esc(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

function capitalizar(s) {
  if (!s) return '';
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function formatarNumero(n) {
  return Number(n).toString().replace('.', ',');
}

function numero(valor) {
  if (valor === null || valor === undefined || String(valor).trim() === '') return null;
  const n = parseFloat(String(valor).replace(',', '.'));
  return isNaN(n) ? null : n;
}

function partesDuracao(min) {
  min = Number(min);
  if (min < 60) return { v: String(min), u: 'min' };
  const horas = Math.floor(min / 60);
  const resto = min % 60;
  return { v: resto === 0 ? horas + 'h' : horas + 'h' + String(resto).padStart(2, '0'), u: '' };
}

function partesDistancia(km) {
  const n = Number(km);
  if (n >= 1) return { v: formatarNumero(n), u: 'km' };
  return { v: String(Math.round(n * 1000)), u: 'm' };
}

function diaLocal(data) {
  const ano = data.getFullYear();
  const mes = String(data.getMonth() + 1).padStart(2, '0');
  const dia = String(data.getDate()).padStart(2, '0');
  return `${ano}-${mes}-${dia}`;
}

function dataRelativa(iso) {
  if (!iso) return '';
  const data = new Date(iso);
  const agora = new Date();
  const hora = data.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });

  if (diaLocal(data) === diaLocal(agora)) return 'Hoje, ' + hora;

  const ontem = new Date();
  ontem.setDate(agora.getDate() - 1);
  if (diaLocal(data) === diaLocal(ontem)) return 'Ontem, ' + hora;

  const dias = Math.floor((agora - data) / (1000 * 60 * 60 * 24));
  if (dias < 30) return `${dias} dias atrás`;
  return data.toLocaleDateString('pt-BR');
}
