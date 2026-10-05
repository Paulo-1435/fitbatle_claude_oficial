const ATRASO_BUSCA_CONVITE_MS = 300;
const MINIMO_BUSCA_CONVITE = 2;

let usuarioLogado = null;
let idGrupo = null;
let temporizadorBusca = null;
let sequenciaBusca = 0;

document.addEventListener('DOMContentLoaded', function () {
  usuarioLogado = exigirLogin();
  if (!usuarioLogado) return;

  idGrupo = new URLSearchParams(window.location.search).get('id');
  if (!idGrupo) {
    window.location.href = 'grupo.html';
    return;
  }

  document.getElementById('linkVoltarGrupo').href = 'grupo-detalhes.html?id=' + idGrupo;
  document.getElementById('btnConcluirConvite').href = 'grupo-detalhes.html?id=' + idGrupo;

  document.getElementById('buscaConvidar').addEventListener('input', function () {
    clearTimeout(temporizadorBusca);
    const termo = this.value.trim();
    if (termo.length < MINIMO_BUSCA_CONVITE) {
      sequenciaBusca++;
      document.getElementById('resultadosConvite').innerHTML = '';
      document.getElementById('contagemResultados').textContent = '';
      return;
    }
    temporizadorBusca = setTimeout(function () { buscar(termo); }, ATRASO_BUSCA_CONVITE_MS);
  });

  document.getElementById('btnCopiarLink').addEventListener('click', copiarLink);
  document.getElementById('btnRegenerarLink').addEventListener('click', regenerarLink);

  carregarGrupo();
});

async function carregarGrupo() {
  try {
    const resposta = await api('/grupos/' + idGrupo);
    const grupo = await resposta.json();
    if (!resposta.ok) {
      mostrarToast(grupo.erro || 'Não foi possível carregar o grupo.');
      window.location.href = 'grupo.html';
      return;
    }
    document.getElementById('nomeGrupoConvite').textContent = grupo.nome;

    if (grupo.meu_papel === 'admin') {
      document.getElementById('blocoLink').hidden = false;
      carregarLink();
    }
  } catch (e) {
    mostrarToast('Não foi possível conectar à API.');
  }
}

async function carregarLink() {
  try {
    const resposta = await api('/grupos/' + idGrupo + '/convite');
    const dados = await resposta.json();
    if (resposta.ok) {
      document.getElementById('linkConvite').value = montarLink(dados.codigo);
    }
  } catch (e) {}
}

function montarLink(codigo) {
  return window.location.origin + '/entrar-grupo.html?codigo=' + codigo;
}

async function regenerarLink() {
  try {
    const resposta = await api('/grupos/' + idGrupo + '/convite/regenerar', { method: 'POST' });
    const dados = await resposta.json();
    if (!resposta.ok) {
      mostrarToast(dados.erro || 'Não foi possível gerar um novo link.');
      return;
    }
    document.getElementById('linkConvite').value = montarLink(dados.codigo);
    mostrarToast('Novo link gerado. O anterior deixou de funcionar.');
  } catch (e) {
    mostrarToast('Não foi possível conectar à API.');
  }
}

function copiarLink() {
  const campo = document.getElementById('linkConvite');
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(campo.value).then(function () {
      mostrarToast('Link copiado!');
    }).catch(function () {
      campo.select();
    });
  } else {
    campo.select();
  }
}

async function buscar(termo) {
  const minha = ++sequenciaBusca;
  try {
    const resposta = await api('/grupos/' + idGrupo + '/busca-convidar?nome=' + encodeURIComponent(termo));
    if (minha !== sequenciaBusca) return;
    const dados = await resposta.json();
    if (!resposta.ok) {
      document.getElementById('contagemResultados').textContent = '';
      document.getElementById('resultadosConvite').innerHTML = `<li class="estado-vazio">${esc(dados.erro || 'Não foi possível buscar agora.')}</li>`;
      return;
    }
    renderizarResultados(dados);
  } catch (e) {
    if (minha === sequenciaBusca) {
      document.getElementById('resultadosConvite').innerHTML = '<li class="estado-vazio">Não foi possível conectar à API.</li>';
    }
  }
}

function renderizarResultados(usuarios) {
  const contagem = document.getElementById('contagemResultados');
  const lista = document.getElementById('resultadosConvite');

  contagem.textContent = 'Resultados encontrados (' + usuarios.length + ')';

  if (usuarios.length === 0) {
    lista.innerHTML = '<li class="estado-vazio">Nenhum atleta encontrado.</li>';
    return;
  }

  lista.innerHTML = usuarios.map(function (usuario) {
    const local = [usuario.cidade, usuario.estado].filter(Boolean).join(' - ');
    const botao = usuario.convite_pendente
      ? '<button type="button" class="btn btn--secundario btn--pequeno" disabled>✓ Convite Enviado</button>'
      : `<button type="button" class="btn btn--primario btn--pequeno" data-convidar="${usuario.id}">Enviar Convite</button>`;
    return `<li class="convite-resultado-item">
      ${htmlAvatar(usuario)}
      <div class="convite-resultado-item__texto">
        <span class="convite-resultado-item__nome">${esc(usuario.nome)}</span>
        <span class="convite-resultado-item__detalhe">@${esc(usuario.handle)}${local ? ' · ' + esc(local) : ''}</span>
      </div>
      ${botao}
    </li>`;
  }).join('');

  lista.querySelectorAll('[data-convidar]').forEach(function (botao) {
    botao.addEventListener('click', function () { convidar(botao); });
  });
}

function htmlAvatar(usuario) {
  const foto = urlFoto(usuario.foto);
  if (foto) {
    return `<span class="avatar avatar--pequeno" aria-hidden="true" style="background-image:url('${foto.replace(/'/g, "%27")}')"></span>`;
  }
  return `<span class="avatar avatar--pequeno" aria-hidden="true">${esc(iniciais(usuario.nome))}</span>`;
}

async function convidar(botao) {
  botao.disabled = true;
  const idUsuario = parseInt(botao.getAttribute('data-convidar'), 10);
  try {
    const resposta = await api('/grupos/' + idGrupo + '/convites', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_usuario: idUsuario })
    });
    const dados = await resposta.json();
    if (!resposta.ok) {
      mostrarToast(dados.erro || 'Não foi possível enviar o convite.');
      botao.disabled = false;
      return;
    }
    botao.outerHTML = '<button type="button" class="btn btn--secundario btn--pequeno" disabled>✓ Convite Enviado</button>';
    mostrarToast('Convite enviado!');
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
