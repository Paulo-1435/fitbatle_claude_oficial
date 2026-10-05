let usuarioLogado = null;

document.addEventListener('DOMContentLoaded', function () {
  usuarioLogado = exigirLogin();
  if (!usuarioLogado) return;

  aplicarFoto('avatarMini', usuarioLogado.foto);
  carregarConsentimentos();
});

async function carregarConsentimentos() {
  const erro = document.getElementById('erroPrivacidade');
  erro.textContent = '';
  try {
    const resposta = await api(`/usuarios/${usuarioLogado.id}/consentimentos`);
    if (!resposta.ok) throw new Error('falha');
    const registros = await resposta.json();
    renderizarConsentimentos(registros);
  } catch (e) {
    erro.textContent = 'Não foi possível carregar suas preferências. A API está rodando?';
  }
}

function renderizarConsentimentos(registros) {
  const obrigatorios = registros.filter(function (r) { return r.obrigatorio; });
  const opcionais = registros.filter(function (r) { return !r.obrigatorio; });

  const listaObrigatorios = document.getElementById('listaObrigatorios');
  const listaOpcionais = document.getElementById('listaOpcionais');
  listaObrigatorios.replaceChildren();
  listaOpcionais.replaceChildren();

  obrigatorios.forEach(function (registro) {
    listaObrigatorios.appendChild(itemFixo(registro));
  });
  opcionais.forEach(function (registro) {
    listaOpcionais.appendChild(itemAlternavel(registro));
  });
}

function itemFixo(registro) {
  const item = document.createElement('div');
  item.className = 'privacidade-item';
  item.innerHTML = `
    <div>
      <span class="privacidade-item-titulo">${esc(registro.descricao)}</span>
      <span class="privacidade-item-legenda">Sempre ativo enquanto sua conta existir</span>
    </div>
    <span class="privacidade-badge-fixo">Sempre ativo</span>
  `;
  return item;
}

function itemAlternavel(registro) {
  const item = document.createElement('div');
  item.className = 'privacidade-item';

  const id = 'consent-' + registro.chave;
  item.innerHTML = `
    <div>
      <label class="privacidade-item-titulo" for="${id}">${esc(registro.descricao)}</label>
      <span class="privacidade-item-legenda" id="${id}-legenda"></span>
    </div>
    <label class="privacidade-switch">
      <input type="checkbox" id="${id}" ${registro.aceito ? 'checked' : ''}>
      <span class="privacidade-switch-track"></span>
    </label>
  `;

  const legenda = item.querySelector('#' + id + '-legenda');
  legenda.textContent = registro.aceito ? 'Ativado' : 'Desativado';

  const caixa = item.querySelector('input');
  caixa.addEventListener('change', function () {
    salvarConsentimento(registro.chave, caixa, legenda);
  });

  return item;
}

async function salvarConsentimento(chave, caixa, legenda) {
  const aceito = caixa.checked;
  const anterior = !aceito;
  caixa.disabled = true;

  try {
    const resposta = await api(`/usuarios/${usuarioLogado.id}/consentimentos/${chave}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ aceito: aceito })
    });
    const dados = await resposta.json().catch(function () { return {}; });

    if (!resposta.ok) {
      caixa.checked = anterior;
      mostrarToast(dados.erro || 'Não foi possível salvar essa preferência.');
      return;
    }

    legenda.textContent = aceito ? 'Ativado' : 'Desativado';
    mostrarToast('Preferência salva.');
  } catch (e) {
    caixa.checked = anterior;
    mostrarToast('Não foi possível conectar à API.');
  } finally {
    caixa.disabled = false;
  }
}

function aplicarFoto(id, url) {
  const el = document.getElementById(id);
  if (!el) return;
  const src = urlFoto(url);
  el.style.backgroundImage = src ? `url("${src}")` : 'none';
}

function urlFoto(caminho) {
  if (!caminho) return null;
  return caminho.indexOf('http') === 0 ? caminho : ORIGEM_API + caminho;
}

function mostrarToast(mensagem) {
  const t = document.getElementById('toast');
  t.textContent = mensagem;
  t.classList.add('mostrar');
  clearTimeout(mostrarToast._timer);
  mostrarToast._timer = setTimeout(function () { t.classList.remove('mostrar'); }, 2600);
}

function esc(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}
