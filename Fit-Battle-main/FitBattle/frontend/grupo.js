let usuarioLogado = null;

document.addEventListener('DOMContentLoaded', function () {
  usuarioLogado = exigirLogin();
  if (!usuarioLogado) return;

  document.getElementById('btnCriarGrupo').addEventListener('click', function () {
    window.location.href = 'grupo-criar.html';
  });
  document.getElementById('btnCriarPrimeiroGrupo').addEventListener('click', function () {
    window.location.href = 'grupo-criar.html';
  });
  document.getElementById('abaMeusGrupos').addEventListener('click', function () { selecionarAba('meus-grupos'); });
  document.getElementById('abaConvites').addEventListener('click', function () { selecionarAba('convites'); });
  document.getElementById('btnVerConvites').addEventListener('click', function () { selecionarAba('convites'); });

  const abaInicial = window.location.hash === '#convites' ? 'convites' : 'meus-grupos';
  selecionarAba(abaInicial);
});

function selecionarAba(aba) {
  const meusGrupos = aba === 'meus-grupos';
  document.getElementById('abaMeusGrupos').classList.toggle('aba--ativa', meusGrupos);
  document.getElementById('abaMeusGrupos').setAttribute('aria-selected', String(meusGrupos));
  document.getElementById('abaConvites').classList.toggle('aba--ativa', !meusGrupos);
  document.getElementById('abaConvites').setAttribute('aria-selected', String(!meusGrupos));
  document.getElementById('painelMeusGrupos').hidden = !meusGrupos;
  document.getElementById('painelConvites').hidden = meusGrupos;

  if (meusGrupos) {
    carregarMeusGrupos();
  } else {
    carregarConvites();
  }
}

async function carregarMeusGrupos() {
  const lista = document.getElementById('listaGrupos');
  const vazio = document.getElementById('estadoVazioGrupos');
  lista.innerHTML = '<p class="estado-vazio">Carregando seus grupos...</p>';
  vazio.hidden = true;

  try {
    const resposta = await api('/grupos');
    const grupos = await resposta.json();
    if (!resposta.ok) {
      lista.innerHTML = '<p class="estado-vazio">Não foi possível carregar seus grupos.</p>';
      return;
    }

    document.getElementById('contadorMeusGrupos').textContent = grupos.length;

    if (grupos.length === 0) {
      lista.innerHTML = '';
      vazio.hidden = false;
      return;
    }

    lista.innerHTML = grupos.map(htmlCartaoGrupo).join('');
  } catch (e) {
    lista.innerHTML = '<p class="estado-vazio">Não foi possível conectar à API.</p>';
  }

  carregarDestaqueConvite();
}

function htmlCartaoGrupo(grupo) {
  const papel = grupo.meu_papel === 'admin' ? 'Você é administrador' : 'Você é membro';
  return `<article class="card grupo-cartao">
    <span class="grupo-cartao__icone" aria-hidden="true">${esc(iniciais(grupo.nome))}</span>
    <div class="grupo-cartao__corpo">
      <div class="grupo-cartao__topo">
        <span class="rotulo-mini">${esc(papel)}</span>
        <span class="rotulo-mini">${grupo.membros} membro${grupo.membros === 1 ? '' : 's'}</span>
      </div>
      <div class="grupo-cartao__nome">${esc(grupo.nome)}</div>
      ${grupo.descricao ? `<div class="grupo-cartao__descricao">${esc(grupo.descricao)}</div>` : ''}
      <div class="grupo-cartao__rodape">
        <span></span>
        <a class="btn btn--secundario btn--pequeno" href="grupo-detalhes.html?id=${grupo.id}">Acessar Grupo</a>
      </div>
    </div>
  </article>`;
}

