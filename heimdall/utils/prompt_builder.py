"""
智能Prompt构建器
"""

from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class TableSchema:
    """表结构"""
    table_name: str
    columns: List[str]
    primary_keys: List[str]
    foreign_keys: List[Dict[str, str]]
    create_statement: str = ""


@dataclass
class FewShotExample:
    """Few-shot示例"""
    original_sql: str
    optimized_sql: str
    explanation: str
    speedup_ratio: float


class PromptBuilder:
    """Prompt构建器"""

    DEFAULT_SYSTEM_PROMPT = """You are an expert SQL performance engineer working on TXSQL database optimization.
Your task is to rewrite inefficient SQL queries to achieve better performance while maintaining 100% semantic equivalence.

Key principles:
1. MUST preserve exact semantic equivalence - results must be identical
2. Focus on performance improvements: reduce subqueries, optimize joins, eliminate redundancy
3. Apply proven optimization techniques: subquery unnesting, predicate pushdown, join reordering
4. Output ONLY the optimized SQL code, no explanations
"""

    OPTIMIZATION_TECHNIQUES = {
        "subquery_unnesting": "Convert correlated subqueries to JOINs when possible",
        "predicate_pushdown": "Push filter conditions closer to data sources",
        "join_reordering": "Reorder joins to reduce intermediate result size",
        "redundancy_elimination": "Remove redundant conditions and operations",
        "in_to_join": "Convert IN subqueries to JOIN operations",
        "exists_to_join": "Convert EXISTS subqueries to JOIN operations"
    }

    def __init__(self):
        self.system_prompt = self.DEFAULT_SYSTEM_PROMPT
        self.few_shot_examples: List[FewShotExample] = []
        self.optimization_hints: List[str] = []

    def build_rewrite_prompt(
        self,
        original_sql: str,
        schemas: List[TableSchema],
        use_few_shot: bool = True
    ) -> str:
        """构建完整的重写Prompt"""

        parts = [self.system_prompt, ""]

        # 添加Schema信息
        if schemas:
            parts.append("## Database Schema\n")
            for schema in schemas:
                parts.append(f"### Table: {schema.table_name}")
                if schema.create_statement:
                    parts.append(f"```sql\n{schema.create_statement}\n```")
                else:
                    parts.append(f"Columns: {', '.join(schema.columns)}")
                    if schema.primary_keys:
                        parts.append(f"Primary Keys: {', '.join(schema.primary_keys)}")
                parts.append("")

        # 添加优化技术提示
        if self.optimization_hints:
            parts.append("## Optimization Techniques to Consider\n")
            for hint in self.optimization_hints:
                if hint in self.OPTIMIZATION_TECHNIQUES:
                    parts.append(f"- **{hint}**: {self.OPTIMIZATION_TECHNIQUES[hint]}")
            parts.append("")

        # 添加Few-shot示例
        if use_few_shot and self.few_shot_examples:
            parts.append("## Examples of Successful Optimizations\n")
            for i, example in enumerate(self.few_shot_examples[:3], 1):
                parts.append(f"### Example {i} (Speedup: {example.speedup_ratio:.1f}x)\n")
                parts.append("**Original:**")
                parts.append(f"```sql\n{example.original_sql}\n```")
                parts.append("\n**Optimized:**")
                parts.append(f"```sql\n{example.optimized_sql}\n```")
                if example.explanation:
                    parts.append(f"\n*{example.explanation}*")
                parts.append("")

        # 添加待优化的SQL
        parts.append("## Query to Optimize\n")
        parts.append("Rewrite the following query for better performance:")
        parts.append(f"```sql\n{original_sql}\n```")
        parts.append("")
        parts.append("## Requirements\n")
        parts.append("1. Output ONLY the optimized SQL query inside a ```sql code block")
        parts.append("2. Ensure 100% semantic equivalence")
        parts.append("3. Focus on measurable performance improvements")
        parts.append("4. If no optimization is possible, return the original query")

        return "\n".join(parts)

    def add_few_shot_example(self, example: FewShotExample):
        """添加Few-shot示例"""
        self.few_shot_examples.append(example)

    def set_optimization_hints(self, hints: List[str]):
        """设置优化提示"""
        self.optimization_hints = hints

    def load_tpcds_examples(self) -> None:
        """加载TPC-DS典型优化示例"""
        # 示例1: 子查询展开
        self.add_few_shot_example(FewShotExample(
            original_sql="""
SELECT * FROM customer
WHERE c_customer_sk IN (
    SELECT ss_customer_sk FROM store_sales
    WHERE ss_sales_price > 100
)
            """.strip(),
            optimized_sql="""
SELECT DISTINCT c.*
FROM customer c
INNER JOIN store_sales ss ON c.c_customer_sk = ss.ss_customer_sk
WHERE ss.ss_sales_price > 100
            """.strip(),
            explanation="Converted IN subquery to INNER JOIN for better performance",
            speedup_ratio=3.2
        ))

        # 示例2: 谓词下推
        self.add_few_shot_example(FewShotExample(
            original_sql="""
SELECT * FROM (
    SELECT * FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
) t
WHERE t.order_date > '2023-01-01'
            """.strip(),
            optimized_sql="""
SELECT *
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_date > '2023-01-01'
            """.strip(),
            explanation="Pushed predicate down to reduce intermediate result size",
            speedup_ratio=2.5
        ))

        # 示例3: EXISTS to JOIN
        self.add_few_shot_example(FewShotExample(
            original_sql="""
SELECT c_customer_id, c_first_name, c_last_name
FROM customer c
WHERE EXISTS (
    SELECT 1 FROM store_sales ss
    WHERE ss.ss_customer_sk = c.c_customer_sk
    AND ss.ss_sales_price > 50
)
            """.strip(),
            optimized_sql="""
SELECT DISTINCT c.c_customer_id, c.c_first_name, c.c_last_name
FROM customer c
INNER JOIN store_sales ss ON c.c_customer_sk = ss.ss_customer_sk
WHERE ss.ss_sales_price > 50
            """.strip(),
            explanation="Converted EXISTS to JOIN to leverage indexes",
            speedup_ratio=4.1
        ))


if __name__ == "__main__":
    # 测试示例
    builder = PromptBuilder()
    builder.load_tpcds_examples()
    builder.set_optimization_hints(["subquery_unnesting", "predicate_pushdown"])

    schemas = [
        TableSchema(
            table_name="customer",
            columns=["c_customer_sk", "c_customer_id", "c_first_name", "c_last_name"],
            primary_keys=["c_customer_sk"],
            foreign_keys=[]
        )
    ]

    test_sql = """
    SELECT * FROM customer
    WHERE c_customer_sk IN (
        SELECT ss_customer_sk FROM store_sales WHERE ss_sales_price > 100
    )
    """

    prompt = builder.build_rewrite_prompt(test_sql, schemas)
    print(prompt)
    print(f"\nPrompt length: {len(prompt)} characters")
