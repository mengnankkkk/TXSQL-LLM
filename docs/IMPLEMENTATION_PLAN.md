# Heimdall 实施计划

本文档提供了完整的、可执行的分阶段实施方案，将项目从理论走向实践。

---

## 📅 总体时间表

| 阶段 | 时间 | 里程碑 |
|------|------|--------|
| **阶段1：地基与勘探** | 2周 | TXSQL编译、TPC-DS部署、靶心查询分析 |
| **阶段2：验证器构建** | 2-3周 | 语义等价验证器完成 |
| **阶段3：LLM集成** | 2周 | LLM生成器就绪，生成-验证流程打通 |
| **阶段4：系统整合** | 1-2周 | TXSQL集成、端到端测试、性能评估 |
| **总计** | **7-9周** | 完整系统上线 |

---

## 🎯 阶段1：地基与勘探（第1-2周）

### 目标
深入理解问题域，锁定优化目标，搭建所有基础设施。

### 任务1.1：TXSQL环境搭建

**时间：2-3天**

#### 1.1.1 源码获取与编译
```bash
# 克隆TXSQL源码
git clone https://github.com/Tencent/TXSQL.git
cd TXSQL

# 安装依赖
sudo apt-get install build-essential cmake libssl-dev \
    libncurses5-dev libaio-dev bison

# 配置编译
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Debug \
         -DWITH_DEBUG=1 \
         -DWITH_BOOST=/path/to/boost

# 编译（使用多核加速）
make -j$(nproc)

# 安装
sudo make install
```

#### 1.1.2 配置调试环境
```bash
# 初始化数据目录
mysqld --initialize-insecure --datadir=/var/lib/mysql

# 启动服务器（调试模式）
mysqld --datadir=/var/lib/mysql \
       --log-error=/var/log/mysql/error.log \
       --general-log=1 \
       --general-log-file=/var/log/mysql/general.log
```

#### 1.1.3 IDE配置（VS Code）
创建 `.vscode/launch.json`：
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug TXSQL",
            "type": "cppdbg",
            "request": "launch",
            "program": "${workspaceFolder}/build/sql/mysqld",
            "args": ["--datadir=/var/lib/mysql", "--gdb"],
            "cwd": "${workspaceFolder}",
            "MIMode": "gdb"
        }
    ]
}
```

**交付物：**
- ✅ 可运行的TXSQL实例
- ✅ 可调试的开发环境
- ✅ 环境配置文档

---

### 任务1.2：TPC-DS基准测试部署

**时间：2-3天**

#### 1.2.1 生成TPC-DS数据集
```bash
# 克隆TPC-DS工具
git clone https://github.com/databricks/tpcds-kit.git
cd tpcds-kit/tools

# 编译
make

# 生成1GB数据集
./dsdgen -SCALE 1 -DIR ../../data/tpcds/1GB

# 生成建表语句
./dsqgen -DIRECTORY ../query_templates \
         -INPUT ../query_templates/templates.lst \
         -OUTPUT_DIR ../../data/queries/tpcds
```

#### 1.2.2 导入数据到TXSQL
```sql
-- 创建数据库
CREATE DATABASE tpcds;
USE tpcds;

-- 创建所有表（使用生成的DDL）
SOURCE data/tpcds/create_tables.sql;

-- 导入数据
LOAD DATA INFILE '/path/to/store_sales.dat'
INTO TABLE store_sales
FIELDS TERMINATED BY '|';

-- 对所有24个表重复上述操作
```

使用脚本自动化：
```bash
#!/bin/bash
# scripts/load_tpcds.sh

