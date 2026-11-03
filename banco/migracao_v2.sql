-- =====================================================================
-- MIGRAÇÃO V2 — rode UMA vez no banco de testes (e depois no definitivo).
-- Pode ser executada de novo sem problema: só cria o que ainda não existe.
--
-- O que muda:
--   tb_veiculos   + marca, + tipo_veiculo (Carro/Moto)
--   tb_vagas      + categoria (Carro/Moto)
--   tb_precos     + categoria; o preço passa a ser único por (categoria, tipo_cobranca)
--   tb_pagamentos + forma_pagamento (Dinheiro, Pix, cartão...)
--   tb_usuarios   + codigo_liberacao (PIN do administrador, guardado com hash)
--
-- Faça um backup antes:  mysqldump -u USUARIO -p --routines --triggers BANCO > backup.sql
-- =====================================================================

DROP PROCEDURE IF EXISTS sp_add_coluna;
DROP PROCEDURE IF EXISTS sp_trocar_indice_precos;

DELIMITER $$

-- adiciona a coluna somente se ela ainda não existir
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

-- troca o índice único antigo (só tipo_cobranca) pelo novo (categoria + tipo_cobranca)
CREATE PROCEDURE sp_trocar_indice_precos()
BEGIN
    DECLARE v_indice VARCHAR(64);

    SELECT INDEX_NAME INTO v_indice
    FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tb_precos'
      AND NON_UNIQUE = 0 AND INDEX_NAME <> 'PRIMARY' AND INDEX_NAME <> 'uq_preco_categoria_tipo'
    GROUP BY INDEX_NAME
    HAVING COUNT(*) = 1 AND MAX(COLUMN_NAME) = 'tipo_cobranca'
    LIMIT 1;

    IF v_indice IS NOT NULL THEN
        SET @ddl = CONCAT('ALTER TABLE tb_precos DROP INDEX `', v_indice, '`');
        PREPARE stmt FROM @ddl;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tb_precos' AND INDEX_NAME = 'uq_preco_categoria_tipo'
    ) THEN
        ALTER TABLE tb_precos ADD UNIQUE KEY uq_preco_categoria_tipo (categoria, tipo_cobranca);
    END IF;
END$$

DELIMITER ;

-- ---------------------------------------------------------------- veículos
CALL sp_add_coluna('tb_veiculos', 'marca', 'VARCHAR(50) NULL AFTER placa');
CALL sp_add_coluna('tb_veiculos', 'tipo_veiculo', "ENUM('Carro','Moto') NOT NULL DEFAULT 'Carro'");

-- ------------------------------------------------------------------- vagas
CALL sp_add_coluna('tb_vagas', 'categoria', "ENUM('Carro','Moto') NOT NULL DEFAULT 'Carro'");

-- ------------------------------------------------------------------ preços
CALL sp_add_coluna('tb_precos', 'categoria', "ENUM('Carro','Moto') NOT NULL DEFAULT 'Carro'");
CALL sp_trocar_indice_precos();

-- -------------------------------------------------------------- pagamentos
CALL sp_add_coluna('tb_pagamentos', 'forma_pagamento', 'VARCHAR(20) NULL');

-- ---------------------------------------------------------------- usuários
CALL sp_add_coluna('tb_usuarios', 'codigo_liberacao', 'VARCHAR(255) NULL');

DROP PROCEDURE sp_add_coluna;
DROP PROCEDURE sp_trocar_indice_precos;

-- Conferência (opcional):
--   DESCRIBE tb_veiculos;  DESCRIBE tb_vagas;  DESCRIBE tb_precos;
--   DESCRIBE tb_pagamentos;  DESCRIBE tb_usuarios;  SHOW INDEX FROM tb_precos;
