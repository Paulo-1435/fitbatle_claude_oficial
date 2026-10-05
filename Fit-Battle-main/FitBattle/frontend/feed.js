const LIMITE_FEED = 30;

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

document.addEventListener('DOMContentLoaded', function () {
  usuarioLogado = exigirLogin();
  if (!usuarioLogado) return;

  configurarBanner();
  configurarModalTreino();
  ligarAcoesDoFeed();

  carregarBanner();
  carregarFeed();
  carregarTop3();
});

function primeiroNome(nome) {
  const partes = String(nome || '').trim().split(/\s+/);
  return partes[0] || 'atleta';
}

function configurarBanner() {
  document.getElementById('feedSaudacao').textContent = 'Bem-vindo de volta, ' + primeiroNome(usuarioLogado.nome) + '! 👋';
}

async function carregarBanner() {
  const chips = document.getElementById('feedChips');
  const subtitulo = document.getElementById('feedSubtitulo');
  chips.replaceChildren(criarElemento('span', { classe: 'badge badge--placeholder', texto: 'Unidade: em breve' }));

  try {
    const resposta = await api(`/usuarios/${usuarioLogado.id}/atividades`);
    if (!resposta.ok) throw new Error('falha');
    const treinos = await resposta.json();
    const sequencia = calcularSequencia(treinos);

    if (sequencia > 0) {
      chips.prepend(criarElemento('span', { classe: 'badge badge--destaque', texto: '🔥 Sequência de ' + sequencia + ' dia' + (sequencia > 1 ? 's' : '') }));
      subtitulo.textContent = 'Você está treinando há ' + sequencia + ' dia' + (sequencia > 1 ? 's' : '') + ' seguidos. Mantenha o ritmo!';
    } else if (treinos.length > 0) {
      subtitulo.textContent = 'Faz um tempo que você não registra um treino. Bora retomar?';
    } else {
      subtitulo.textContent = 'Registre seu primeiro treino para começar sua sequência.';
    }
  } catch (e) {
    subtitulo.textContent = 'Não foi possível carregar seu progresso agora.';
  }
}

async function carregarFeed() {
  const lista = document.getElementById('feedLista');
  try {
    const resposta = await api(`/feed?limite=${LIMITE_FEED}`);
    if (!resposta.ok) throw new Error('falha');
    const itens = await resposta.json();

    if (itens.length === 0) {
      lista.replaceChildren(criarElemento('p', {
        classe: 'estado-vazio',
        texto: 'Ninguém postou nada ainda. Registre um treino para começar o feed.'
      }));
      return;
    }

    lista.innerHTML = itens.map(htmlCardFeed).join('');
  } catch (e) {
    lista.replaceChildren(criarElemento('p', { classe: 'estado-vazio', texto: 'Não foi possível carregar o feed. A API está rodando?' }));
  }
}

async function carregarTop3() {
  const lista = document.getElementById('top3Lista');
  try {
    const resposta = await api('/ranking/global?limite=3');
    if (!resposta.ok) throw new Error('falha');
    const dados = await resposta.json();

    if (dados.length === 0) {
      lista.replaceChildren(criarElemento('p', { classe: 'estado-vazio', texto: 'Ninguém no ranking ainda.' }));
      return;
    }

    lista.innerHTML = dados.map(function (item) {
      return `<div class="top3-linha">
        <span class="top3-linha__pos">${item.posicao}º</span>
        <span class="top3-linha__info"><span class="top3-linha__nome">${esc(item.nome)}</span></span>
        <span class="top3-linha__pontos">${item.pontuacao_total} xp</span>
      </div>`;
    }).join('');
  } catch (e) {
    lista.replaceChildren(criarElemento('p', { classe: 'estado-vazio', texto: 'Não foi possível carregar o ranking.' }));
  }
}

