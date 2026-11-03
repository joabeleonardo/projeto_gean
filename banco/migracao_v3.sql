-- =====================================================================
-- MIGRAÇÃO V3 — rode DEPOIS da migracao_v2.sql, uma vez por banco.
-- Pode ser executada de novo sem problema: só cria o que ainda não existe.
--
-- O que muda:
--   tb_vagas        + ativa            (inativar vaga em reforma/manutenção)
--   tb_precos       + valor_minimo, tempo_minimo_minutos (cobrança proporcional com mínimo)
--   tb_mensalidades NOVA TABELA        (plano de mensalista: cotas e data de adesão)
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

-- ------------------------------------------------------------------- vagas
-- 1 = ativa (padrão: todas as vagas existentes continuam ativas)
CALL sp_add_coluna('tb_vagas', 'ativa', 'TINYINT(1) NOT NULL DEFAULT 1');

-- ------------------------------------------------------------------ preços
-- 0 = sem mínimo (cobrança 100% proporcional). Defina os valores na tela de Preços.
CALL sp_add_coluna('tb_precos', 'valor_minimo', 'DECIMAL(10,2) NOT NULL DEFAULT 0');
CALL sp_add_coluna('tb_precos', 'tempo_minimo_minutos', 'INT NOT NULL DEFAULT 0');

-- ------------------------------------------------------------ mensalidades
CREATE TABLE IF NOT EXISTS tb_mensalidades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_cliente INT NOT NULL,
    categoria ENUM('Carro', 'Moto') NOT NULL DEFAULT 'Carro',
    cotas INT NOT NULL DEFAULT 1,
    data_inicio DATE NOT NULL,
    data_fim DATE NULL,
    ativa TINYINT(1) NOT NULL DEFAULT 1,
    CONSTRAINT fk_mensalidade_cliente FOREIGN KEY (id_cliente) REFERENCES tb_clientes(id),
    INDEX idx_mensalidade_cliente (id_cliente, ativa)
);

DROP PROCEDURE sp_add_coluna;

-- Conferência (opcional):
--   DESCRIBE tb_vagas;  DESCRIBE tb_precos;  DESCRIBE tb_mensalidades;
