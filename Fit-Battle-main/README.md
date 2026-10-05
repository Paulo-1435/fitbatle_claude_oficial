# Fit-Battle

Bernardo Nardelli, Cauã Gomes, João Paulo Costa, João Pedro Braga, Miguel Assunção, Henrique Vale.

Plataforma gamificada de treinos. Este repositório contém a API (Flask) e o
frontend web.

## Status do desenvolvimento

**Pronto e testado (end-to-end com MySQL):**

- Cadastro de usuário — `RF01` (frontend `index.html` + API)
- Login — `RF02` (frontend `login.html` + API)
- Manter perfil: ver e editar — `RF03` (frontend `perfil.html` + API: nome, e-mail, bio, idade, cidade, peso, altura)
- Registrar treino — `RF04` (frontend `perfil.html`, botão "+ Novo treino")
- Histórico de treinos — `RF05` (lista de treinos no `perfil.html`)
- Cálculo automático de pontuação — `RF12`
- Atribuição automática de nível por XP — `RF13` (barra de nível no `perfil.html`)
- Consentimento LGPD granular no cadastro (Termo de Uso / Termo de Consentimento):
  caixa com opções marcadas que o usuário desmarca, `frontend/termos.html`,
  gravação por finalidade na tabela `consentimento` e revogação via API
- Regras de idade (art. 14 da LGPD): cadastro bloqueado para menores de 13;
  adolescentes de 13 a 17 anos precisam informar nome e e-mail do responsável
  legal e a autorização, gravados em `usuario.responsavel_*`
- Foto de perfil: upload de arquivo para `backend/uploads/`, prévia e lightbox
- Rankings regional e global — `RF10`, `RF11` (modal no `perfil.html`, lê as
  *views* `vw_ranking_*`); "Ranking Local" do perfil mostra a posição real
- Compartilhar treino: copia um texto pronto para a área de transferência

**Ainda não implementado:** grupos e convites (RF06–08), ranking interno de
grupo (RF09 — depende dos grupos), dashboard de gráficos (RF14), metas (RF15),
desafios (RF16–17), notificações (RF18), busca de perfis/grupos (RF19),
compartilhamento direto em redes sociais (RF20).

**Próximos passos sugeridos:** o "Relatório" de progresso com gráficos (RF14);
depois grupos, convites e metas.

**Pendências no `perfil.html`:** a paleta ainda difere um pouco do
cadastro/login; a busca no topo e o menu (Explorar/Amigos/Grupos) mostram
"em desenvolvimento"; o "Desafios sazonais" da barra lateral é um aviso fixo.

**Ambiente já configurado nesta máquina:** Python 3.12, dependências instaladas,
banco `fitbattle` criado no MySQL local, usuário de app `fitbattle` / `Fitbattle@123`
(senha de exemplo para desenvolvimento local — troque-a em qualquer ambiente
compartilhado ou de produção). Para testar com dados de exemplo, não há mais
uma conta fixa publicada aqui: rode `backend/tests/servidor_dev.py`, que sobe a
API num banco SQLite local já populado com usuários e treinos de teste, ou
cadastre sua própria conta pela tela de cadastro.

## Estrutura

```
FitBattle/
├── frontend/
│   ├── index.html          # tela de cadastro + caixa de consentimento (LGPD)
│   ├── script.js           # cadastro: chama a API via fetch
│   ├── login.html / login.js  # tela de login
│   ├── termos.html         # Termo de Uso + Termo de Consentimento (texto completo)
│   ├── style.css
│   ├── perfil.html / perfil.css / perfil.js  # (ainda mockup)
│   └── ...
└── backend/
    ├── app.py              # cria e sobe a aplicação Flask
    ├── database.py         # instância do SQLAlchemy (objeto db)
    ├── requirements.txt
    ├── routers/
    │   └── routers.py      # mapeia as URLs para o Controller
    ├── controllers/
    │   └── controller.py   # UsuarioController, AtividadeController, ConsentimentoController
    ├── services/
    │   └── service.py      # UsuarioService, AtividadeService, ConsentimentoService
    ├── repositories/
    │   └── repository.py   # único ponto de acesso ao banco
    ├── models/
    │   └── model.py        # tabelas usuario, atividade, consentimento
    └── database/
        └── create_database.sql   # schema completo (MySQL)
```

Fluxo de uma requisição: **routers → controller → service → repository → model → MySQL**.

## Como rodar

### 1. Banco de dados (MySQL 8+)

Rode o script `backend/database/create_database.sql` inteiro. Pelo terminal:

```bash
mysql -u root -p < backend/database/create_database.sql
```

Ou pelo MySQL Workbench: *File > Open SQL Script* > selecione o arquivo >
botão do raio (Execute All).

O script cria o banco `fitbattle`, todas as tabelas e o usuário de aplicação
`fitbattle` / senha `Fitbattle@123` (usado pela API, não pelo root). Essa senha
é só um exemplo para desenvolvimento local; troque-a (e configure `DB_PASSWORD`
com o novo valor) em qualquer ambiente compartilhado ou de produção.

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
python app.py
```

A API sobe em `http://localhost:5000`. Deixe esse terminal aberto enquanto usa
o sistema — se fechar (ou o PC reiniciar), rode `python app.py` de novo.

> O pacote `cryptography` está no `requirements.txt` porque o MySQL 8 usa o
> método de autenticação `caching_sha2_password`, e o PyMySQL precisa dele para
> conectar.

