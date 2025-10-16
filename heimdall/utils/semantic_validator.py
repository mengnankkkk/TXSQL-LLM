"""
SQL语义验证器的简化Python实现
用于原型验证和测试
"""

import re
import sqlparse
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """验证结果"""
    is_equivalent: bool
    confidence: float
    reason: str
    differences: List[str]


class SimpleSemanticValidator:
    """简化版语义验证器

    注意：这是一个启发式验证器，用于快速原型开发
    生产环境应使用C++实现的完整验证器
    """

    def __init__(self):
        self.rules = [
            self._check_basic_structure,
            self._check_tables_used,
            self._check_columns_projected,
            self._check_join_conditions,
            self._check_filter_conditions
        ]

    def validate(self, sql1: str, sql2: str) -> ValidationResult:
        """验证两个SQL是否语义等价"""

        # 标准化SQL
        norm1 = self._normalize(sql1)
        norm2 = self._normalize(sql2)

        # 完全相同
        if norm1 == norm2:
            return ValidationResult(
                is_equivalent=True,
                confidence=1.0,
                reason="Queries are identical after normalization",
                differences=[]
            )

        # 解析SQL
        parsed1 = self._parse(norm1)
        parsed2 = self._parse(norm2)

        # 应用验证规则
        differences = []
        confidence_scores = []

        for rule in self.rules:
            is_same, conf, diff = rule(parsed1, parsed2)
            confidence_scores.append(conf)
            if diff:
                differences.extend(diff)

        # 计算总体置信度
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        is_equivalent = avg_confidence >= 0.9 and len(differences) == 0

        reason = "Likely equivalent" if is_equivalent else "Differences detected"

        return ValidationResult(
            is_equivalent=is_equivalent,
            confidence=avg_confidence,
            reason=reason,
            differences=differences
        )

    def _normalize(self, sql: str) -> str:
        """标准化SQL"""
        # 移除注释和多余空白
        sql = sqlparse.format(
            sql,
            keyword_case='upper',
            strip_comments=True,
            reindent=True
        )

        # 移除多余空白
        sql = re.sub(r'\s+', ' ', sql).strip()

        return sql

    def _parse(self, sql: str) -> Dict:
        """解析SQL结构"""
        parsed = sqlparse.parse(sql)[0]

        structure = {
            'type': self._get_statement_type(parsed),
            'tables': self._extract_tables(sql),
            'columns': self._extract_columns(sql),
            'where': self._extract_where_clause(sql),
            'joins': self._extract_joins(sql),
            'group_by': self._extract_group_by(sql),
            'order_by': self._extract_order_by(sql)
        }

        return structure

    def _get_statement_type(self, parsed) -> str:
        """获取语句类型"""
        return parsed.get_type()

    def _extract_tables(self, sql: str) -> List[str]:
        """提取表名"""
        # 简化实现：使用正则表达式
        tables = []

        # FROM子句
        from_match = re.search(r'FROM\s+(\w+(?:\s+\w+)?)', sql, re.IGNORECASE)
        if from_match:
            tables.append(from_match.group(1).strip())

        # JOIN子句
        join_matches = re.findall(r'JOIN\s+(\w+(?:\s+\w+)?)', sql, re.IGNORECASE)
        tables.extend([m.strip() for m in join_matches])

        return sorted(set(tables))

    def _extract_columns(self, sql: str) -> List[str]:
        """提取选择的列"""
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
        if not select_match:
            return []

        cols_str = select_match.group(1)

        # 处理SELECT *
        if '*' in cols_str:
            return ['*']

        # 分割列
        columns = [c.strip() for c in cols_str.split(',')]
        return sorted(columns)

    def _extract_where_clause(self, sql: str) -> str:
        """提取WHERE子句"""
        where_match = re.search(r'WHERE\s+(.*?)(?:GROUP BY|ORDER BY|$)', sql, re.IGNORECASE | re.DOTALL)
        if where_match:
            return where_match.group(1).strip()
        return ""

    def _extract_joins(self, sql: str) -> List[str]:
        """提取JOIN条件"""
        joins = re.findall(r'(INNER|LEFT|RIGHT|FULL)?\s*JOIN\s+\w+\s+ON\s+(.*?)(?:JOIN|WHERE|GROUP|ORDER|$)',
                          sql, re.IGNORECASE)
        return [f"{j[0]} {j[1]}".strip() for j in joins]

    def _extract_group_by(self, sql: str) -> List[str]:
        """提取GROUP BY列"""
        group_match = re.search(r'GROUP BY\s+(.*?)(?:HAVING|ORDER BY|$)', sql, re.IGNORECASE)
        if group_match:
            return sorted([c.strip() for c in group_match.group(1).split(',')])
        return []

    def _extract_order_by(self, sql: str) -> List[str]:
        """提取ORDER BY列"""
        order_match = re.search(r'ORDER BY\s+(.*?)$', sql, re.IGNORECASE)
        if order_match:
            return [c.strip() for c in order_match.group(1).split(',')]
        return []

    # 验证规则
    def _check_basic_structure(self, p1: Dict, p2: Dict) -> Tuple[bool, float, List[str]]:
        """检查基本结构"""
        if p1['type'] != p2['type']:
            return False, 0.0, [f"Statement type mismatch: {p1['type']} vs {p2['type']}"]
        return True, 1.0, []

    def _check_tables_used(self, p1: Dict, p2: Dict) -> Tuple[bool, float, List[str]]:
        """检查使用的表"""
        tables1 = set(p1['tables'])
        tables2 = set(p2['tables'])

        if tables1 != tables2:
            diff = list(tables1.symmetric_difference(tables2))
            return False, 0.5, [f"Different tables used: {diff}"]

        return True, 1.0, []

    def _check_columns_projected(self, p1: Dict, p2: Dict) -> Tuple[bool, float, List[str]]:
        """检查投影列"""
        cols1 = set(p1['columns'])
        cols2 = set(p2['columns'])

        # SELECT * 等价处理
        if '*' in cols1 or '*' in cols2:
            return True, 0.9, []

        if cols1 != cols2:
            return False, 0.7, [f"Different columns: {cols1} vs {cols2}"]

        return True, 1.0, []

    def _check_join_conditions(self, p1: Dict, p2: Dict) -> Tuple[bool, float, List[str]]:
        """检查JOIN条件"""
        joins1 = set(p1['joins'])
        joins2 = set(p2['joins'])

        if joins1 != joins2:
            return False, 0.8, ["Join conditions differ"]

        return True, 1.0, []

    def _check_filter_conditions(self, p1: Dict, p2: Dict) -> Tuple[bool, float, List[str]]:
        """检查过滤条件"""
        where1 = self._normalize_condition(p1['where'])
        where2 = self._normalize_condition(p2['where'])

        if where1 != where2:
            return False, 0.7, ["Filter conditions differ"]

        return True, 1.0, []

    def _normalize_condition(self, condition: str) -> str:
        """标准化条件表达式"""
        # 移除多余空白
        condition = re.sub(r'\s+', ' ', condition).strip()

        # 标准化操作符
        condition = condition.replace('!=', '<>')

        # 排序AND条件（简化处理）
        if ' AND ' in condition.upper():
            parts = re.split(r'\s+AND\s+', condition, flags=re.IGNORECASE)
            parts = sorted([p.strip() for p in parts])
            condition = ' AND '.join(parts)

        return condition


if __name__ == "__main__":
    # 测试
    validator = SimpleSemanticValidator()

    # 测试用例1: 完全相同
    sql1 = "SELECT * FROM customer WHERE customer_id > 100"
    sql2 = "SELECT * FROM customer WHERE customer_id > 100"
    result = validator.validate(sql1, sql2)
    print(f"Test 1: {result.is_equivalent} (confidence: {result.confidence:.2f})")

    # 测试用例2: 子查询展开
    sql1 = """
    SELECT * FROM customer
    WHERE customer_sk IN (SELECT customer_sk FROM sales WHERE price > 100)
    """
    sql2 = """
    SELECT DISTINCT c.*
    FROM customer c
    INNER JOIN sales s ON c.customer_sk = s.customer_sk
    WHERE s.price > 100
    """
    result = validator.validate(sql1, sql2)
    print(f"Test 2: {result.is_equivalent} (confidence: {result.confidence:.2f})")
    if result.differences:
        print(f"  Differences: {result.differences}")
