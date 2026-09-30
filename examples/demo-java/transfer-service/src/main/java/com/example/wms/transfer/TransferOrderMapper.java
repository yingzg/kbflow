package com.example.wms.transfer;

import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

/**
 * 调拨单数据访问
 */
@Mapper
public interface TransferOrderMapper {

    @Insert("INSERT INTO transfer_order(sku, qty, target_warehouse, status) VALUES(#{sku}, #{qty}, #{targetWarehouse}, #{status})")
    int insert(TransferOrder order);

    @Select("SELECT * FROM transfer_order WHERE transfer_no = #{transferNo}")
    TransferOrder selectByNo(String transferNo);

    @Update("UPDATE transfer_order SET status = #{status} WHERE transfer_no = #{transferNo}")
    int update(TransferOrder order);
}
