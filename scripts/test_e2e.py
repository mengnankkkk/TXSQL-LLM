#!/usr/bin/env python3
"""
端到端测试脚本
测试完整的生成-验证流程
"""

import sys
import time
import json
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

from heimdall.utils.llm_client import LLMClient, GenerationConfig
from heimdall.utils.prompt_builder import PromptBuilder, TableSchema
from heimdall.utils.semantic_validator import SimpleSemanticValidator


class HeimdallE2ETest:
    """端到端测试"""

    def __init__(self):
        self.llm_client = LLMClient(provider="openai")
        self.prompt_builder = PromptBuilder()
        self.validator = SimpleSemanticValidator()

        # 加载示例
        self.prompt_builder.load_tpcds_examples()
        self.prompt_builder.set_optimization_hints([
            "subquery_unnesting",
            "predicate_pushdown",
            "join_reordering"
        ])

    def run_test(self, sql: str, schemas: list = None) -> dict:
        """运行单个测试"""
        print(f"\n{'='*80}")
        print(f"Testing SQL:")
        print(f"{sql}")
        print(f"{'='*80}\n")

        # 1. 构建Prompt
        print("Step 1: Building prompt...")
        prompt = self.prompt_builder.build_rewrite_prompt(
            sql,
            schemas or [],
            use_few_shot=True
        )
        print(f"  Prompt length: {len(prompt)} characters\n")

        # 2. 调用LLM生成候选
        print("Step 2: Generating candidates...")
        start_time = time.time()

        config = GenerationConfig(
            model_name="gpt-4",
            temperature=0.3,
            num_candidates=3
        )

        response = self.llm_client.generate(prompt, config)
        generation_time = time.time() - start_time

        if not response.success:
            print(f"  ERROR: {response.error_message}")
            return {"success": False, "error": response.error_message}

        print(f"  Generated {len(response.candidates)} candidates in {generation_time:.2f}s\n")

        # 3. 验证每个候选
        print("Step 3: Validating candidates...")
        validated_candidates = []

        for i, candidate in enumerate(response.candidates, 1):
            print(f"\n  Candidate {i}:")
            print(f"  {'-'*70}")
            print(f"  {candidate[:200]}...")

            # 验证
            result = self.validator.validate(sql, candidate)
            print(f"  Equivalent: {result.is_equivalent} (confidence: {result.confidence:.2f})")

            if result.differences:
                print(f"  Differences: {result.differences}")

            if result.is_equivalent:
                validated_candidates.append(candidate)
                print(f"  ✓ VALIDATED")
            else:
                print(f"  ✗ REJECTED")

        # 4. 选择最佳候选
        print(f"\n{'='*80}")
        if validated_candidates:
            print(f"SUCCESS: {len(validated_candidates)}/{len(response.candidates)} candidates validated")
            best_candidate = validated_candidates[0]
            print(f"\nBest candidate:")
            print(f"{best_candidate}")
        else:
            print("FAILURE: No candidates passed validation")
            best_candidate = None

        # 返回结果
        return {
            "success": len(validated_candidates) > 0,
            "original_sql": sql,
            "best_candidate": best_candidate,
            "num_candidates": len(response.candidates),
            "num_validated": len(validated_candidates),
            "generation_time": generation_time,
            "llm_latency": response.latency_ms
        }


def main():
    """主测试函数"""
    print("=" * 80)
    print("Heimdall E2E Test Suite")
    print("=" * 80)

    tester = HeimdallE2ETest()

    # 定义测试用例
    test_cases = [
        {
            "name": "Subquery Unnesting",
            "sql": """
                SELECT * FROM customer
                WHERE c_customer_sk IN (
                    SELECT ss_customer_sk FROM store_sales
                    WHERE ss_sales_price > 100
                )
            """,
            "schemas": [
                TableSchema(
                    table_name="customer",
                    columns=["c_customer_sk", "c_customer_id", "c_first_name", "c_last_name"],
                    primary_keys=["c_customer_sk"],
                    foreign_keys=[]
                ),
                TableSchema(
                    table_name="store_sales",
                    columns=["ss_customer_sk", "ss_sales_price", "ss_quantity"],
                    primary_keys=[],
                    foreign_keys=[{"column": "ss_customer_sk", "ref_table": "customer"}]
                )
            ]
        },
        {
            "name": "EXISTS to JOIN",
            "sql": """
                SELECT c_customer_id, c_first_name
                FROM customer c
                WHERE EXISTS (
                    SELECT 1 FROM store_sales ss
                    WHERE ss.ss_customer_sk = c.c_customer_sk
                    AND ss.ss_sales_price > 50
                )
            """,
            "schemas": []
        },
        {
            "name": "Complex OR Condition",
            "sql": """
                SELECT * FROM orders
                WHERE (status = 'pending' AND priority = 'high')
                   OR (status = 'processing' AND created_date < '2023-01-01')
            """,
            "schemas": []
        }
    ]

    # 运行所有测试
    results = []
    for test_case in test_cases:
        print(f"\n{'#'*80}")
        print(f"# Test Case: {test_case['name']}")
        print(f"{'#'*80}")

        result = tester.run_test(
            test_case["sql"].strip(),
            test_case.get("schemas")
        )
        result["test_name"] = test_case["name"]
        results.append(result)

        time.sleep(2)  # 避免API速率限制

    # 汇总结果
    print(f"\n{'='*80}")
    print("Test Summary")
    print(f"{'='*80}")

    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed

    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success rate: {passed/total*100:.1f}%")

    # 保存详细结果
    output_file = Path(__file__).parent.parent / "data" / "results" / "e2e_test_results.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump({
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "success_rate": passed/total
            },
            "results": results
        }, f, indent=2)

    print(f"\nDetailed results saved to: {output_file}")

    # 获取LLM统计
    stats = tester.llm_client.get_stats()
    print(f"\nLLM Client Statistics:")
    print(f"  Total calls: {stats['total_calls']}")
    print(f"  Cache hits: {stats['hits']}")
    print(f"  Cache hit rate: {stats['hit_rate']*100:.1f}%")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
