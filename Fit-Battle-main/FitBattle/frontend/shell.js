const ANO_RODAPE = 2026;
const ATRASO_BUSCA_MS = 300;
const MINIMO_BUSCA = 2;
const XP_POR_NIVEL = 250;

const ITENS_NAVEGACAO = [
  { id: 'feed', rotulo: 'Feed', href: 'feed.html' },
  { id: 'ranking', rotulo: 'Ranking', href: 'ranking.html' },
  { id: 'registrar', rotulo: 'Registrar Treino', href: 'registrar-treino.html' },
  { id: 'desafios', rotulo: '1v1', href: 'desafio.html' },
  { id: 'grupo', rotulo: 'Grupo', href: 'grupo.html' },
  { id: 'metas', rotulo: 'Metas', href: 'metas.html' },
  { id: 'perfil', rotulo: 'Perfil', href: 'perfil.html' }
];

const DIVISOES = {
  iniciante: 'Bronze',
  intermediario: 'Silver',
  avancado: 'Gold',
  profissional: 'Platinum',
  elite: 'Diamond'
};

const ICONES = {
  raio: '<svg viewBox="0 0 24 24" aria-hidden="true"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
  busca: '<svg class="busca__icone" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.35-4.35"/></svg>',
  sino: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></svg>',
  menu: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/></svg>'
};

function criarElemento(tag, atributos, filhos) {
  const elemento = document.createElement(tag);
  Object.keys(atributos || {}).forEach(function (chave) {
    const valor = atributos[chave];
    if (valor === false || valor === null || valor === undefined) return;
    if (chave === 'texto') elemento.textContent = valor;
    else if (chave === 'html') elemento.innerHTML = valor;
    else if (chave === 'classe') elemento.className = valor;
    else elemento.setAttribute(chave, valor === true ? '' : valor);
  });
  (filhos || []).forEach(function (filho) {
    if (filho) elemento.appendChild(filho);
  });
  return elemento;
}

function nivelNumerico(xp) {
  return 1 + Math.floor(Math.max(0, Number(xp) || 0) / XP_POR_NIVEL);
}

function nomeDivisao(usuario) {
  return (DIVISOES[usuario && usuario.nivel] || DIVISOES.iniciante) + ' Division';
}

function iniciais(nome) {
  const partes = String(nome || '').trim().split(/\s+/).filter(Boolean);
  if (partes.length === 0) return '?';
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
}

function urlFoto(caminho) {
  if (!caminho) return null;
  return caminho.indexOf('http') === 0 ? caminho : ORIGEM_API + caminho;
}

function criarAvatar(usuario, opcoes) {
  const config = opcoes || {};
  const classes = ['avatar'];
  if (config.tamanho) classes.push('avatar--' + config.tamanho);
  const avatar = criarElemento('span', { classe: classes.join(' '), 'aria-hidden': 'true' });
  const foto = urlFoto(usuario && usuario.foto);
  if (foto) {
    avatar.style.backgroundImage = 'url("' + foto.replace(/"/g, '%22') + '")';
  } else {
    avatar.textContent = iniciais(usuario && usuario.nome);
  }
  if (config.comNivel) {
    avatar.appendChild(criarElemento('span', { classe: 'avatar__nivel', texto: 'L' + nivelNumerico(usuario && usuario.xp) }));
  }
  return avatar;
}

function mostrarToast(mensagem) {
  let area = document.querySelector('.area-toast');
  if (!area) {
    area = criarElemento('div', { classe: 'area-toast', role: 'status', 'aria-live': 'polite' });
    document.body.appendChild(area);
  }
  const toast = criarElemento('div', { classe: 'toast', texto: mensagem });
  area.appendChild(toast);
  setTimeout(function () { toast.remove(); }, 3200);
}

function ligarMenuFlutuante(botao, painel) {
  function fechar() {
    painel.hidden = true;
    botao.setAttribute('aria-expanded', 'false');
  }
  function alternar() {
    const abrir = painel.hidden;
    document.querySelectorAll('.menu-flutuante').forEach(function (outro) { outro.hidden = true; });
    document.querySelectorAll('[aria-haspopup]').forEach(function (b) { b.setAttribute('aria-expanded', 'false'); });
    painel.hidden = !abrir;
    botao.setAttribute('aria-expanded', abrir ? 'true' : 'false');
  }
  botao.addEventListener('click', function (evento) {
    evento.stopPropagation();
    alternar();
  });
  painel.addEventListener('click', function (evento) { evento.stopPropagation(); });
  document.addEventListener('click', fechar);
  document.addEventListener('keydown', function (evento) {
    if (evento.key === 'Escape' && !painel.hidden) {
      fechar();
      botao.focus();
    }
  });
  return { fechar: fechar };
}

