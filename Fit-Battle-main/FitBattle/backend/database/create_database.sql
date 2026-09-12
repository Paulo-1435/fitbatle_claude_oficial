DROP DATABASE IF EXISTS fitbattle;
CREATE DATABASE fitbattle
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE fitbattle;

CREATE TABLE usuario (
    id_usuario     INT AUTO_INCREMENT PRIMARY KEY,
    nome           VARCHAR(120)  NOT NULL,
    email          VARCHAR(150)  NOT NULL UNIQUE,
    senha          VARCHAR(255)  NOT NULL,
    idade          TINYINT UNSIGNED,
    peso           DECIMAL(5,2),
    altura         DECIMAL(3,2),
    cidade         VARCHAR(100),
    estado         CHAR(2),
    foto           VARCHAR(255),
    descricao      VARCHAR(300),
    responsavel_nome          VARCHAR(120),
    responsavel_email         VARCHAR(150),
    responsavel_autorizado_em DATETIME,
    nivel          ENUM('iniciante','intermediario','avancado','profissional','elite')
                       NOT NULL DEFAULT 'iniciante',
    xp             INT NOT NULL DEFAULT 0,
    perfil_publico TINYINT(1) NOT NULL DEFAULT 1,
    criado_em      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_usuario_cidade (cidade),
    INDEX idx_usuario_estado (estado),
    INDEX idx_usuario_xp (xp)
) ENGINE=InnoDB;

CREATE TABLE atividade (
    id_atividade   INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario     INT NOT NULL,
    tipo           VARCHAR(60) NOT NULL,
    titulo         VARCHAR(120),
    descricao      VARCHAR(500),
    tempo_min      INT UNSIGNED,
    distancia_km   DECIMAL(6,2),
    carga_kg       DECIMAL(6,2),
    repeticoes     INT UNSIGNED,
    pontuacao      INT NOT NULL DEFAULT 0,
    data_registro  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_atividade_usuario
        FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
        ON DELETE CASCADE,
    INDEX idx_atividade_usuario_data (id_usuario, data_registro)
) ENGINE=InnoDB;

CREATE TABLE postagem (
    id_postagem    INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario     INT NOT NULL,
    texto          VARCHAR(1000) NOT NULL,
    foto           VARCHAR(255),
    data_registro  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_postagem_usuario
        FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
        ON DELETE CASCADE,
    INDEX idx_postagem_usuario_data (id_usuario, data_registro)
) ENGINE=InnoDB;

CREATE TABLE curtida (
    id_curtida     INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario     INT NOT NULL,
    tipo_alvo      ENUM('atividade','postagem') NOT NULL,
    id_alvo        INT NOT NULL,
    data_registro  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_curtida_usuario
        FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    UNIQUE KEY uq_curtida_usuario_alvo (id_usuario, tipo_alvo, id_alvo),
    INDEX idx_curtida_alvo (tipo_alvo, id_alvo)
) ENGINE=InnoDB;

CREATE TABLE comentario (
    id_comentario  INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario     INT NOT NULL,
    tipo_alvo      ENUM('atividade','postagem') NOT NULL,
    id_alvo        INT NOT NULL,
    texto          VARCHAR(500) NOT NULL,
    data_registro  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_comentario_usuario
        FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    INDEX idx_comentario_alvo (tipo_alvo, id_alvo)
) ENGINE=InnoDB;

CREATE TABLE consentimento (
    id_consentimento INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario       INT NOT NULL,
    chave            VARCHAR(40)  NOT NULL,
    descricao        VARCHAR(200) NOT NULL,
    obrigatorio      TINYINT(1)   NOT NULL DEFAULT 0,
    aceito           TINYINT(1)   NOT NULL DEFAULT 1,
    data_registro    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao DATETIME     NULL,
    CONSTRAINT fk_consent_usuario
        FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    UNIQUE KEY uq_consent_usuario_chave (id_usuario, chave)
) ENGINE=InnoDB;