for table in $(ls data/tpcds/1GB/*.dat | xargs -n 1 basename | cut -d'.' -f1); do
    echo "Loading $table..."
    mysql -u root tpcds -e "
        LOAD DATA INFILE '/path/to/data/tpcds/1GB/${table}.dat'
        INTO TABLE $table
        FIELDS TERMINATED BY '|'
        LINES TERMINATED BY '\n';
    "
done

echo "Creating indexes..."
mysql -u root tpcds < data/tpcds/create_indexes.sql
```

#### 1.2.3 运行基线基准测试
```bash
# 使用我们的脚本
python scripts/benchmark_tpcds.py \
    --host localhost \
    --database tpcds \
    --queries q77 q80 q87 q19 q37 \
    --num-runs 3

# 结果保存在 data/results/baseline.json
```

**交付物：**
- ✅ 1GB TPC-DS数据集已导入
- ✅ 基线性能数据（JSON格式）
- ✅ 可重复的测试脚本

---

### 任务1.3：锁定"靶心"查询并手动优化

**时间：3-5天**

#### 1.3.1 识别高价值目标查询

分析基线结果，选择：
1. **执行时间最长**的查询（如 q77, q80, q87）
2. **包含复杂子查询**的查询
3. **有明显优化空间**的查询

```python
# 分析脚本
import json

with open('data/results/baseline.json') as f:
    results = json.load(f)

# 按执行时间排序
queries = sorted(results['results'], key=lambda x: x['time'], reverse=True)

print("Top 10 slowest queries:")
for i, q in enumerate(queries[:10], 1):
    print(f"{i}. {q['query']}: {q['time']:.2f}s")
```

#### 1.3.2 深度分析每个靶心查询

以 **TPC-DS Q77** 为例：

**步骤1：获取执行计划**
```sql
EXPLAIN FORMAT=JSON
SELECT ss_customer_sk, SUM(ss_quantity*ss_sales_price) as total
FROM store_sales s, store_returns sr, store st
WHERE s.ss_customer_sk = sr.sr_customer_sk
  AND s.ss_item_sk = sr.sr_item_sk
  AND s.ss_ticket_number = sr.sr_ticket_number
  AND s.ss_store_sk = st.s_store_sk
  AND st.s_state = 'TN'
GROUP BY ss_customer_sk
HAVING SUM(ss_quantity*ss_sales_price) > (
    SELECT 0.5 * AVG(total_sum)
    FROM (
        SELECT SUM(ss_quantity*ss_sales_price) as total_sum
        FROM store_sales ss2, store st2
        WHERE ss2.ss_store_sk = st2.s_store_sk
        AND st2.s_state = 'TN'
        GROUP BY ss2.ss_customer_sk
    ) t
)
ORDER BY total
LIMIT 100;
```

**步骤2：识别瓶颈**
```json
{
  "query_block": {
    "select_id": 1,
    "cost_info": {
      "query_cost": "125673.80"  // 非常高！
    },
    "having_subqueries": [
      {
        "dependent": true,  // ← 问题：相关子查询
        "query_block": {...}
      }
    ]
  }
}
```

**问题诊断：**
- ✗ `DEPENDENT SUBQUERY` 在 HAVING 子句中
- ✗ 对每一组都执行一次子查询
- ✗ 未利用索引

**步骤3：手动编写优化版本**
```sql
-- 优化版：将子查询转换为WITH CTE
WITH customer_totals AS (
    SELECT ss_customer_sk,
           SUM(ss_quantity*ss_sales_price) as total
    FROM store_sales s, store st
    WHERE s.ss_store_sk = st.s_store_sk
      AND st.s_state = 'TN'
    GROUP BY ss_customer_sk
),
avg_total AS (
    SELECT 0.5 * AVG(total) as threshold
    FROM customer_totals
)
SELECT ct.ss_customer_sk, ct.total
FROM customer_totals ct, avg_total
WHERE ct.total > avg_total.threshold
ORDER BY ct.total
LIMIT 100;
```

**步骤4：验证等价性**
```sql
-- 确保结果完全一致
(SELECT * FROM original_query)
EXCEPT
(SELECT * FROM optimized_query);
-- 应返回空集
```

**步骤5：测试性能**
```bash
# 运行原始版本
time mysql -u root tpcds < queries/q77_original.sql

# 运行优化版本
time mysql -u root tpcds < queries/q77_optimized.sql

# 记录结果
echo "q77: Original 12.5s → Optimized 3.8s (3.3x speedup)" >> optimizations.log
```

#### 1.3.3 对所有靶心查询重复

创建分析文档 `docs/TARGET_QUERIES.md`：

```markdown
# 靶心查询分析

## Q77: 相关子查询优化

### 原始SQL
[完整SQL]

### 性能瓶颈
- DEPENDENT SUBQUERY 在 HAVING 子句
- 估算代价: 125,673

### 优化策略
- 子查询展开为CTE
- 消除相关性

### 优化后SQL
[完整SQL]

### 结果对比
| 指标 | 原始 | 优化后 | 改进 |
|------|------|--------|------|
| 执行时间 | 12.5s | 3.8s | 3.3x |
| 估算代价 | 125,673 | 38,250 | 3.3x |
| 中间结果行数 | 1,200,000 | 45,000 | 26.7x |

### 验证
✅ 结果集完全一致（0行差异）

---

## Q80: IN子查询转JOIN
[类似的完整分析]

...
```

**交付物：**
- ✅ 3-5个完全分析的靶心查询
- ✅ 每个查询的手动优化版本
- ✅ 详细的分析文档（成为Few-shot示例的基础）
- ✅ 验证脚本确保等价性

---

## 🔧 阶段2：核心引擎构建 - 语义验证器（第3-5周）

### 目标
构建能够形式化证明SQL等价性的验证引擎。

### 任务2.1：逻辑计划提取器

**时间：3-4天**

#### 2.1.1 研究TXSQL内部结构
```cpp
// 关键数据结构位置（需根据实际TXSQL版本调整）
// sql/sql_optimizer.h
// sql/sql_select.h
// sql/item.h

// 关键类：
class SELECT_LEX;          // 查询块
class Item;                // 表达式节点
class JOIN;                // JOIN操作
class TABLE_LIST;          // 表引用
```

找到优化器中获取逻辑计划的"钩子"：
```cpp
// 在 sql/sql_optimizer.cc 中
int JOIN::optimize() {
    // ... 解析完成，逻辑计划已构建

    // ← 在这里插入我们的提取器
    heimdall::validator::LogicalPlan plan =
        heimdall::validator::PlanExtractor::extractFromTXSQL(thd, this);

    // ... 继续优化
}
```

#### 2.1.2 实现提取器核心逻辑

创建 `heimdall/core/validator/plan_extractor.cpp`：

```cpp
LogicalPlan PlanExtractor::extractFromTXSQL(void* thd_ptr, void* join_ptr) {
    THD* thd = static_cast<THD*>(thd_ptr);
    JOIN* join = static_cast<JOIN*>(join_ptr);

    LogicalPlan plan;
    plan.original_sql = thd->query().str;

    // 递归遍历SELECT_LEX树
    SELECT_LEX* select_lex = join->select_lex;
    plan.root = convertSelectLex(select_lex);

    return plan;
}

std::shared_ptr<LogicalPlanNode>
PlanExtractor::convertSelectLex(SELECT_LEX* lex) {
    auto node = std::make_shared<LogicalPlanNode>(PlanNodeType::PROJECT);

    // 提取投影列
    for (Item* item : lex->item_list) {
        node->projected_columns.push_back(extractColumnName(item));
    }

    // 提取表
    for (TABLE_LIST* table = lex->table_list.first; table; table = table->next_local) {
        auto scan_node = std::make_shared<LogicalPlanNode>(PlanNodeType::SCAN);
        scan_node->table_name = table->table_name;
        node->children.push_back(scan_node);
    }

    // 提取WHERE条件
    if (lex->where_cond()) {
        node->condition = convertExpression(lex->where_cond());
    }

    // 递归处理子查询
    for (SELECT_LEX_UNIT* unit : lex->slave_units) {
        // ...
    }

    return node;
}
```

#### 2.1.3 序列化为JSON

```cpp
std::string LogicalPlan::toJsonString() const {
    Json::Value root;
    root["type"] = "LogicalPlan";
    root["sql"] = original_sql;
    root["plan"] = rootToJson(this->root);

    Json::StreamWriterBuilder builder;
    return Json::writeString(builder, root);
}

Json::Value LogicalPlanNode::toJson() const {
    Json::Value node;
    node["type"] = planNodeTypeToString(type);
    node["id"] = id;

    if (!table_name.empty()) {
        node["table"] = table_name;
    }

    if (condition) {
        node["condition"] = condition->toJson();
    }

    Json::Value children_array(Json::arrayValue);
    for (const auto& child : children) {
        children_array.append(child->toJson());
    }
    node["children"] = children_array;

    return node;
}
```

**测试：**
```cpp
// 单元测试
TEST(PlanExtractor, SimpleSelect) {
    std::string sql = "SELECT * FROM customer WHERE id > 100";
    auto plan = extractPlanFromSQL(sql);

    EXPECT_EQ(plan.root->type, PlanNodeType::PROJECT);
    EXPECT_EQ(plan.root->children.size(), 1);
    EXPECT_EQ(plan.root->children[0]->type, PlanNodeType::SCAN);
    EXPECT_EQ(plan.root->children[0]->table_name, "customer");
}
```

---

### 任务2.2：范式化引擎

**时间：4-5天**

这是验证器的核心算法。

#### 2.2.1 实现基础范式化规则

**规则1：交换律 - JOIN顺序标准化**
```cpp
class CommutativeJoinRule : public CanonicalizationRule {
public:
    std::shared_ptr<LogicalPlanNode> apply(
        const std::shared_ptr<LogicalPlanNode>& node) const override {

        if (node->type != PlanNodeType::JOIN) {
            return node;
        }

        // 对于INNER JOIN，子节点顺序无关
        if (node->join_type == "INNER") {
            // 按表名字典序排序子节点
            std::sort(node->children.begin(), node->children.end(),
                     [](const auto& a, const auto& b) {
                         return a->table_name < b->table_name;
                     });
        }

        return node;
    }
};
```

**规则2：谓词规范化**
```cpp
class PredicateNormalizationRule : public CanonicalizationRule {
public:
    std::shared_ptr<ExpressionNode> normalizeExpression(
        std::shared_ptr<ExpressionNode> expr) const {

        if (expr->type == ExprType::BINARY_OP) {
            // 规范化比较操作符方向: 确保常量在右边
            if (expr->op == ">" && expr->children[1]->type == ExprType::COLUMN_REF) {
                // a > b 转换为 b < a
                std::swap(expr->children[0], expr->children[1]);
                expr->op = "<";
            }

            // 规范化 != 为 <>
            if (expr->op == "!=") {
                expr->op = "<>";
            }
        }

        if (expr->type == ExprType::BINARY_OP && expr->op == "AND") {
            // AND条件按字典序排序
            sortAndConditions(expr->children);
        }

        return expr;
    }
};
```

**规则3：IN表达式展开**
```cpp
class InExpressionExpansionRule : public CanonicalizationRule {
public:
    std::shared_ptr<ExpressionNode> apply(
        std::shared_ptr<ExpressionNode> expr) const override {

        if (expr->type == ExprType::IN_EXPR) {
            // col IN (1, 2, 3) → (col = 1) OR (col = 2) OR (col = 3)
            auto or_expr = std::make_shared<ExpressionNode>(ExprType::BINARY_OP);
            or_expr->op = "OR";

            for (const auto& value : expr->children) {
                auto eq = std::make_shared<ExpressionNode>(ExprType::BINARY_OP);
                eq->op = "=";
                eq->children.push_back(expr->children[0]);
                eq->children.push_back(value);
                or_expr->children.push_back(eq);
            }

            return or_expr;
        }

        return expr;
    }
};
```

#### 2.2.2 组合所有规则

```cpp
LogicalPlan LogicalPlan::canonicalize() const {
    LogicalPlan canonical;
    canonical.original_sql = this->original_sql;
    canonical.root = this->root->clone();

    // 应用所有范式化规则
    std::vector<std::shared_ptr<CanonicalizationRule>> rules = {
        std::make_shared<CommutativeJoinRule>(),
        std::make_shared<PredicateNormalizationRule>(),
        std::make_shared<InExpressionExpansionRule>(),
        std::make_shared<SubqueryUnnestingRule>()
    };

    for (const auto& rule : rules) {
        canonical.root = applyRuleRecursive(canonical.root, rule);
    }

    return canonical;
}
```

---

### 任务2.3：比对引擎

**时间：2-3天**

```cpp
bool LogicalPlan::equals(const LogicalPlan& other) const {
    // 1. 范式化两个计划
    LogicalPlan canon1 = this->canonicalize();
    LogicalPlan canon2 = other.canonicalize();

    // 2. 比对根节点
    return compareNodes(canon1.root, canon2.root);
}

bool compareNodes(const std::shared_ptr<LogicalPlanNode>& n1,
                 const std::shared_ptr<LogicalPlanNode>& n2) {
    // 类型必须相同
    if (n1->type != n2->type) return false;

    // 表名必须相同（对于SCAN节点）
    if (n1->type == PlanNodeType::SCAN) {
        if (n1->table_name != n2->table_name) return false;
    }

    // 条件必须相同
    if (!compareExpressions(n1->condition, n2->condition)) {
        return false;
    }

    // 递归比对子节点
    if (n1->children.size() != n2->children.size()) {
        return false;
    }

    for (size_t i = 0; i < n1->children.size(); ++i) {
        if (!compareNodes(n1->children[i], n2->children[i])) {
            return false;
        }
    }

    return true;
}
```

---

### 任务2.4：集成测试

**时间：2天**

使用阶段1的手动优化查询对进行测试：

```cpp
TEST(SemanticValidator, Q77_SubqueryUnnesting) {
    std::string original = loadQuery("data/queries/tpcds/q77_original.sql");
    std::string optimized = loadQuery("data/queries/tpcds/q77_optimized.sql");

    SemanticValidator validator;
    ValidationResult result = validator.validate(original, optimized);

    EXPECT_TRUE(result.is_equivalent);
    EXPECT_GE(result.confidence, 0.95);
}
```

**交付物：**
- ✅ 完整的验证器实现
- ✅ 通过所有靶心查询对的测试
- ✅ 单元测试覆盖率 >80%

---

## 🤖 阶段3：智能大脑集成 - LLM生成器（第6-7周）

### 任务3.1：LLM客户端实现

**时间：2-3天**

已提供Python实现，现在实现C++版本（或通过Python FFI）：

**方案A：Python FFI（推荐，快速）**
```cpp
// 使用pybind11调用Python客户端
#include <pybind11/embed.h>

namespace py = pybind11;

class LLMClient::Impl {
private:
    py::scoped_interpreter guard_;
    py::object client_;

public:
    Impl() {
        py::module_ llm_module = py::module_::import("heimdall.utils.llm_client");
        client_ = llm_module.attr("LLMClient")("openai");
    }

    LLMResponse generate(const std::string& prompt, const GenerationConfig& config) {
        py::object result = client_.attr("generate")(prompt, config);

        LLMResponse response;
        response.success = result.attr("success").cast<bool>();
        response.candidates = result.attr("candidates").cast<std::vector<std::string>>();
        response.latency_ms = result.attr("latency_ms").cast<double>();

        return response;
    }
};
```

**方案B：纯C++实现**
```cpp
// 使用libcurl进行HTTP调用
LLMResponse OpenAIProvider::generate(const std::string& prompt,
                                    const GenerationConfig& config) {
    Json::Value request;
    request["model"] = config.model_name;
    request["messages"][0]["role"] = "user";
    request["messages"][0]["content"] = prompt;
    request["temperature"] = config.temperature;
    request["max_tokens"] = config.max_tokens;
    request["n"] = config.num_candidates;

    std::string response_str = httpPost(
        "https://api.openai.com/v1/chat/completions",
        request.toStyledString(),
        {"Authorization: Bearer " + api_key_}
    );

    Json::Value response = Json::parse(response_str);

    LLMResponse llm_response;
    for (const auto& choice : response["choices"]) {
        std::string content = choice["message"]["content"].asString();
        llm_response.candidates.push_back(extractSQL(content));
    }
    llm_response.success = true;

    return llm_response;
}
```

### 任务3.2：Prompt工程优化

**时间：2-3天**

基于阶段1的手动优化，构建高质量Few-shot示例：

```cpp
void PromptBuilder::loadTPCDSExamples() {
    // 从我们的分析文档加载
    auto examples = parseFewShotFile("docs/TARGET_QUERIES.md");

    for (const auto& example : examples) {
        this->addFewShotExample(FewShotExample{
            .original_sql = example.original,
            .optimized_sql = example.optimized,
            .explanation = example.explanation,
            .speedup_ratio = example.speedup
        });
    }
}
```

**迭代优化Prompt模板：**

版本1：
```
Rewrite this SQL for better performance:
[SQL]
```

版本2（添加上下文）：
```
You are an expert SQL optimizer for TXSQL.
Rewrite the following query to improve performance while maintaining semantic equivalence.

Schema:
[Schemas]

Query:
[SQL]
```

版本3（添加Few-shot）：
```
[System Prompt]

Here are examples of successful optimizations:

Example 1: [Original] → [Optimized] (3.3x speedup)
Example 2: [Original] → [Optimized] (4.0x speedup)

Now optimize this query:
[SQL]

Output only the optimized SQL in a code block.
```

**A/B测试不同Prompt版本：**
```python
def test_prompt_variants():
    variants = [prompt_v1, prompt_v2, prompt_v3]
    results = []

    for variant in variants:
        response = llm.generate(variant.format(sql=test_sql))
        validated = validator.validate(test_sql, response.candidates[0])

        results.append({
            'variant': variant.name,
            'valid': validated.is_equivalent,
            'latency': response.latency_ms
        })

    # 选择最佳版本
    best = max(results, key=lambda x: x['valid'])
    return best['variant']
```

### 任务3.3：打通生成-验证循环

**时间：2天**

```cpp
OptimizationResult HeimdallOptimizer::optimize(const std::string& sql, void* thd) {
    auto start_time = std::chrono::steady_clock::now();

    OptimizationResult result;
    result.original_sql = sql;

    // 1. 检查是否应该优化
    if (!shouldOptimize(sql)) {
        result.optimized = false;
        result.reason = "Query does not meet optimization criteria";
        return result;
    }

    // 2. 生成候选
    std::vector<std::string> candidates = generateCandidates(sql);
    result.stats.candidates_generated = candidates.size();

    // 3. 验证候选
    std::vector<std::string> valid_candidates;
    for (const auto& candidate : candidates) {
        auto validation = validator_->validate(sql, candidate);
        if (validation.is_equivalent) {
            valid_candidates.push_back(candidate);
        }
    }
    result.stats.candidates_validated = valid_candidates.size();

    // 4. 如果没有通过验证的候选
    if (valid_candidates.empty()) {
        result.optimized = false;
        result.reason = "No candidates passed validation";
        return result;
    }

    // 5. 选择最佳候选
    std::string best = selectBestCandidate(sql, valid_candidates, thd);
    result.optimized_sql = best;
    result.optimized = true;

    // 6. 估算代价
    result.estimated_cost_original = estimateCost(sql, thd);
    result.estimated_cost_optimized = estimateCost(best, thd);
    result.improvement_ratio = result.estimated_cost_original /
                               result.estimated_cost_optimized;

    result.total_time = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - start_time
    );

    return result;
}
```

**交付物：**
- ✅ LLM客户端（C++或Python FFI）
- ✅ 优化的Prompt模板
- ✅ 完整的生成-验证流程
- ✅ 端到端测试通过

---

## 🔗 阶段4：系统整合与评估（第8-9周）

### 任务4.1：TXSQL集成

**时间：3-4天**

#### 4.1.1 编写集成钩子

在TXSQL优化器中找到合适的插入点：

```cpp
// sql/sql_optimizer.cc

#include "heimdall/core/optimizer_integration/heimdall_optimizer.h"

int JOIN::optimize() {
    // ... TXSQL原有的优化逻辑

    // === Heimdall集成点 ===
    if (heimdall_enabled()) {
        auto& heimdall = heimdall::optimizer::HeimdallOptimizer::getInstance();

        std::string original_sql = thd->query().str;
        auto result = heimdall.optimize(original_sql, thd);

        if (result.optimized &&
            result.improvement_ratio >= heimdall_min_improvement_ratio()) {

            // 用优化后的SQL替换原始查询
            thd->set_query(result.optimized_sql.c_str(),
                          result.optimized_sql.length());

            // 重新解析优化后的SQL
            mysql_parse(thd, result.optimized_sql.c_str(),
                       result.optimized_sql.length(), &parser_state);

            // 记录统计信息
            heimdall_stats_increment();
        }
    }

    // ... 继续TXSQL的物理优化
}
```

#### 4.1.2 编译集成

修改TXSQL的CMakeLists.txt：

```cmake
# 添加Heimdall库
find_library(HEIMDALL_LIB heimdall HINTS ${PROJECT_SOURCE_DIR}/../TXSQL-LLM/build)

# 链接到mysqld
target_link_libraries(mysqld
    ...现有依赖...
    ${HEIMDALL_LIB}
)
```

重新编译：
```bash
cd TXSQL/build
cmake .. -DHEIMDALL_ENABLED=ON
make -j$(nproc)
```

#### 4.1.3 运行时配置

添加MySQL系统变量：

```cpp
// sql/sys_vars.cc

static Sys_var_bool Sys_heimdall_enabled(
    "heimdall_enabled",
    "Enable Heimdall AI optimizer",
    GLOBAL_VAR(opt_heimdall_enabled),
    CMD_LINE(OPT_ARG),
    DEFAULT(FALSE)
);

static Sys_var_double Sys_heimdall_min_improvement(
    "heimdall_min_improvement_ratio",
    "Minimum improvement ratio required",
    GLOBAL_VAR(opt_heimdall_min_improvement),
    CMD_LINE(REQUIRED_ARG),
    VALID_RANGE(1.0, 10.0),
    DEFAULT(1.2)
);
```

启用Heimdall：
```sql
SET GLOBAL heimdall_enabled = ON;
SET GLOBAL heimdall_min_improvement_ratio = 1.2;
```

---

### 任务4.2：端到端性能评估

**时间：2-3天**

#### 4.2.1 重新运行TPC-DS基准测试

```bash
# 1. 启用Heimdall
mysql -e "SET GLOBAL heimdall_enabled = ON"

# 2. 重新运行基准测试
python scripts/benchmark_tpcds.py \
    --database tpcds \
    --queries q77 q80 q87 q19 q37 \
    --num-runs 3 \
    --output data/results/heimdall_enabled.json

# 3. 对比结果
python scripts/compare_results.py \
    data/results/baseline.json \
    data/results/heimdall_enabled.json
```

#### 4.2.2 生成性能报告

```python
# scripts/compare_results.py

import json
import matplotlib.pyplot as plt

def generate_report(baseline_file, optimized_file):
    with open(baseline_file) as f:
        baseline = json.load(f)
    with open(optimized_file) as f:
        optimized = json.load(f)

    # 对比每个查询
    comparisons = []
    for b_result in baseline['results']:
        query = b_result['query']
        o_result = next(r for r in optimized['results'] if r['query'] == query)

        speedup = b_result['time'] / o_result['time']
        comparisons.append({
            'query': query,
            'baseline': b_result['time'],
            'optimized': o_result['time'],
            'speedup': speedup
        })

    # 打印表格
    print(f"{'Query':<10} {'Baseline':<12} {'Optimized':<12} {'Speedup':<10}")
    print("-" * 50)
    for c in comparisons:
        print(f"{c['query']:<10} {c['baseline']:<12.2f} "
              f"{c['optimized']:<12.2f} {c['speedup']:<10.2f}x")

    # 生成图表
    fig, ax = plt.subplots(figsize=(12, 6))
    queries = [c['query'] for c in comparisons]
    speedups = [c['speedup'] for c in comparisons]

    ax.bar(queries, speedups)
    ax.set_ylabel('Speedup Factor')
    ax.set_title('Heimdall Optimization Results')
    ax.axhline(y=1.0, color='r', linestyle='--', label='No improvement')
    ax.legend()

    plt.savefig('data/results/speedup_chart.png')
    print("\nChart saved to: data/results/speedup_chart.png")
```

---

### 任务4.3：准备最终展示

**时间：2天**

#### 4.3.1 技术报告

创建 `docs/FINAL_REPORT.md`，包含：

1. **项目概述**
2. **技术架构**
   - 生成-验证架构图
   - 各模块详细设计
3. **核心技术突破**
   - 语义验证算法
   - LLM Prompt工程
4. **性能评估**
   - TPC-DS完整结果
   - 靶心查询对比
   - 统计分析
5. **创新点总结**
6. **未来扩展方向**

#### 4.3.2 Live Demo脚本

```bash
#!/bin/bash
# demo.sh - 现场演示脚本

echo "=== Heimdall Live Demo ==="

# 1. 显示待优化的查询
echo "Original query (TPC-DS Q77):"
cat queries/q77_original.sql

# 2. 执行原始查询并计时
echo -e "\nExecuting original query..."
time mysql -u root tpcds < queries/q77_original.sql > /tmp/original_result.txt
ORIGINAL_TIME=$?

# 3. 启用Heimdall
echo -e "\nEnabling Heimdall optimizer..."
mysql -e "SET GLOBAL heimdall_enabled = ON"

# 4. 再次执行（自动优化）
echo -e "\nExecuting with Heimdall..."
time mysql -u root tpcds < queries/q77_original.sql > /tmp/optimized_result.txt
OPTIMIZED_TIME=$?

# 5. 显示Heimdall生成的优化SQL
echo -e "\nOptimized SQL generated by Heimdall:"
mysql -e "SHOW HEIMDALL_LAST_REWRITE" | sed -n '2p'

# 6. 验证结果等价性
echo -e "\nVerifying semantic equivalence..."
diff /tmp/original_result.txt /tmp/optimized_result.txt
if [ $? -eq 0 ]; then
    echo "✓ Results are identical!"
else
    echo "✗ Results differ (this should not happen!)"
fi

# 7. 显示性能改进
echo -e "\nPerformance improvement:"
echo "Original: ${ORIGINAL_TIME}s"
echo "Optimized: ${OPTIMIZED_TIME}s"
python3 -c "print(f'Speedup: {${ORIGINAL_TIME}/${OPTIMIZED_TIME}:.2f}x')"
```

---

## 📊 成功标准

在项目结束时，您应该能够展示：

### 功能性指标
- ✅ 语义验证器对所有靶心查询对返回"等价"
- ✅ LLM成功生成至少1个通过验证的候选（>80%的情况）
- ✅ 完整的生成-验证-选择流程运行无错误

### 性能指标
- ✅ 至少3个TPC-DS查询加速 **>2倍**
- ✅ 整体TPC-DS套件时间缩短 **>30%**
- ✅ 优化开销 < 原始查询时间的20%

### 工程质量
- ✅ 代码可编译、可运行
- ✅ 单元测试覆盖率 >70%
- ✅ 完整的文档和演示

---

## 🛡️ 风险缓解策略

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| LLM生成质量不稳定 | 高 | 中 | 多候选策略 + 严格验证 |
| 验证器覆盖不全 | 中 | 高 | 明确声明支持的模式，聚焦高价值场景 |
| TXSQL集成困难 | 中 | 中 | 先完成独立模块，最后再集成 |
| 性能提升不显著 | 低 | 高 | 靶心查询已人工验证，有保底成果 |

---

## 📚 参考资源

### 学术论文
- "Optimizing Queries using Transformations" - Pirahesh et al.
- "The Cascades Framework for Query Optimization" - Graefe
- "Learning to Optimize Join Queries With Deep Reinforcement Learning" - Marcus et al.

### 开源项目
- Calcite: Apache SQL优化器框架
- CockroachDB: 分布式SQL数据库
- Presto: 分布式查询引擎

### TXSQL文档
- TXSQL GitHub Repository
- MySQL 8.0 Optimizer Documentation

---

**祝您实施顺利，期待看到Heimdall的精彩表现！** 🚀