function montarBusca() {
  const campo = criarElemento('input', {
    classe: 'busca__campo',
    type: 'search',
    id: 'busca-global',
    placeholder: 'Buscar amigos ou treinos...',
    autocomplete: 'off',
    'aria-label': 'Buscar amigos ou treinos'
  });
  const resultados = criarElemento('ul', { classe: 'menu-flutuante busca__resultados', hidden: true });
  const caixa = criarElemento('div', { classe: 'busca' }, [criarElemento('span', { html: ICONES.busca }).firstChild, campo, resultados]);

  let temporizador = null;
  let sequencia = 0;

  function fechar() { resultados.hidden = true; }

  function mostrarAviso(texto) {
    resultados.replaceChildren(criarElemento('li', { classe: 'busca__aviso', texto: texto }));
    resultados.hidden = false;
  }

  function mostrarResultados(usuarios) {
    if (usuarios.length === 0) return mostrarAviso('Nenhum atleta encontrado.');
    const itens = usuarios.map(function (u) {
      const detalhe = [nomeDivisao(u), u.cidade].filter(Boolean).join(' • ');
      const item = criarElemento('button', { classe: 'busca__item', type: 'button' }, [
        criarAvatar(u, { tamanho: 'pequeno' }),
        criarElemento('span', {}, [
          criarElemento('span', { classe: 'busca__nome', texto: u.nome }),
          criarElemento('span', { classe: 'busca__detalhe', texto: detalhe })
        ])
      ]);
      item.addEventListener('click', function () {
        fechar();
        mostrarToast('Perfis públicos de outros atletas chegam em breve.');
      });
      return criarElemento('li', {}, [item]);
    });
    resultados.replaceChildren.apply(resultados, itens);
    resultados.hidden = false;
  }

  async function buscar(termo) {
    const minha = ++sequencia;
    try {
      const resposta = await api('/usuarios/busca?nome=' + encodeURIComponent(termo));
      if (minha !== sequencia) return;
      if (!resposta.ok) return mostrarAviso('Não foi possível buscar agora.');
      mostrarResultados(await resposta.json());
    } catch (e) {
      if (minha === sequencia) mostrarAviso('Não foi possível conectar à API.');
    }
  }

  campo.addEventListener('input', function () {
    clearTimeout(temporizador);
    const termo = campo.value.trim();
    if (termo.length < MINIMO_BUSCA) {
      sequencia++;
      return fechar();
    }
    temporizador = setTimeout(function () { buscar(termo); }, ATRASO_BUSCA_MS);
  });
  campo.addEventListener('keydown', function (evento) {
    if (evento.key === 'Escape') {
      fechar();
      campo.blur();
    }
  });
  document.addEventListener('click', function (evento) {
    if (!caixa.contains(evento.target)) fechar();
  });

  return caixa;
}

function montarNavegacao(paginaAtiva) {
  const links = ITENS_NAVEGACAO.map(function (item) {
    return criarElemento('a', {
      classe: 'nav-principal__link',
      href: item.href,
      texto: item.rotulo,
      'aria-current': item.id === paginaAtiva ? 'page' : false
    });
  });
  return criarElemento('nav', { classe: 'nav-principal', id: 'nav-principal', 'aria-label': 'Navegação principal' }, links);
}

function montarNotificacoes() {
  const botao = criarElemento('button', {
    classe: 'botao-icone',
    type: 'button',
    'aria-label': 'Notificações',
    'aria-haspopup': 'true',
    'aria-expanded': 'false',
    html: ICONES.sino
  });
  const painel = criarElemento('div', { classe: 'menu-flutuante notificacoes__painel', hidden: true }, [
    criarElemento('p', { classe: 'notificacoes__titulo', texto: 'Notificações' }),
    criarElemento('p', { classe: 'notificacoes__vazio', texto: 'Você não tem notificações no momento.' })
  ]);
  ligarMenuFlutuante(botao, painel);
  return criarElemento('div', { classe: 'seletor' }, [botao, painel]);
}

