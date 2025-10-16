#!/usr/bin/env python3
"""
TPC-DS工具链自动化部署脚本
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Optional
import argparse


class TPCDSSetup:
    """TPC-DS环境准备"""

    def __init__(self, project_root: Path, scale_factor: str = "1GB"):
        self.project_root = project_root
        self.tpcds_dir = project_root / "data" / "tpcds"
        self.tools_dir = self.tpcds_dir / "tools"
        self.scale_factor = scale_factor
        self.queries_dir = project_root / "data" / "queries" / "tpcds"

    def setup(self):
        """完整设置流程"""
        print("=" * 80)
        print("TPC-DS环境准备")
        print("=" * 80)
        print()

        steps = [
            ("创建目录结构", self.create_directories),
            ("下载TPC-DS工具", self.download_tools),
            ("编译工具", self.compile_tools),
            ("生成数据", self.generate_data),
            ("生成查询", self.generate_queries),
            ("创建DDL", self.create_ddl),
        ]

        for step_name, step_func in steps:
            print(f"\n{'='*60}")
            print(f"步骤: {step_name}")
            print(f"{'='*60}")
            try:
                step_func()
                print(f"✓ {step_name} 完成")
            except Exception as e:
                print(f"✗ {step_name} 失败: {str(e)}")
                return False

        self.print_summary()
        return True

    def create_directories(self):
        """创建必要的目录"""
        dirs = [
            self.tpcds_dir,
            self.tpcds_dir / self.scale_factor,
            self.tools_dir,
            self.queries_dir,
            self.project_root / "data" / "results"
        ]

        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
            print(f"  创建目录: {d}")

    def download_tools(self):
        """下载TPC-DS工具"""
        print("  正在克隆TPC-DS工具...")

        if self.tools_dir.exists() and (self.tools_dir / "dsdgen.c").exists():
            print("  工具已存在，跳过下载")
            return

        subprocess.run([
            "git", "clone",
            "https://github.com/databricks/tpcds-kit.git",
            str(self.tpcds_dir / "tpcds-kit")
        ], check=True)

        # 移动tools目录
        kit_tools = self.tpcds_dir / "tpcds-kit" / "tools"
        if kit_tools.exists():
            shutil.copytree(kit_tools, self.tools_dir, dirs_exist_ok=True)
            print(f"  工具已复制到: {self.tools_dir}")

    def compile_tools(self):
        """编译TPC-DS工具"""
        print("  正在编译工具...")

        if sys.platform == "win32":
            print("  Windows平台，使用预编译二进制或WSL")
            # 在Windows上，建议使用WSL或提供预编译版本
            print("  提示: 在Windows上建议使用WSL2或Docker编译")
            return
        else:
            # Linux/macOS
            original_dir = os.getcwd()
            os.chdir(self.tools_dir)

            try:
                subprocess.run(["make", "clean"], check=False)
                subprocess.run(["make"], check=True)
                print("  编译成功")
            finally:
                os.chdir(original_dir)

    def generate_data(self):
        """生成TPC-DS数据"""
        print(f"  正在生成 {self.scale_factor} 数据...")

        # 解析规模因子
        scale_map = {
            "1GB": 1,
            "10GB": 10,
            "100GB": 100,
            "1TB": 1000
        }
        scale = scale_map.get(self.scale_factor, 1)

        output_dir = self.tpcds_dir / self.scale_factor

        dsdgen = self.tools_dir / "dsdgen"
        if not dsdgen.exists():
            print(f"  警告: dsdgen未找到于 {dsdgen}")
            print("  请手动编译或使用预编译版本")
            return

        # 运行dsdgen
        subprocess.run([
            str(dsdgen),
            "-SCALE", str(scale),
            "-DIR", str(output_dir),
            "-FORCE", "Y"
        ], check=True)

        # 统计生成的文件
        data_files = list(output_dir.glob("*.dat"))
        print(f"  生成了 {len(data_files)} 个数据文件")

    def generate_queries(self):
        """生成TPC-DS查询"""
        print("  正在生成查询...")

        dsqgen = self.tools_dir / "dsqgen"
        if not dsqgen.exists():
            print("  跳过查询生成（dsqgen未找到）")
            return

        template_dir = self.tools_dir.parent / "query_templates"

        # 生成所有99个查询
        for i in range(1, 100):
            query_file = self.queries_dir / f"q{i}.sql"

            subprocess.run([
                str(dsqgen),
                "-DIRECTORY", str(template_dir),
                "-TEMPLATE", f"query{i}.tpl",
                "-OUTPUT_DIR", str(self.queries_dir),
                "-DIALECT", "mysql"
            ], check=False)  # 有些查询可能失败，继续执行

        generated = list(self.queries_dir.glob("*.sql"))
        print(f"  生成了 {len(generated)} 个查询文件")

    def create_ddl(self):
        """创建建表语句"""
        print("  创建DDL语句...")

        ddl_content = """-- TPC-DS Schema for MySQL/TXSQL