function htmlCardFeed(item) {
  const dono = item.usuario || {};
  const foto = urlFoto(dono.foto);
  const avatarEstilo = foto ? ` style="background-image:url('${foto.replace(/'/g, '%27')}')"` : '';
  const avatarConteudo = foto ? '' : esc(iniciais(dono.nome));

  let titulo;
  let metricasHtml = '';

  if (item.tipo_conteudo === 'atividade') {
    const emoji = EMOJI_TIPO[item.tipo] || '💪';
    const nomeTipo = NOME_TIPO[item.tipo] || capitalizar(item.tipo);
    titulo = `${emoji} ${nomeTipo}${item.titulo ? ' — ' + esc(item.titulo) : ''}`;

    const metricas = [];
    if (item.tempo_min != null) {
      const duracao = partesDuracao(item.tempo_min);
      metricas.push(feedMetrica(duracao.v, duracao.u, 'Duração'));
    }
    if (item.carga_kg != null) metricas.push(feedMetrica(formatarNumero(item.carga_kg), 'kg', 'Carga máx.'));
    if (item.repeticoes != null) metricas.push(feedMetrica(item.repeticoes, '', 'Séries / reps'));
    if (item.distancia_km != null) {
      const distancia = partesDistancia(item.distancia_km);
      metricas.push(feedMetrica(distancia.v, distancia.u, 'Distância'));
    }
    metricasHtml = metricas.length ? `<div class="feed-card__metricas">${metricas.join('')}</div>` : '';
  } else {
    titulo = '📣 Nova postagem';
  }

  const descricao = item.descricao || item.texto || '';
  const midia = item.foto ? `<img class="feed-card__midia" src="${urlFoto(item.foto)}" alt="Foto do treino de ${esc(dono.nome || '')}" >` : '';

  const textoCompartilhar = item.tipo_conteudo === 'atividade'
    ? `Registrei um treino de ${NOME_TIPO[item.tipo] || item.tipo}${item.titulo ? ' (' + item.titulo + ')' : ''} no FitBattle! 💪 #FitBattle`
    : (item.texto ? item.texto + ' #FitBattle' : 'Confira meu FitBattle! #FitBattle');

  return `
    <article class="card card--interno feed-card" data-tipo-alvo="${item.tipo_conteudo}" data-id-alvo="${item.id}">
      <div class="feed-card__cabecalho">
        <span class="avatar avatar--pequeno"${avatarEstilo} aria-hidden="true">${avatarConteudo}</span>
        <div class="feed-card__quem">
          <span class="feed-card__nome">${esc(dono.nome || 'Usuário removido')}</span>
          <span class="feed-card__tempo">${dataRelativa(item.data_registro)}</span>
        </div>
      </div>
      <div class="feed-card__titulo">${titulo}</div>
      ${descricao ? `<p class="feed-card__texto">${esc(descricao)}</p>` : ''}
      ${midia}
      ${metricasHtml}
      <div class="feed-card__rodape">
        <button type="button" class="btn btn--fantasma btn--pequeno feed-acao${item.curti ? ' feed-acao--ativa' : ''}" data-acao="curtir">
          <svg class="icone" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 10v11M2 13v7a2 2 0 0 0 2 2h12.5a2 2 0 0 0 2-2l1.3-7a2 2 0 0 0-2-2.4H15V5a3 3 0 0 0-3-3l-3 7v9"/></svg>
          <span data-contagem="curtidas">${item.curtidas} Mandou Bem</span>
        </button>
        <button type="button" class="btn btn--fantasma btn--pequeno feed-acao" data-acao="comentar">
          <svg class="icone" viewBox="0 0 24 24" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          <span data-contagem="comentarios">${item.comentarios} Comentários</span>
        </button>
        <button type="button" class="btn btn--fantasma btn--pequeno feed-acao" data-acao="compartilhar" data-texto="${esc(textoCompartilhar)}">
          <svg class="icone" viewBox="0 0 24 24" aria-hidden="true"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.6" y1="13.5" x2="15.4" y2="17.5"/><line x1="15.4" y1="6.5" x2="8.6" y2="10.5"/></svg>
          Compartilhar
        </button>
      </div>
      <div class="feed-comentarios" hidden data-painel-comentarios>
        <div data-lista-comentarios></div>
        <form class="feed-comentarios__form" data-form-comentario>
          <input type="text" class="input" placeholder="Escreva um comentário..." maxlength="500" required>
          <button type="submit" class="btn btn--primario btn--pequeno">Enviar</button>
        </form>
      </div>
    </article>`;
}

function feedMetrica(valor, unidade, rotulo) {
  return `<div class="feed-metrica">
    <span class="feed-metrica__valor">${valor}${unidade ? ` <small>${unidade}</small>` : ''}</span>
    <span class="feed-metrica__rotulo">${rotulo}</span>
  </div>`;
}

