-- TABLE: transfer_order
CREATE TABLE transfer_order (
    transfer_no VARCHAR(64) PRIMARY KEY COMMENT '调拨单号',
    sku VARCHAR(64) COMMENT 'SKU',
    qty INT COMMENT '数量',
    target_warehouse VARCHAR(64) COMMENT '目标仓库',
    status VARCHAR(16) COMMENT '状态'
) COMMENT='调拨单主表';

-- TABLE: stock_record
CREATE TABLE stock_record (
    sku VARCHAR(64) PRIMARY KEY COMMENT 'SKU',
    quantity INT COMMENT '库存数量'
) COMMENT='库存记录表';