async function carregarDestaqueConvite() {
  const destaque = document.getElementById('destaqueConvite');
  try {
    const resposta = await api('/convites');
    const dados = await resposta.json();
    if (!resposta.ok || dados.pendentes.length === 0) {
      destaque.hidden = true;
      atualizarBadgeConvites(0);
      return;
    }
    const primeiro = dados.pendentes[0];
    document.getElementById('destaqueConviteGrupo').textContent = primeiro.grupo.nome;
    document.getElementById('destaqueConviteTexto').textContent =
      primeiro.remetente.nome + ' te convidou para participar deste grupo.';
    destaque.hidden = false;
    atualizarBadgeConvites(dados.pendentes.length);
  } catch (e) {
    destaque.hidden = true;
  }
}

function atualizarBadgeConvites(quantidade) {
  const badge = document.getElementById('contadorConvites');
  badge.textContent = quantidade;
  badge.hidden = quantidade === 0;
}

async function carregarConvites() {
  const lista = document.getElementById('listaConvites');
  lista.innerHTML = '<p class="estado-vazio">Carregando convites...</p>';

  try {
    const resposta = await api('/convites');
    const dados = await resposta.json();
    if (!resposta.ok) {
      lista.innerHTML = '<p class="estado-vazio">Não foi possível carregar os convites.</p>';
      return;
    }

    atualizarBadgeConvites(dados.pendentes.length);
    document.getElementById('contadorMeusGruposLateral').textContent = dados.meus_grupos;
    document.getElementById('contadorEnviados').textContent = dados.convites_enviados_pendentes;

    if (dados.pendentes.length === 0) {
      lista.innerHTML = `<div class="card card--interno estado-vazio-grupo">
        <p class="estado-vazio-grupo__titulo">Nenhum convite pendente no momento.</p>
        <p class="estado-vazio-grupo__texto">Quando alguém te convidar para um grupo privado, a solicitação aparece aqui.</p>
      </div>`;
      return;
    }

    lista.innerHTML = dados.pendentes.map(htmlCartaoConvite).join('');
    lista.querySelectorAll('[data-aceitar]').forEach(function (botao) {
      botao.addEventListener('click', function () { responderConvite(botao, true); });
    });
    lista.querySelectorAll('[data-recusar]').forEach(function (botao) {
      botao.addEventListener('click', function () { responderConvite(botao, false); });
    });
  } catch (e) {
    lista.innerHTML = '<p class="estado-vazio">Não foi possível conectar à API.</p>';
  }
}

function htmlCartaoConvite(convite) {
  return `<article class="card convite-cartao">
    <div class="convite-cartao__topo">
      <span class="rotulo-mini">${esc(convite.remetente.nome)} convidou você</span>
      <span class="rotulo-mini">${convite.grupo.membros} membro${convite.grupo.membros === 1 ? '' : 's'}</span>
    </div>
    <h3 class="convite-cartao__titulo">${esc(convite.grupo.nome)}</h3>
    ${convite.grupo.descricao ? `<p class="convite-cartao__texto">${esc(convite.grupo.descricao)}</p>` : ''}
    <div class="convite-cartao__acoes">
      <button type="button" class="btn btn--primario btn--pequeno" data-aceitar="${convite.id}">Aceitar</button>
      <button type="button" class="btn btn--secundario btn--pequeno" data-recusar="${convite.id}">Recusar</button>
    </div>
  </article>`;
}

async function responderConvite(botao, aceito) {
  const id = botao.closest('[data-aceitar], [data-recusar]')
    ? botao.getAttribute('data-aceitar') || botao.getAttribute('data-recusar')
    : null;
  botao.disabled = true;
  try {
    const resposta = await api('/convites/' + id, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ aceito: aceito })
    });
    const dados = await resposta.json();
    if (!resposta.ok) {
      mostrarToast(dados.erro || 'Não foi possível responder o convite.');
      botao.disabled = false;
      return;
    }
    mostrarToast(aceito ? 'Convite aceito! Você entrou no grupo.' : 'Convite recusado.');
    carregarConvites();
  } catch (e) {
    mostrarToast('Não foi possível conectar à API.');
    botao.disabled = false;
  }
}

function esc(s) {
  const div = document.createElement('div');
  div.textContent = s == null ? '' : s;
  return div.innerHTML;
}