Variáveis de ambiente aceitas (todas opcionais, já vêm com padrão):
`DB_USER` (fitbattle), `DB_PASSWORD` (Fitbattle@123), `DB_HOST` (localhost),
`DB_PORT` (3306), `DB_NAME` (fitbattle), `SECRET_KEY`, `FLASK_DEBUG` (desligado
por padrão; defina como `1` só em desenvolvimento), `CORS_EXTRA_ORIGENS`
(origens extras separadas por vírgula, além de localhost/127.0.0.1/IPs de rede
local, já liberados por padrão).

### 3. Frontend

Abrir `frontend/index.html` no navegador (ou servir com Live Server).

## Endpoints da API

| Método | Rota | Descrição | RF |
|---|---|---|---|
| POST | `/api/usuarios` | Cadastra usuário (nome, email, idade, senha, `aceite_termos`, `consentimentos`) | RF01 |
| POST | `/api/login` | Autentica (email, senha) | RF02 |
| GET | `/api/usuarios/<id>/consentimentos` | Lista os consentimentos LGPD do usuário | — |
| PUT | `/api/usuarios/<id>/consentimentos/<chave>` | Revoga/reativa um consentimento **opcional** (`{"aceito": true/false}`) | — |
| GET | `/api/usuarios` | Lista usuários (`?nome=` filtra) | RF19 |
| GET | `/api/usuarios/<id>` | Busca um usuário | RF03 |
| PUT | `/api/usuarios/<id>` | Atualiza o perfil (nome, e-mail, bio, idade, cidade, peso, altura) | RF03 |
| POST | `/api/usuarios/<id>/foto` | Envia a foto de perfil (multipart, campo `foto`); salva em `backend/uploads/` | RF03 |
| DELETE | `/api/usuarios/<id>` | Exclui usuário | — |
| POST | `/api/usuarios/<id>/atividades` | Registra um treino; calcula a pontuação e atualiza XP/nível | RF04, RF12, RF13 |
| GET | `/api/usuarios/<id>/atividades` | Histórico de treinos do usuário | RF05 |
| GET | `/api/atividades/<id>` | Detalhe de um treino | RF05 |
| DELETE | `/api/atividades/<id>` | Exclui o treino (desconta a pontuação) | — |
| GET | `/api/ranking/global` | Ranking de todos os usuários por XP (`?limite=`) | RF11 |
| GET | `/api/ranking/regional` | Ranking por cidade (`?cidade=...&limite=`) | RF10 |
| GET | `/api/usuarios/<id>/ranking` | Posição do usuário nos rankings global e regional | RF10, RF11 |
| GET | `/api/estatisticas` | Total de usuários e média de XP | RF14 |

As senhas são armazenadas com hash (`werkzeug.security`), nunca em texto puro.

### Cálculo de pontuação (RF12) e nível (RF13)

A cada treino registrado, a pontuação é calculada automaticamente
(`AtividadeService.calcular_pontuacao`) a partir de tempo, distância, carga e
repetições, mais um bônus por tipo de exercício. Essa pontuação é somada ao
`xp` do usuário e o `nivel` é reatribuído pelas faixas em
`FAIXAS_NIVEL` (iniciante → intermediario → avancado → profissional → elite).

### Consentimento LGPD

No cadastro, o `index.html` mostra uma caixa com as finalidades de tratamento
já marcadas. As **obrigatórias** (conta, registro de treinos, histórico, dados
que podem revelar saúde — art. 11 da LGPD, segurança/auditoria) ficam travadas;
as **opcionais** (ranking público, localização, chats, busca, notificações,
compartilhamento) podem ser desmarcadas. O `script.js` envia `aceite_termos` e o
objeto `consentimentos`; o `ConsentimentoService` grava uma linha por finalidade
na tabela `consentimento`. Recusar `ranking_publico` já define
`usuario.perfil_publico = 0`. O usuário pode revogar/reativar qualquer opção
depois via `PUT /api/usuarios/<id>/consentimentos/<chave>`. O texto completo dos
dois termos está em `frontend/termos.html`.

### Foto de perfil (upload de arquivo)

O modal "Editar perfil" tem um botão **Escolher foto**. A imagem (PNG, JPG ou
WEBP, até 3 MB) é enviada em `multipart/form-data` para
`POST /api/usuarios/<id>/foto`. O Flask salva o arquivo em `backend/uploads/`
com um nome único (`usuario_<id>_<timestamp>.<ext>`), apaga a foto anterior do
usuário e grava o caminho `/uploads/...` na coluna `usuario.foto`. Os arquivos
são servidos pela rota `GET /uploads/<nome>`. A pasta `backend/uploads/` está no
`.gitignore` (não versionar fotos de usuário).

### Faixa etária (art. 14 da LGPD)

`UsuarioService._validar_faixa_etaria` aplica no cadastro:

- **< 13 anos:** cadastro recusado (400).
- **13 a 17 anos:** obrigatório `responsavel` (`nome`, `email`) e
  `autorizacao_responsavel = true`; o `index.html` mostra esses campos
  automaticamente quando a idade digitada está nessa faixa. Os dados ficam em
  `usuario.responsavel_nome / responsavel_email / responsavel_autorizado_em`.
- **>= 18 anos:** fluxo normal.

Por decisão do projeto, menores de 18 **participam** dos rankings e da busca
(a autorização do responsável, dada no cadastro, cobre isso) — o texto de
`termos.html` foi ajustado para refletir essa regra.
