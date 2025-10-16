#!/usr/bin/env python3
"""
TPC-DS基准测试脚本
"""

import sys
import time
import mysql.connector
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    query_name: str
    original_time: float
    optimized_time: float
    speedup: float
    success: bool
    error: str = ""


class TPCDSBenchmark:
    """TPC-DS基准测试"""

    def __init__(self, host: str = "localhost", port: int = 3306,
                 user: str = "root", password: str = "", database: str = "tpcds"):
        self.conn_params = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database
        }
        self.queries_dir = Path(__file__).parent.parent / "data" / "queries" / "tpcds"

    def connect(self):
        """连接数据库"""
        return mysql.connector.connect(**self.conn_params)

    def load_query(self, query_name: str) -> str:
        """加载查询SQL"""
        query_file = self.queries_dir / f"{query_name}.sql"
        if not query_file.exists():
            raise FileNotFoundError(f"Query file not found: {query_file}")

        with open(query_file, 'r') as f:
            return f.read()

    def execute_query(self, sql: str, num_runs: int = 3) -> float:
        """执行查询并测量时间"""
        times = []

        for i in range(num_runs):
            conn = self.connect()
            cursor = conn.cursor()

            try:
                start_time = time.time()
                cursor.execute(sql)
                cursor.fetchall()  # 获取所有结果
                elapsed = time.time() - start_time
                times.append(elapsed)

                print(f"    Run {i+1}: {elapsed:.3f}s")

            finally:
                cursor.close()
                conn.close()

            # 避免缓存影响
            if i < num_runs - 1:
                time.sleep(1)

        # 返回中位数
        times.sort()
        return times[len(times) // 2]

    def benchmark_query(self, query_name: str, optimized_sql: str = None,
                       num_runs: int = 3) -> BenchmarkResult:
        """对单个查询进行基准测试"""
        print(f"\nBenchmarking {query_name}...")

        try:
            # 加载原始查询
            original_sql = self.load_query(query_name)
            print(f"  Original SQL loaded")

            # 测试原始查询
            print(f"  Testing original query...")
            original_time = self.execute_query(original_sql, num_runs)
            print(f"  Original median time: {original_time:.3f}s")

            # 如果提供了优化版本，测试优化查询
            if optimized_sql:
                print(f"  Testing optimized query...")
                optimized_time = self.execute_query(optimized_sql, num_runs)
                print(f"  Optimized median time: {optimized_time:.3f}s")

                speedup = original_time / optimized_time
                print(f"  Speedup: {speedup:.2f}x")

                return BenchmarkResult(
                    query_name=query_name,
                    original_time=original_time,
                    optimized_time=optimized_time,
                    speedup=speedup,
                    success=True
                )
            else:
                # 仅测试原始查询（建立基线）
                return BenchmarkResult(
                    query_name=query_name,
                    original_time=original_time,
                    optimized_time=0.0,
                    speedup=1.0,
                    success=True
                )

        except Exception as e:
            print(f"  ERROR: {str(e)}")
            return BenchmarkResult(
                query_name=query_name,
                original_time=0.0,
                optimized_time=0.0,
                speedup=0.0,
                success=False,
                error=str(e)
            )

    def run_baseline_benchmark(self, query_names: List[str],
                              num_runs: int = 3) -> Dict:
        """运行基线基准测试"""
        print("="*80)
        print("TPC-DS Baseline Benchmark")
        print("="*80)

        results = []
        for query_name in query_names:
            result = self.benchmark_query(query_name, num_runs=num_runs)
            results.append(result)

        # 汇总结果
        total_time = sum(r.original_time for r in results if r.success)

        summary = {
            "total_queries": len(results),
            "successful": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
            "total_time": total_time,
            "results": [
                {
                    "query": r.query_name,
                    "time": r.original_time,
                    "success": r.success,
                    "error": r.error
                }
                for r in results
            ]
        }

        # 保存结果
        output_file = Path(__file__).parent.parent / "data" / "results" / "baseline.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"\n{'='*80}")
        print(f"Baseline Summary")
        print(f"{'='*80}")
        print(f"Total queries: {summary['total_queries']}")
        print(f"Successful: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        print(f"Total time: {summary['total_time']:.2f}s")
        print(f"\nResults saved to: {output_file}")

        return summary


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="TPC-DS Benchmark")
    parser.add_argument("--host", default="localhost", help="MySQL host")
    parser.add_argument("--port", type=int, default=3306, help="MySQL port")
    parser.add_argument("--user", default="root", help="MySQL user")
    parser.add_argument("--password", default="", help="MySQL password")
    parser.add_argument("--database", default="tpcds", help="Database name")
    parser.add_argument("--queries", nargs="+", help="Query names to benchmark")
    parser.add_argument("--num-runs", type=int, default=3, help="Number of runs per query")

    args = parser.parse_args()

    # 默认目标查询
    target_queries = args.queries or [
        "q77", "q80", "q87", "q19", "q37",
        "q13", "q41", "q51", "q64", "q82"
    ]

    benchmark = TPCDSBenchmark(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database
    )

    # 运行基线测试
    benchmark.run_baseline_benchmark(target_queries, num_runs=args.num_runs)

    return 0


if __name__ == "__main__":
    sys.exit(main())