-- Store Sales
CREATE TABLE store_sales (
    ss_sold_date_sk INT,
    ss_sold_time_sk INT,
    ss_item_sk INT NOT NULL,
    ss_customer_sk INT,
    ss_cdemo_sk INT,
    ss_hdemo_sk INT,
    ss_addr_sk INT,
    ss_store_sk INT,
    ss_promo_sk INT,
    ss_ticket_number BIGINT NOT NULL,
    ss_quantity INT,
    ss_wholesale_cost DECIMAL(7,2),
    ss_list_price DECIMAL(7,2),
    ss_sales_price DECIMAL(7,2),
    ss_ext_discount_amt DECIMAL(7,2),
    ss_ext_sales_price DECIMAL(7,2),
    ss_ext_wholesale_cost DECIMAL(7,2),
    ss_ext_list_price DECIMAL(7,2),
    ss_ext_tax DECIMAL(7,2),
    ss_coupon_amt DECIMAL(7,2),
    ss_net_paid DECIMAL(7,2),
    ss_net_paid_inc_tax DECIMAL(7,2),
    ss_net_profit DECIMAL(7,2),
    PRIMARY KEY (ss_item_sk, ss_ticket_number)
) ENGINE=InnoDB;

-- Customer
CREATE TABLE customer (
    c_customer_sk INT NOT NULL PRIMARY KEY,
    c_customer_id CHAR(16) NOT NULL,
    c_current_cdemo_sk INT,
    c_current_hdemo_sk INT,
    c_current_addr_sk INT,
    c_first_shipto_date_sk INT,
    c_first_sales_date_sk INT,
    c_salutation CHAR(10),
    c_first_name CHAR(20),
    c_last_name CHAR(30),
    c_preferred_cust_flag CHAR(1),
    c_birth_day INT,
    c_birth_month INT,
    c_birth_year INT,
    c_birth_country VARCHAR(20),
    c_login CHAR(13),
    c_email_address CHAR(50),
    c_last_review_date INT
) ENGINE=InnoDB;

-- Store
CREATE TABLE store (
    s_store_sk INT NOT NULL PRIMARY KEY,
    s_store_id CHAR(16) NOT NULL,
    s_rec_start_date DATE,
    s_rec_end_date DATE,
    s_closed_date_sk INT,
    s_store_name VARCHAR(50),
    s_number_employees INT,
    s_floor_space INT,
    s_hours CHAR(20),
    s_manager VARCHAR(40),
    s_market_id INT,
    s_geography_class VARCHAR(100),
    s_market_desc VARCHAR(100),
    s_market_manager VARCHAR(40),
    s_division_id INT,
    s_division_name VARCHAR(50),
    s_company_id INT,
    s_company_name VARCHAR(50),
    s_street_number VARCHAR(10),
    s_street_name VARCHAR(60),
    s_street_type CHAR(15),
    s_suite_number CHAR(10),
    s_city VARCHAR(60),
    s_county VARCHAR(30),
    s_state CHAR(2),
    s_zip CHAR(10),
    s_country VARCHAR(20),
    s_gmt_offset DECIMAL(5,2),
    s_tax_percentage DECIMAL(5,2)
) ENGINE=InnoDB;

