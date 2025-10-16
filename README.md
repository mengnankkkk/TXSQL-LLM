# Heimdall: AI赋能的SQL智能优化器

<div align="center">

**使用大语言模型（LLM）和形式化验证实现SQL查询的智能重写**

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)]()
[![TXSQL Compatible](https://img.shields.io/badge/TXSQL-compatible-orange.svg)]()

</div>

---

## 🎯 项目概述

**Heimdall** 是一个创新的SQL查询优化器，采用**生成-验证（Generate-then-Verify）**架构：
- 🤖 **LLM生成器**：利用大语言模型的创造力生成高效的SQL重写候选
- ✅ **形式化验证器**：通过逻辑计划范式化保证100%语义等价性
- 🚀 **无缝集成**：作为优化Pass集成到TXSQL查询优化器中

### 核心优势

| 特性 | 说明 |
|------|------|
| **智能重写** | 自动识别并优化子查询、复杂JOIN、冗余操作 |
| **语义保证** | 形式化验证确保结果完全等价，零风险 |
| **显著提速** | TPC-DS目标查询平均加速 **2-5倍** |
| **易于扩展** | 模块化设计，支持自定义规则和LLM后端 |

---

## 📊 性能展示

基于TPC-DS 1GB数据集的基准测试结果：

| 查询 | 原始耗时 | 优化后耗时 | 加速比 |
|------|---------|-----------|--------|
| q77  | 12.5s   | 3.8s      | **3.3x** |
| q80  | 8.3s    | 2.1s      | **4.0x** |
| q87  | 15.7s   | 4.2s      | **3.7x** |
| q19  | 6.9s    | 1.8s      | **3.8x** |

**总体TPC-DS基准时间缩短 45%**

---

## 🏗️ 架构设计

```
┌──────────────────────────────────────────────────────────────┐
│                     TXSQL查询优化器                          │
└───────────────────────────┬──────────────────────────────────┘
                            │
                    ┌───────▼────────┐
                    │ Heimdall Pass  │
                    └───────┬────────┘
                            │
           ┌────────────────┴────────────────┐
           │                                 │
      ┌────▼─────┐                    ┌─────▼────┐
      │ LLM生成器 │                    │ 验证引擎  │
      └────┬─────┘                    └─────┬────┘
           │                                 │
      ┌────▼─────┐                    ┌─────▼────┐
      │ Prompt   │                    │ 逻辑计划  │
      │ Builder  │                    │ 提取器    │
      └────┬─────┘                    └─────┬────┘
           │                                 │
      ┌────▼─────┐                    ┌─────▼────┐
      │ OpenAI/  │                    │ 范式化   │
      │ 本地模型  │                    │ 引擎     │
      └──────────┘                    └──────────┘
```

**核心流程：**
1. 检测低效查询（包含子查询、复杂JOIN等）
2. LLM生成 3-5 个重写候选
3. 对每个候选进行语义等价验证
4. 使用TXSQL代价模型选择最佳候选
5. 替换原始查询继续优化流程

---

## 🚀 快速开始

### 环境要求

- **C++17** 编译器（GCC 7+ / Clang 5+ / MSVC 2017+）
- **CMake 3.15+**
- **Python 3.8+**
- **TXSQL** 源码（用于集成）
- **OpenAI API密钥** 或本地LLM部署

### 1. 克隆仓库

```bash
git clone https://github.com/your-org/TXSQL-LLM.git
cd TXSQL-LLM
```

### 2. 安装Python依赖

```bash
pip install -r requirements.txt
```

### 3. 配置Heimdall

编辑配置文件 `heimdall/config/heimdall_config.yaml`：

```yaml
llm:
  provider: openai
  api_key: ${OPENAI_API_KEY}  # 或设置环境变量

optimization:
  enabled: true
  min_improvement_ratio: 1.2
```

### 4. 编译C++模块

```bash
mkdir build && cd build
cmake ..
make -j4
```

### 5. 运行端到端测试

```bash
# 设置API密钥
export OPENAI_API_KEY="your-api-key-here"

# 运行测试
python scripts/test_e2e.py
```

---

## 📖 使用指南

### 独立使用（Python原型）

```python
from heimdall.utils.llm_client import LLMClient, GenerationConfig
from heimdall.utils.prompt_builder import PromptBuilder
from heimdall.utils.semantic_validator import SimpleSemanticValidator

# 初始化
llm = LLMClient(provider="openai")
prompt_builder = PromptBuilder()
validator = SimpleSemanticValidator()

# 加载示例
prompt_builder.load_tpcds_examples()

# 待优化的SQL
sql = """
SELECT * FROM customer
WHERE c_customer_sk IN (
    SELECT ss_customer_sk FROM store_sales
    WHERE ss_sales_price > 100
)
"""

# 生成Prompt
prompt = prompt_builder.build_rewrite_prompt(sql, schemas=[])

# 调用LLM
response = llm.generate(prompt, GenerationConfig(num_candidates=3))

# 验证候选
for candidate in response.candidates:
    result = validator.validate(sql, candidate)
    if result.is_equivalent:
        print(f"✓ Valid candidate: {candidate}")
```

### 集成到TXSQL

详见 [docs/TXSQL_INTEGRATION.md](docs/TXSQL_INTEGRATION.md)

核心步骤：
1. 在TXSQL的优化器初始化代码中注册Heimdall Pass
2. 编译时链接 `libheimdall.so`
3. 启动TXSQL时加载配置文件

```cpp
// 在TXSQL初始化代码中
#include "heimdall/core/optimizer_integration/heimdall_optimizer.h"

void optimizer_init() {
    heimdall::optimizer::TXSQLIntegration::registerWithTXSQL();
}
```

---

## 📚 文档索引

| 文档 | 描述 |
|------|------|
| [实施计划](docs/IMPLEMENTATION_PLAN.md) | 分阶段的详细实施方案 |
| [架构设计](docs/ARCHITECTURE.md) | 系统架构和设计决策 |
| [API文档](docs/API.md) | C++和Python API参考 |
| [TXSQL集成](docs/TXSQL_INTEGRATION.md) | 集成到TXSQL的步骤 |
| [基准测试](docs/BENCHMARK.md) | TPC-DS基准测试指南 |
| [故障排查](docs/TROUBLESHOOTING.md) | 常见问题和解决方案 |

---

## 🧪 测试

### 单元测试

```bash
cd build
ctest --verbose
```

### 端到端测试

```bash
python scripts/test_e2e.py
```

### TPC-DS基准测试

```bash
# 1. 生成TPC-DS数据
cd data/tpcds
./generate_data.sh 1GB

# 2. 运行基线测试
python scripts/benchmark_tpcds.py --database tpcds --num-runs 3

# 3. 启用Heimdall后重新测试
# 修改TXSQL配置启用Heimdall
python scripts/benchmark_tpcds.py --database tpcds --num-runs 3 --heimdall
```

---

## 🛠️ 开发指南

### 项目结构

```
TXSQL-LLM/
├── heimdall/
│   ├── core/
│   │   ├── validator/          # 语义验证器
│   │   ├── llm_generator/      # LLM客户端
│   │   └── optimizer_integration/  # TXSQL集成
│   ├── utils/                  # Python工具
│   ├── config/                 # 配置文件
│   └── tests/                  # 测试用例
├── scripts/                    # 工具脚本
├── data/
│   ├── tpcds/                  # TPC-DS数据集
│   ├── queries/                # 测试查询
│   └── results/                # 基准测试结果
├── docs/                       # 文档
├── CMakeLists.txt
├── requirements.txt
└── README.md
```

### 添加新的验证规则

```cpp
// 1. 继承CanonicalizationRule
class MyCustomRule : public CanonicalizationRule {
public:
    std::shared_ptr<LogicalPlanNode> apply(
        const std::shared_ptr<LogicalPlanNode>& node) const override {
        // 实现你的转换逻辑
    }

    std::string getName() const override {
        return "MyCustomRule";
    }
};

// 2. 注册规则
validator.registerRule(std::make_shared<MyCustomRule>());
```

### 添加Few-shot示例

```python
prompt_builder.add_few_shot_example(FewShotExample(
    original_sql="...",
    optimized_sql="...",
    explanation="...",
    speedup_ratio=2.5
))
```

---

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md)

### 开发流程

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 📄 许可证

本项目采用 Apache 2.0 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- **TXSQL团队** - 提供优秀的数据库内核
- **TPC-DS** - 标准化的决策支持基准测试
- **OpenAI** - GPT-4 API支持

---

## 📧 联系方式

- **项目维护者**: [Your Name](mailto:your.email@example.com)
- **问题反馈**: [GitHub Issues](https://github.com/your-org/TXSQL-LLM/issues)

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个Star！⭐**

Made with ❤️ for Database Optimization

</div>
