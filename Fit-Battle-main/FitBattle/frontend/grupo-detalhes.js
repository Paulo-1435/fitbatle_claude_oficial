let usuarioLogado = null;
let idGrupo = null;

document.addEventListener('DOMContentLoaded', function () {
  usuarioLogado = exigirLogin();
  if (!usuarioLogado) return;

  idGrupo = new URLSearchParams(window.location.search).get('id');
  if (!idGrupo) {
    window.location.href = 'grupo.html';
    return;
  }

  document.getElementById('btnConvidarMembro').addEventListener('click', function () {
    window.location.href = 'grupo-convidar.html?id=' + idGrupo;
  });

  document.body.addEventListener('click', function (evento) {
    const alvo = evento.target.closest('[data-em-breve]');
    if (!alvo) return;
    mostrarToast(alvo.getAttribute('data-em-breve') + ' estará disponível em breve.');
  });

  carregarDetalhe();
  carregarMembros();
  carregarRanking();
});

async function carregarDetalhe() {
  try {
    const resposta = await api('/grupos/' + idGrupo);
    const grupo = await resposta.json();
    if (!resposta.ok) {
      mostrarToast(grupo.erro || 'Não foi possível carregar o grupo.');
      window.location.href = 'grupo.html';
      return;
    }

    document.title = 'FitBattle - ' + grupo.nome;
    document.getElementById('iconeGrupo').textContent = iniciais(grupo.nome);
    document.getElementById('nomeGrupo').textContent = grupo.nome;
    document.getElementById('descricaoGrupo').textContent = grupo.descricao || '';
    document.getElementById('infoGrupo').textContent =
      grupo.membros + ' membro' + (grupo.membros === 1 ? '' : 's') + ' participante' + (grupo.membros === 1 ? '' : 's') +
      ' · Criado em ' + formatarMesAno(grupo.data_criacao);

    document.getElementById('btnConvidarMembro').hidden = false;
  } catch (e) {
    mostrarToast('Não foi possível conectar à API.');
  }
}

async function carregarMembros() {
  const lista = document.getElementById('listaMembros');
  try {
    const resposta = await api('/grupos/' + idGrupo + '/membros');
    const membros = await resposta.json();
    if (!resposta.ok) {
      lista.innerHTML = '<li class="estado-vazio">Não foi possível carregar os membros.</li>';
      return;
    }

    document.getElementById('totalMembros').textContent = membros.length + ' total';
    lista.innerHTML = membros.map(function (membro) {
      return `<li class="grupo-membro-item">
        ${htmlAvatar(membro)}
        <div class="grupo-membro-item__texto">
          <span class="grupo-membro-item__nome">${esc(membro.nome)}</span>
          <span class="grupo-membro-item__handle">@${esc(membro.handle)}</span>
        </div>
        <span class="badge${membro.papel === 'admin' ? ' badge--destaque' : ''}">${membro.papel === 'admin' ? 'Admin' : 'Membro'}</span>
      </li>`;
    }).join('');
  } catch (e) {
    lista.innerHTML = '<li class="estado-vazio">Não foi possível conectar à API.</li>';
  }
}

function htmlAvatar(usuario) {
  const foto = urlFoto(usuario.foto);
  if (foto) {
    return `<span class="avatar" aria-hidden="true" style="background-image:url('${foto.replace(/'/g, "%27")}')"></span>`;
  }
  return `<span class="avatar" aria-hidden="true">${esc(iniciais(usuario.nome))}</span>`;
}

async function carregarRanking() {
  const podio = document.getElementById('podioGrupo');
  const corpo = document.getElementById('tabelaRankingGrupoCorpo');
  try {
    const resposta = await api('/grupos/' + idGrupo + '/ranking');
    const dados = await resposta.json();
    if (!resposta.ok) {
      podio.innerHTML = '<p class="estado-vazio">Não foi possível carregar o ranking.</p>';
      corpo.innerHTML = '<tr><td colspan="4" class="estado-vazio">Não foi possível carregar o ranking.</td></tr>';
      return;
    }

    if (dados.length === 0) {
      podio.innerHTML = '<p class="estado-vazio">Ninguém pontuou neste grupo ainda.</p>';
      corpo.innerHTML = '<tr><td colspan="4" class="estado-vazio">Ninguém pontuou neste grupo ainda.</td></tr>';
      return;
    }

    podio.innerHTML = dados.slice(0, 3).map(htmlVagaPodio).join('');
    corpo.innerHTML = dados.map(htmlLinhaTabela).join('');
  } catch (e) {
    podio.innerHTML = '<p class="estado-vazio">Não foi possível conectar à API.</p>';
    corpo.innerHTML = '<tr><td colspan="4" class="estado-vazio">Não foi possível conectar à API.</td></tr>';
  }
}

function htmlVagaPodio(item) {
  const eu = usuarioLogado && item.id_usuario === usuarioLogado.id;
  return `<div class="podio-vaga podio-vaga--${item.posicao}${eu ? ' podio-vaga--eu' : ''}">
    <span class="podio-vaga__pos">${item.posicao}º</span>
    <span class="avatar" aria-hidden="true">${esc(iniciais(item.nome))}</span>
    <span class="podio-vaga__nome">${esc(item.nome)}${eu ? ' (você)' : ''}</span>
    <span class="podio-vaga__pontos">${item.pontuacao_total} xp</span>
  </div>`;
}

function htmlLinhaTabela(item) {
  const eu = usuarioLogado && item.id_usuario === usuarioLogado.id;
  return `<tr class="${eu ? 'linha--eu' : ''}">
    <td class="ranking-tabela__pos">${item.posicao}º</td>
    <td>
      <div class="ranking-tabela__atleta">
        <span class="avatar avatar--pequeno" aria-hidden="true">${esc(iniciais(item.nome))}</span>
        <span>${esc(item.nome)}${eu ? ' (você)' : ''}</span>
      </div>
    </td>
    <td class="ranking-tabela__pontos">${item.pontuacao_total} xp</td>
    <td>${eu ? '—' : '<button type="button" class="btn btn--secundario btn--pequeno" data-em-breve="Perfis públicos de outros atletas">Ver Perfil</button>'}</td>
  </tr>`;
}

function formatarMesAno(iso) {
  const data = new Date(iso);
  return data.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
}

function esc(s) {
  const div = document.createElement('div');
  div.textContent = s == null ? '' : s;
  return div.innerHTML;
}
