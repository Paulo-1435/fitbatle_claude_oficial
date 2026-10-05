document.addEventListener('DOMContentLoaded', async function () {
  const usuarioLogado = exigirLogin();
  if (!usuarioLogado) return;

  const codigo = new URLSearchParams(window.location.search).get('codigo');
  const titulo = document.getElementById('entrarGrupoTitulo');
  const texto = document.getElementById('entrarGrupoTexto');
  const botao = document.getElementById('entrarGrupoBotao');

  if (!codigo) {
    titulo.textContent = 'Código de convite não informado.';
    texto.textContent = 'Verifique se o link que você recebeu está completo.';
    botao.hidden = false;
    botao.textContent = 'Ver meus grupos';
    botao.href = 'grupo.html';
    return;
  }

  try {
    const resposta = await api('/grupos/entrar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ codigo: codigo })
    });
    const dados = await resposta.json();

    if (!resposta.ok) {
      titulo.textContent = 'Não foi possível entrar no grupo';
      texto.textContent = dados.erro || 'Tente novamente mais tarde.';
      botao.hidden = false;
      botao.textContent = 'Ver meus grupos';
      botao.href = 'grupo.html';
      return;
    }

    titulo.textContent = 'Você entrou em ' + dados.grupo.nome + '!';
    texto.textContent = 'Agora você já pontua no ranking interno deste grupo.';
    botao.hidden = false;
    botao.textContent = 'Acessar o grupo';
    botao.href = 'grupo-detalhes.html?id=' + dados.grupo.id;
  } catch (e) {
    titulo.textContent = 'Não foi possível conectar à API.';
    texto.textContent = 'Verifique sua conexão e tente novamente.';
    botao.hidden = false;
    botao.textContent = 'Ver meus grupos';
    botao.href = 'grupo.html';
  }
});
