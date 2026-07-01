CREATE DATABASE IF NOT EXISTS mydatabase
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE mydatabase;


-- PRODUCTS

CREATE TABLE IF NOT EXISTS products (
    wid                 VARCHAR(64)  NOT NULL PRIMARY KEY,
    ean                 VARCHAR(32)  NOT NULL,
    manufacturing_date  DATE         NOT NULL,
    expiry_date         DATE         NOT NULL,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_products_ean (ean)
) ENGINE=InnoDB;


-- INGESTION BATCHES

CREATE TABLE IF NOT EXISTS ingestion_batches (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    file_name       VARCHAR(255) NOT NULL,
    uploaded_by     VARCHAR(64)  DEFAULT 'warehouse_manager',
    total_rows      INT          DEFAULT 0,
    inserted_rows   INT          DEFAULT 0,
    duplicate_rows  INT          DEFAULT 0,
    failed_rows     INT          DEFAULT 0,
    status          ENUM('processing','completed','failed') DEFAULT 'processing',
    started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at     TIMESTAMP NULL
) ENGINE=InnoDB;


-- VALIDATION LOGS 

CREATE TABLE IF NOT EXISTS validation_logs (
    id                  BIGINT      AUTO_INCREMENT PRIMARY KEY,
    wid                 VARCHAR(64) NOT NULL,
    ean                 VARCHAR(32),
    manufacturing_date  DATE,
    expiry_date         DATE,
    operator_id         VARCHAR(64) NOT NULL DEFAULT 'operator',
    result              ENUM('CORRECT','INCORRECT','NOT_FOUND') NOT NULL,
    mfg_date_result     ENUM('CORRECT','INCORRECT')             NULL,
    expiry_date_result  ENUM('CORRECT','INCORRECT')             NULL,
    validation_mode     ENUM('MANUAL','IMAGE')                  NOT NULL DEFAULT 'MANUAL',
    ocr_mfg_date        VARCHAR(20)  NULL,
    ocr_expiry_date     VARCHAR(20)  NULL,
    image_path          VARCHAR(512)             NULL,
    checked_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_logs_checked_at (checked_at),
    INDEX idx_logs_wid        (wid),
    INDEX idx_logs_result     (result)
) ENGINE=InnoDB;