-- Store Returns
CREATE TABLE store_returns (
    sr_returned_date_sk INT,
    sr_return_time_sk INT,
    sr_item_sk INT NOT NULL,
    sr_customer_sk INT,
    sr_cdemo_sk INT,
    sr_hdemo_sk INT,
    sr_addr_sk INT,
    sr_store_sk INT,
    sr_reason_sk INT,
    sr_ticket_number BIGINT NOT NULL,
    sr_return_quantity INT,
    sr_return_amt DECIMAL(7,2),
    sr_return_tax DECIMAL(7,2),
    sr_return_amt_inc_tax DECIMAL(7,2),
    sr_fee DECIMAL(7,2),
    sr_return_ship_cost DECIMAL(7,2),
    sr_refunded_cash DECIMAL(7,2),
    sr_reversed_charge DECIMAL(7,2),
    sr_store_credit DECIMAL(7,2),
    sr_net_loss DECIMAL(7,2),
    PRIMARY KEY (sr_item_sk, sr_ticket_number)
) ENGINE=InnoDB;

-- 注意: 这里只包含了最常用的几个表
-- 完整的TPC-DS包含24个表，您可能需要添加其他表的定义
"""

        ddl_file = self.tpcds_dir / "create_tables.sql"
        with open(ddl_file, 'w') as f:
            f.write(ddl_content)

        print(f"  DDL已创建: {ddl_file}")

        # 创建索引DDL
        index_content = """-- TPC-DS Indexes

-- Store Sales Indexes
CREATE INDEX idx_ss_sold_date ON store_sales(ss_sold_date_sk);
CREATE INDEX idx_ss_customer ON store_sales(ss_customer_sk);
CREATE INDEX idx_ss_store ON store_sales(ss_store_sk);

-- Customer Indexes
CREATE INDEX idx_c_customer_id ON customer(c_customer_id);
CREATE INDEX idx_c_current_addr ON customer(c_current_addr_sk);

-- Store Indexes
CREATE INDEX idx_s_store_id ON store(s_store_id);
CREATE INDEX idx_s_state ON store(s_state);

-- Store Returns Indexes
CREATE INDEX idx_sr_returned_date ON store_returns(sr_returned_date_sk);
CREATE INDEX idx_sr_customer ON store_returns(sr_customer_sk);
CREATE INDEX idx_sr_store ON store_returns(sr_store_sk);
"""

        index_file = self.tpcds_dir / "create_indexes.sql"
        with open(index_file, 'w') as f:
            f.write(index_content)

        print(f"  索引DDL已创建: {index_file}")

    def print_summary(self):
        """打印总结"""
        print("\n" + "=" * 80)
        print("TPC-DS准备完成")
        print("=" * 80)
        print(f"\n数据目录: {self.tpcds_dir / self.scale_factor}")
        print(f"查询目录: {self.queries_dir}")
        print(f"\n下一步:")
        print(f"  1. 启动MySQL: mysqld --datadir=/your/data/dir")
        print(f"  2. 创建数据库: mysql -e 'CREATE DATABASE tpcds'")
        print(f"  3. 导入表结构: mysql tpcds < {self.tpcds_dir / 'create_tables.sql'}")
        print(f"  4. 导入数据: python scripts/load_tpcds_data.py")
        print(f"  5. 创建索引: mysql tpcds < {self.tpcds_dir / 'create_indexes.sql'}")


def main():
    parser = argparse.ArgumentParser(description="TPC-DS环境准备")
    parser.add_argument("--scale", default="1GB",
                       choices=["1GB", "10GB", "100GB", "1TB"],
                       help="数据规模因子")
    parser.add_argument("--project-root", type=Path,
                       default=Path(__file__).parent.parent,
                       help="项目根目录")

    args = parser.parse_args()

    setup = TPCDSSetup(args.project_root, args.scale)
    success = setup.setup()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