function montarUsuarioAtual(usuario) {
  const divisao = nomeDivisao(usuario);
  const botao = criarElemento('button', {
    classe: 'usuario-atual',
    type: 'button',
    'aria-haspopup': 'true',
    'aria-expanded': 'false',
    'aria-label': 'Menu do usuário ' + usuario.nome
  }, [
    criarAvatar(usuario, { comNivel: true }),
    criarElemento('span', { classe: 'usuario-atual__texto' }, [
      criarElemento('span', { classe: 'usuario-atual__nome', texto: usuario.nome }),
      criarElemento('span', {
        classe: 'usuario-atual__divisao' + (usuario.nivel === 'avancado' ? ' usuario-atual__divisao--ouro' : ''),
        texto: divisao
      })
    ])
  ]);

  const sair = criarElemento('button', { classe: 'menu-flutuante__item menu-flutuante__item--perigo', type: 'button', texto: 'Sair' });
  sair.addEventListener('click', encerrarSessao);
  const painel = criarElemento('div', { classe: 'menu-flutuante usuario__painel', hidden: true }, [
    criarElemento('a', { classe: 'menu-flutuante__item', href: 'perfil.html', texto: 'Meu Perfil' }),
    sair
  ]);
  ligarMenuFlutuante(botao, painel);
  return criarElemento('div', { classe: 'seletor', 'data-usuario-atual': '' }, [botao, painel]);
}

function montarHeader(usuario, paginaAtiva) {
  const marca = criarElemento('a', { classe: 'marca', href: 'feed.html', 'aria-label': 'FitBattle, ir para o feed' }, [
    criarElemento('span', { html: ICONES.raio }).firstChild,
    criarElemento('span', {}, [
      document.createTextNode('Fit'),
      criarElemento('span', { classe: 'marca__battle', texto: 'Battle' })
    ])
  ]);

  const nav = montarNavegacao(paginaAtiva);
  const botaoMenu = criarElemento('button', {
    classe: 'botao-icone botao-menu',
    type: 'button',
    'aria-label': 'Abrir menu de navegação',
    'aria-controls': 'nav-principal',
    'aria-expanded': 'false',
    html: ICONES.menu
  });
  botaoMenu.addEventListener('click', function () {
    const aberto = nav.classList.toggle('aberto');
    botaoMenu.setAttribute('aria-expanded', aberto ? 'true' : 'false');
  });

  const acoes = criarElemento('div', { classe: 'app-header__acoes' }, [
    montarNotificacoes(),
    montarUsuarioAtual(usuario),
    botaoMenu
  ]);

  const interno = criarElemento('div', { classe: 'app-header__interno' }, [marca, montarBusca(), nav, acoes]);
  return criarElemento('header', { classe: 'app-header' }, [interno]);
}

function montarFooter() {
  function linkEmBreve(texto) {
    const link = criarElemento('a', { href: '#', texto: texto });
    link.addEventListener('click', function (evento) {
      evento.preventDefault();
      mostrarToast(texto + ' estará disponível em breve.');
    });
    return link;
  }

  const marca = criarElemento('a', { classe: 'marca marca--pequena', href: 'feed.html' }, [
    criarElemento('span', { html: ICONES.raio }).firstChild,
    criarElemento('span', {}, [
      document.createTextNode('Fit'),
      criarElemento('span', { classe: 'marca__battle', texto: 'Battle' })
    ])
  ]);

  const links = criarElemento('nav', { classe: 'app-footer__links', 'aria-label': 'Links do rodapé' }, [
    linkEmBreve('Regras e Pontuação'),
    criarElemento('a', { href: 'termos.html#termo-uso', texto: 'Termos' }),
    linkEmBreve('Suporte')
  ]);

  const interno = criarElemento('div', { classe: 'app-footer__interno' }, [
    criarElemento('div', { classe: 'app-footer__marca' }, [
      marca,
      criarElemento('span', { texto: '© ' + ANO_RODAPE + ' Gamified Fitness & Gym Rankings' })
    ]),
    links
  ]);
  return criarElemento('footer', { classe: 'app-footer' }, [interno]);
}

function atualizarUsuarioNoHeader(usuario) {
  const atual = document.querySelector('[data-usuario-atual]');
  if (atual) atual.replaceWith(montarUsuarioAtual(usuario));
}

async function iniciarShell() {
  const pagina = document.body.dataset.pagina;
  if (!pagina) return;

  const usuario = exigirLogin();
  if (!usuario) return;

  const principal = document.querySelector('main');
  if (principal && !principal.id) principal.id = 'conteudo';

  document.body.prepend(criarElemento('a', { classe: 'link-pular', href: '#conteudo', texto: 'Ir para o conteúdo' }));
  document.body.insertBefore(montarHeader(usuario, pagina), document.body.children[1]);
  document.body.appendChild(montarFooter());

  try {
    const atualizado = await atualizarSessaoPelaApi();
    if (atualizado) {
      atualizarUsuarioNoHeader(atualizado);
      document.dispatchEvent(new CustomEvent('fitbattle:usuario', { detail: atualizado }));
    }
  } catch (e) {}
}

document.addEventListener('DOMContentLoaded', iniciarShell);
