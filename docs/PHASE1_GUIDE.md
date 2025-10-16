# 阶段1实施指南

## 当前进度

- [ ] 环境检查完成
- [ ] TXSQL源码获取
- [ ] TXSQL编译成功
- [ ] TPC-DS工具准备
- [ ] TPC-DS数据生成
- [ ] 数据导入MySQL
- [ ] 基线基准测试
- [ ] 靶心查询识别
- [ ] 手动优化分析

## 详细步骤

### Step 1: 环境检查
```bash
python scripts/phase1_setup.py
```

### Step 2: 获取TXSQL源码
```bash
# 方案A: 克隆官方仓库
git clone https://github.com/Tencent/TXSQL.git ../TXSQL

# 方案B: 使用MySQL 8.0源码
git clone https://github.com/mysql/mysql-server.git ../mysql-8.0
```

### Step 3: 编译TXSQL（Linux/macOS）
```bash
cd ../TXSQL
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Debug \
         -DWITH_DEBUG=1 \
         -DDOWNLOAD_BOOST=1 \
         -DWITH_BOOST=../boost
make -j$(nproc)
```

### Step 4: 编译TXSQL（Windows）
```cmd
cd ..\TXSQL
mkdir build && cd build
cmake .. -G "Visual Studio 16 2019" -A x64
cmake --build . --config Debug
```

### Step 5: 准备TPC-DS
```bash
python scripts/setup_tpcds.py --scale 1GB
```

### Step 6: 运行基线测试
```bash
python scripts/benchmark_tpcds.py --num-runs 3
```

### Step 7: 分析结果
```bash
python scripts/analyze_baseline.py
```

## 常见问题

### Q: TXSQL编译失败
A: 检查依赖是否完整安装，参考TXSQL官方文档

### Q: TPC-DS数据生成失败
A: 确保有足够磁盘空间（1GB规模约需5GB空间）

### Q: MySQL连接失败
A: 检查MySQL服务是否运行，端口是否正确

## 里程碑检查点

完成阶段1后，您应该具备：
- [x] 可运行的TXSQL实例
- [x] 完整的TPC-DS数据集
- [x] 基线性能数据
- [x] 3-5个已识别的靶心查询
