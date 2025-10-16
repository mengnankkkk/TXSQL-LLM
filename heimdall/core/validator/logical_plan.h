/**
 * @file logical_plan.h
 * @brief 逻辑执行计划的抽象表示和序列化
 */

#ifndef HEIMDALL_LOGICAL_PLAN_H
#define HEIMDALL_LOGICAL_PLAN_H

#include <string>
#include <vector>
#include <memory>
#include <unordered_map>

namespace heimdall {
namespace validator {

enum class PlanNodeType {
    SCAN, JOIN, FILTER, PROJECT, AGGREGATE,
    SORT, SUBQUERY, UNION, LIMIT, UNKNOWN
};

enum class ExprType {
    COLUMN_REF, LITERAL, BINARY_OP, UNARY_OP,
    FUNCTION, SUBQUERY_EXPR, CASE_EXPR, IN_EXPR,
    EXISTS_EXPR, UNKNOWN_EXPR
};

class ExpressionNode {
public:
    ExprType type;
    std::string op;
    std::string value;
    std::vector<std::shared_ptr<ExpressionNode>> children;

    ExpressionNode(ExprType t) : type(t) {}
    std::string toJson() const;
    std::shared_ptr<ExpressionNode> canonicalize() const;
    bool equals(const std::shared_ptr<ExpressionNode>& other) const;
};

class LogicalPlanNode {
public:
    PlanNodeType type;
    std::string id;
    std::string table_name;
    std::string join_type;
    std::shared_ptr<ExpressionNode> condition;
    std::vector<std::string> projected_columns;
    std::vector<std::string> group_by_columns;
    std::vector<std::shared_ptr<LogicalPlanNode>> children;

    LogicalPlanNode(PlanNodeType t) : type(t) {}
    std::string toJson() const;
    std::shared_ptr<LogicalPlanNode> clone() const;
};

class LogicalPlan {
public:
    std::shared_ptr<LogicalPlanNode> root;
    std::string original_sql;
    std::unordered_map<std::string, std::string> metadata;

    LogicalPlan() : root(nullptr) {}
    std::string toJsonString() const;
    LogicalPlan canonicalize() const;
    bool equals(const LogicalPlan& other) const;
    std::string toPrettyString() const;
};

class PlanExtractor {
public:
    static LogicalPlan extractFromTXSQL(void* thd, const std::string& sql);
private:
    static std::shared_ptr<LogicalPlanNode> convertNode(void* txsql_node);
};

} // namespace validator
} // namespace heimdall

#endif