CREATE TABLE grupo (
    id_grupo       INT AUTO_INCREMENT PRIMARY KEY,
    nome           VARCHAR(120) NOT NULL,
    descricao      VARCHAR(300),
    privacidade    ENUM('publico','privado') NOT NULL DEFAULT 'privado',
    codigo_convite CHAR(10) UNIQUE,
    id_criador     INT NOT NULL,
    data_criacao   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_grupo_criador
        FOREIGN KEY (id_criador) REFERENCES usuario(id_usuario)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE grupo_membro (
    id_grupo       INT NOT NULL,
    id_usuario     INT NOT NULL,
    papel          ENUM('admin','membro') NOT NULL DEFAULT 'membro',
    entrou_em      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_grupo, id_usuario),
    CONSTRAINT fk_membro_grupo
        FOREIGN KEY (id_grupo) REFERENCES grupo(id_grupo) ON DELETE CASCADE,
    CONSTRAINT fk_membro_usuario
        FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE convite (
    id_convite     INT AUTO_INCREMENT PRIMARY KEY,
    id_grupo       INT NOT NULL,
    id_remetente   INT NOT NULL,
    id_destinatario INT NOT NULL,
    status         ENUM('pendente','aceito','recusado') NOT NULL DEFAULT 'pendente',
    data_envio     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_resposta  DATETIME NULL,
    CONSTRAINT fk_convite_grupo
        FOREIGN KEY (id_grupo) REFERENCES grupo(id_grupo) ON DELETE CASCADE,
    CONSTRAINT fk_convite_remetente
        FOREIGN KEY (id_remetente) REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    CONSTRAINT fk_convite_destinatario
        FOREIGN KEY (id_destinatario) REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    UNIQUE KEY uq_convite (id_grupo, id_destinatario, status)
) ENGINE=InnoDB;

CREATE TABLE ranking (
    id_ranking     INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario     INT NOT NULL,
    escopo         ENUM('global','regional','grupo') NOT NULL,
    id_grupo       INT NULL,
    referencia     VARCHAR(100),
    posicao        INT NOT NULL,
    pontuacao      INT NOT NULL DEFAULT 0,
    data_ref       DATE NOT NULL,
    CONSTRAINT fk_ranking_usuario
        FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    CONSTRAINT fk_ranking_grupo
        FOREIGN KEY (id_grupo) REFERENCES grupo(id_grupo) ON DELETE CASCADE,
    INDEX idx_ranking_escopo (escopo, data_ref, posicao)
) ENGINE=InnoDB;

CREATE TABLE meta (
    id_meta        INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario     INT NOT NULL,
    descricao      VARCHAR(300) NOT NULL,
    tipo           ENUM('curto_prazo','longo_prazo') NOT NULL DEFAULT 'curto_prazo',
    data_inicio    DATE NOT NULL,
    data_final     DATE,
    status         ENUM('em_andamento','concluida','expirada') NOT NULL DEFAULT 'em_andamento',
    progresso      TINYINT UNSIGNED NOT NULL DEFAULT 0,
    CONSTRAINT fk_meta_usuario
        FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE desafio (
    id_desafio     INT AUTO_INCREMENT PRIMARY KEY,
    nome           VARCHAR(120) NOT NULL,
    descricao      VARCHAR(500),
    exercicio      VARCHAR(120),
    data_inicio    DATE NOT NULL,
    data_fim       DATE NOT NULL,
    recompensa_xp  INT NOT NULL DEFAULT 0
) ENGINE=InnoDB;

CREATE TABLE desafio_usuario (
    id_desafio     INT NOT NULL,
    id_usuario     INT NOT NULL,
    status         ENUM('inscrito','concluido','desistiu') NOT NULL DEFAULT 'inscrito',
    concluido_em   DATETIME NULL,
    PRIMARY KEY (id_desafio, id_usuario),
    CONSTRAINT fk_du_desafio
        FOREIGN KEY (id_desafio) REFERENCES desafio(id_desafio) ON DELETE CASCADE,
    CONSTRAINT fk_du_usuario
        FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE notificacao (
    id_notif       INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario     INT NOT NULL,
    tipo           VARCHAR(60) NOT NULL,
    mensagem       VARCHAR(300) NOT NULL,
    lida           TINYINT(1) NOT NULL DEFAULT 0,
    data_envio     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notif_usuario
        FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    INDEX idx_notif_usuario_lida (id_usuario, lida)
) ENGINE=InnoDB;

CREATE TABLE compartilhamento (
    id_comp        INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario     INT NOT NULL,
    tipo_conteudo  ENUM('atividade','meta','desafio','recorde') NOT NULL,
    id_atividade   INT NULL,
    id_meta        INT NULL,
    rede_social    VARCHAR(40),
    data_comp      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_comp_usuario
        FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    CONSTRAINT fk_comp_atividade
        FOREIGN KEY (id_atividade) REFERENCES atividade(id_atividade) ON DELETE SET NULL,
    CONSTRAINT fk_comp_meta
        FOREIGN KEY (id_meta) REFERENCES meta(id_meta) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE OR REPLACE VIEW vw_ranking_global AS
SELECT
    u.id_usuario,
    u.nome,
    u.cidade,
    u.estado,
    COALESCE(SUM(a.pontuacao), 0) AS pontuacao_total,
    RANK() OVER (ORDER BY COALESCE(SUM(a.pontuacao), 0) DESC) AS posicao
FROM usuario u
LEFT JOIN atividade a ON a.id_usuario = u.id_usuario
WHERE u.perfil_publico = 1
GROUP BY u.id_usuario, u.nome, u.cidade, u.estado;

CREATE OR REPLACE VIEW vw_ranking_regional AS
SELECT
    u.id_usuario,
    u.nome,
    u.cidade,
    u.estado,
    COALESCE(SUM(a.pontuacao), 0) AS pontuacao_total,
    RANK() OVER (
        PARTITION BY u.cidade
        ORDER BY COALESCE(SUM(a.pontuacao), 0) DESC
    ) AS posicao
FROM usuario u
LEFT JOIN atividade a ON a.id_usuario = u.id_usuario
WHERE u.perfil_publico = 1
GROUP BY u.id_usuario, u.nome, u.cidade, u.estado;

CREATE OR REPLACE VIEW vw_ranking_grupo AS
SELECT
    gm.id_grupo,
    u.id_usuario,
    u.nome,
    COALESCE(SUM(a.pontuacao), 0) AS pontuacao_total,
    RANK() OVER (
        PARTITION BY gm.id_grupo
        ORDER BY COALESCE(SUM(a.pontuacao), 0) DESC
    ) AS posicao
FROM grupo_membro gm
JOIN usuario u   ON u.id_usuario = gm.id_usuario
LEFT JOIN atividade a ON a.id_usuario = u.id_usuario
GROUP BY gm.id_grupo, u.id_usuario, u.nome;

INSERT INTO usuario (nome, email, senha, idade, peso, altura, cidade, estado, descricao, nivel, xp) VALUES
('Paulo Souza',  'paulo@fitbattle.com',  'hash_exemplo_1', 28, 78.0, 1.80, 'Belo Horizonte', 'MG', 'Apaixonado por musculacao.', 'profissional', 11101),
('Camila Rocha',  'camila@fitbattle.com', 'hash_exemplo_2', 24, 61.5, 1.66, 'Belo Horizonte', 'MG', 'Corredora.', 'elite', 15230),
('Bruno Alves',   'bruno@fitbattle.com',  'hash_exemplo_3', 31, 84.2, 1.75, 'Contagem',       'MG', 'Crossfit.',  'avancado', 12890);

INSERT INTO atividade (id_usuario, tipo, titulo, descricao, tempo_min, carga_kg, repeticoes, pontuacao) VALUES
(1, 'musculacao', 'Peito', 'Treino pesado de peito.', 67, 300.0, 7, 120),
(1, 'cardio',     'Corrida', 'Corrida intensa.',       99, NULL,  NULL, 120),
(2, 'cardio',     'Corrida longa', '10k no parque.',   58, NULL,  NULL, 150);

INSERT INTO consentimento (id_usuario, chave, descricao, obrigatorio, aceito)
SELECT u.id_usuario, c.chave, c.descricao, c.obrigatorio, 1
FROM usuario u
CROSS JOIN (
                  SELECT 'conta_autenticacao'     AS chave, 'Criar, autenticar e manter a conta' AS descricao, 1 AS obrigatorio
        UNION ALL SELECT 'registro_atividades',        'Registrar e armazenar meus treinos', 1
        UNION ALL SELECT 'historico_estatisticas',     'Manter meu historico e minhas estatisticas individuais', 1
        UNION ALL SELECT 'dados_saude',                'Tratar dados de treino que possam revelar condicao de saude (art. 11 da LGPD)', 1
        UNION ALL SELECT 'seguranca_auditoria',        'Guardar registros tecnicos de seguranca e auditoria', 1
        UNION ALL SELECT 'ranking_publico',            'Exibir meu perfil e desempenho nos rankings regional e global', 0
        UNION ALL SELECT 'localizacao',                'Usar minha cidade/regiao para o ranking regional', 0
        UNION ALL SELECT 'chat_publico',               'Participar dos chats publicos da plataforma', 0
        UNION ALL SELECT 'chat_privado_externo',       'Receber mensagens privadas de usuarios fora dos meus grupos', 0
        UNION ALL SELECT 'busca_perfil',               'Permitir que outros usuarios me encontrem pela busca', 0
        UNION ALL SELECT 'notificacoes',               'Receber notificacoes por push ou e-mail', 0
        UNION ALL SELECT 'compartilhamento',           'Compartilhar conquistas e recordes em redes sociais externas', 0
) c;

INSERT INTO grupo (nome, descricao, privacidade, codigo_convite, id_criador) VALUES
('Amigos da Academia', 'Grupo de competicao entre amigos', 'privado', 'FITBTL1234', 1);

INSERT INTO grupo_membro (id_grupo, id_usuario, papel) VALUES
(1, 1, 'admin'),
(1, 2, 'membro');

INSERT INTO desafio (nome, descricao, exercicio, data_inicio, data_fim, recompensa_xp) VALUES
('Desafio de Verao', 'Complete 20 treinos no mes', 'livre', '2026-01-01', '2026-01-31', 500);

CREATE USER IF NOT EXISTS 'fitbattle'@'localhost' IDENTIFIED BY 'Fitbattle@123';
GRANT ALL PRIVILEGES ON fitbattle.* TO 'fitbattle'@'localhost';
FLUSH PRIVILEGES;
