-- =====================================================================
-- MIGRAÇÃO V4 — rode DEPOIS da migracao_v3.sql, uma vez por banco.
-- Pode ser executada de novo sem problema: só cria o que ainda não existe.
--
-- O que muda:
--   tb_clientes      cpf agora cabe CNPJ (VARCHAR 18); + tipo_documento, pais,
--                    telefone2, telefone_whatsapp, telefone2_whatsapp
--   tb_pagamentos    + valor_recebido, troco (pagamento em dinheiro)
--   tb_movimentacao  + id_usuario_liberacao, obs_liberacao (entrada liberada por código)
--   tb_vagas         tipo passa a aceitar 'Premium' (vaga exclusiva)
--   tb_precos        tipo_cobranca passa a aceitar 'Premium'
--   tb_mensalidades  + tipo_plano (Rotativo/Premium), id_vaga (vaga do plano premium)
--   tb_logs          NOVA TABELA (relatório de logs do sistema)
--
-- Faça um backup antes:  mysqldump -u USUARIO -p --routines --triggers BANCO > backup.sql
-- =====================================================================

DROP PROCEDURE IF EXISTS sp_add_coluna;

DELIMITER $$
CREATE PROCEDURE sp_add_coluna(IN p_tabela VARCHAR(64), IN p_coluna VARCHAR(64), IN p_definicao VARCHAR(255))
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = p_tabela AND COLUMN_NAME = p_coluna
    ) THEN
        SET @ddl = CONCAT('ALTER TABLE `', p_tabela, '` ADD COLUMN `', p_coluna, '` ', p_definicao);
        PREPARE stmt FROM @ddl;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END$$
DELIMITER ;

-- ---------------------------------------------------------------- clientes
-- A coluna continua se chamando "cpf" (as triggers de auditoria usam esse nome); agora guarda CPF, CNPJ ou passaporte.
ALTER TABLE tb_clientes MODIFY cpf VARCHAR(18) NOT NULL;
CALL sp_add_coluna('tb_clientes', 'tipo_documento', "ENUM('CPF','CNPJ','Passaporte') NOT NULL DEFAULT 'CPF'");
CALL sp_add_coluna('tb_clientes', 'pais', "VARCHAR(60) NOT NULL DEFAULT 'Brasil'");
CALL sp_add_coluna('tb_clientes', 'telefone2', 'VARCHAR(20) NULL');
CALL sp_add_coluna('tb_clientes', 'telefone_whatsapp', 'TINYINT(1) NOT NULL DEFAULT 0');
CALL sp_add_coluna('tb_clientes', 'telefone2_whatsapp', 'TINYINT(1) NOT NULL DEFAULT 0');

-- -------------------------------------------------------------- pagamentos
CALL sp_add_coluna('tb_pagamentos', 'valor_recebido', 'DECIMAL(10,2) NULL');
CALL sp_add_coluna('tb_pagamentos', 'troco', 'DECIMAL(10,2) NULL');

-- ------------------------------------------------------------ movimentação
CALL sp_add_coluna('tb_movimentacao', 'id_usuario_liberacao', 'INT NULL');
CALL sp_add_coluna('tb_movimentacao', 'obs_liberacao', 'VARCHAR(255) NULL');

-- ------------------------------------------------------- vagas premium
ALTER TABLE tb_vagas MODIFY tipo ENUM('Mensalista','Horista','Premium') NOT NULL;
ALTER TABLE tb_precos MODIFY tipo_cobranca ENUM('Mensalista','Horista','Premium') NOT NULL;
CALL sp_add_coluna('tb_mensalidades', 'tipo_plano', "ENUM('Rotativo','Premium') NOT NULL DEFAULT 'Rotativo'");
CALL sp_add_coluna('tb_mensalidades', 'id_vaga', 'INT NULL');

-- ------------------------------------------------------------------- logs
CREATE TABLE IF NOT EXISTS tb_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    data_hora DATETIME NOT NULL,
    id_usuario INT NULL,
    usuario VARCHAR(100) NOT NULL DEFAULT 'Sistema',
    acao VARCHAR(20) NOT NULL,
    entidade VARCHAR(40) NOT NULL,
    id_registro INT NULL,
    descricao TEXT NOT NULL,
    campo VARCHAR(60) NULL,
    valor_antigo TEXT NULL,
    valor_novo TEXT NULL,
    INDEX idx_logs_data (data_hora),
    INDEX idx_logs_usuario (id_usuario),
    INDEX idx_logs_entidade (entidade, id_registro)
);

DROP PROCEDURE sp_add_coluna;

-- Conferência (opcional):
--   DESCRIBE tb_clientes;  DESCRIBE tb_pagamentos;  DESCRIBE tb_movimentacao;
--   DESCRIBE tb_vagas;  DESCRIBE tb_precos;  DESCRIBE tb_mensalidades;  DESCRIBE tb_logs;