function htmlComentario(c) {
  const dono = c.usuario || {};
  const foto = urlFoto(dono.foto);
  const avatarEstilo = foto ? ` style="background-image:url('${foto.replace(/'/g, '%27')}')"` : '';
  const avatarConteudo = foto ? '' : esc(iniciais(dono.nome));

  return `<div class="feed-comentario">
    <span class="avatar avatar--pequeno"${avatarEstilo} aria-hidden="true">${avatarConteudo}</span>
    <div class="feed-comentario__corpo">
      <div class="feed-comentario__nome">${esc(dono.nome || 'Usuário removido')}</div>
      <div class="feed-comentario__texto">${esc(c.texto)}</div>
    </div>
  </div>`;
}

function ligarAcoesDoFeed() {
  const lista = document.getElementById('feedLista');

  lista.addEventListener('click', function (evento) {
    const botaoCurtir = evento.target.closest('[data-acao="curtir"]');
    if (botaoCurtir) return curtir(botaoCurtir);

    const botaoComentar = evento.target.closest('[data-acao="comentar"]');
    if (botaoComentar) return alternarComentarios(botaoComentar);

    const botaoCompartilhar = evento.target.closest('[data-acao="compartilhar"]');
    if (botaoCompartilhar) return compartilhar(botaoCompartilhar.getAttribute('data-texto'));
  });

  lista.addEventListener('submit', function (evento) {
    const form = evento.target.closest('[data-form-comentario]');
    if (!form) return;
    evento.preventDefault();
    enviarComentario(form);
  });
}

async function curtir(botao) {
  const card = botao.closest('.feed-card');
  botao.disabled = true;
  try {
    const resposta = await api(`/feed/${card.dataset.tipoAlvo}/${card.dataset.idAlvo}/curtir`, { method: 'POST' });
    const dados = await resposta.json().catch(function () { return {}; });
    if (!resposta.ok) {
      mostrarToast(dados.erro || 'Não foi possível curtir agora.');
      return;
    }
    botao.classList.toggle('feed-acao--ativa', dados.curti);
    botao.querySelector('[data-contagem="curtidas"]').textContent = dados.curtidas + ' Mandou Bem';
  } catch (e) {
    mostrarToast('Não foi possível conectar à API.');
  } finally {
    botao.disabled = false;
  }
}

function alternarComentarios(botao) {
  const card = botao.closest('.feed-card');
  const painel = card.querySelector('[data-painel-comentarios]');
  const vaiAbrir = painel.hidden;
  painel.hidden = !vaiAbrir;
  if (vaiAbrir && !painel.dataset.carregado) {
    painel.dataset.carregado = '1';
    carregarComentarios(card);
  }
}

async function carregarComentarios(card) {
  const lista = card.querySelector('[data-lista-comentarios]');
  lista.replaceChildren(criarElemento('p', { classe: 'feed-card__texto', texto: 'Carregando...' }));
  try {
    const resposta = await api(`/feed/${card.dataset.tipoAlvo}/${card.dataset.idAlvo}/comentarios`);
    const dados = await resposta.json();
    if (!resposta.ok) throw new Error('falha');

    if (dados.length === 0) {
      lista.replaceChildren(criarElemento('p', { classe: 'feed-card__texto', texto: 'Nenhum comentário ainda. Seja o primeiro!' }));
      return;
    }
    lista.innerHTML = dados.map(htmlComentario).join('');
  } catch (e) {
    lista.replaceChildren(criarElemento('p', { classe: 'feed-card__texto', texto: 'Não foi possível carregar os comentários.' }));
  }
}

async function enviarComentario(form) {
  const card = form.closest('.feed-card');
  const campo = form.querySelector('input');
  const botao = form.querySelector('button');
  const texto = campo.value.trim();
  if (!texto) return;

  botao.disabled = true;
  try {
    const resposta = await api(`/feed/${card.dataset.tipoAlvo}/${card.dataset.idAlvo}/comentarios`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texto: texto })
    });
    const dados = await resposta.json();
    if (!resposta.ok) {
      mostrarToast(dados.erro || 'Não foi possível comentar.');
      return;
    }

    campo.value = '';
    const lista = card.querySelector('[data-lista-comentarios]');
    if (lista.querySelector('.feed-card__texto')) lista.replaceChildren();
    lista.insertAdjacentHTML('beforeend', htmlComentario(dados.comentario));

    const contagem = card.querySelector('[data-contagem="comentarios"]');
    const atual = parseInt(contagem.textContent, 10) || 0;
    contagem.textContent = (atual + 1) + ' Comentários';
  } catch (e) {
    mostrarToast('Não foi possível conectar à API.');
  } finally {
    botao.disabled = false;
  }
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

