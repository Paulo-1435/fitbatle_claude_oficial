document.addEventListener('DOMContentLoaded', function () {
  const usuarioLogado = exigirLogin();
  if (!usuarioLogado) return;

  const nome = document.getElementById('nomeGrupo');
  const descricao = document.getElementById('descricaoGrupo');

  nome.addEventListener('input', function () {
    document.getElementById('contadorNome').textContent = nome.value.length;
  });
  descricao.addEventListener('input', function () {
    document.getElementById('contadorDescricao').textContent = descricao.value.length;
  });

  document.getElementById('formCriarGrupo').addEventListener('submit', async function (evento) {
    evento.preventDefault();
    const erro = document.getElementById('erroCriarGrupo');
    erro.textContent = '';
    const botao = document.getElementById('btnSalvarGrupo');
    botao.disabled = true;

    try {
      const resposta = await api('/grupos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nome: nome.value.trim(), descricao: descricao.value.trim() })
      });
      const dados = await resposta.json();
      if (!resposta.ok) {
        erro.textContent = dados.erro || 'Não foi possível criar o grupo.';
        return;
      }
      mostrarToast('Grupo criado!');
      window.location.href = 'grupo-detalhes.html?id=' + dados.grupo.id;
    } catch (e) {
      erro.textContent = 'Não foi possível conectar à API.';
    } finally {
      botao.disabled = false;
    }
  });
});