function configurarModalTreino() {
  const overlay = document.getElementById('overlayTreino');
  const form = document.getElementById('formTreino');
  const erro = document.getElementById('erroTreino');

  function abrir() {
    form.reset();
    erro.textContent = '';
    ajustarCamposTreino();
    overlay.classList.add('aberto');
    document.getElementById('treinoTitulo').focus();
  }
  function fechar() {
    overlay.classList.remove('aberto');
  }
  function ajustarCamposTreino() {
    const tipo = document.getElementById('treinoTipo').value;
    const mostraForca = (tipo === 'musculacao' || tipo === 'outro');
    const mostraDist = (tipo === 'cardio' || tipo === 'outro');
    document.getElementById('linhaForca').hidden = !mostraForca;
    document.getElementById('campoDist').hidden = !mostraDist;
  }

  document.getElementById('btnNovoTreino').addEventListener('click', abrir);
  document.getElementById('closeTreino').addEventListener('click', fechar);
  document.getElementById('cancelarTreino').addEventListener('click', fechar);
  document.getElementById('treinoTipo').addEventListener('change', ajustarCamposTreino);
  overlay.addEventListener('click', function (evento) {
    if (evento.target === overlay) fechar();
  });
  document.addEventListener('keydown', function (evento) {
    if (evento.key === 'Escape' && overlay.classList.contains('aberto')) fechar();
  });

  form.addEventListener('submit', async function (evento) {
    evento.preventDefault();
    erro.textContent = '';

    const titulo = document.getElementById('treinoTitulo').value.trim();

    const horas = numero(document.getElementById('treinoHoras').value) || 0;
    const minutos = numero(document.getElementById('treinoMinutos').value) || 0;
    if (minutos < 0 || minutos > 59) { erro.textContent = 'Os minutos devem ser de 0 a 59.'; return; }
    if (horas < 0) { erro.textContent = 'Duração inválida.'; return; }
    const tempoMin = (horas * 60 + minutos) || null;

    const km = numero(document.getElementById('treinoKm').value) || 0;
    const metros = numero(document.getElementById('treinoMetros').value) || 0;
    if (metros < 0 || metros > 999) { erro.textContent = 'Os metros devem ser de 0 a 999.'; return; }
    if (km < 0) { erro.textContent = 'Distância inválida.'; return; }
    const distanciaKm = (km + metros / 1000) || null;

    if (titulo === '') { erro.textContent = 'Informe o título do treino.'; return; }
    if (!tempoMin && !distanciaKm) { erro.textContent = 'Informe ao menos a duração ou a distância.'; return; }

    const corpo = {
      tipo: document.getElementById('treinoTipo').value,
      titulo: titulo,
      descricao: document.getElementById('treinoDesc').value.trim(),
      tempo_min: tempoMin,
      carga_kg: numero(document.getElementById('treinoCarga').value),
      repeticoes: numero(document.getElementById('treinoReps').value),
      distancia_km: distanciaKm
    };

    const botaoSalvar = form.querySelector('button[type="submit"]');
    botaoSalvar.disabled = true;
    try {
      const resposta = await api(`/usuarios/${usuarioLogado.id}/atividades`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corpo)
      });
      const dados = await resposta.json();
      if (!resposta.ok) { erro.textContent = dados.erro || 'Não foi possível registrar.'; return; }

      fechar();
      mostrarToast('Treino registrado! +' + dados.pontuacao_ganha + ' xp');
      carregarBanner();
      carregarFeed();
    } catch (e) {
      erro.textContent = 'Não foi possível conectar à API.';
    } finally {
      botaoSalvar.disabled = false;
    }
  });
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

function esc(s) {
  const div = document.createElement('div');
  div.textContent = s == null ? '' : s;
  return div.innerHTML;
}
