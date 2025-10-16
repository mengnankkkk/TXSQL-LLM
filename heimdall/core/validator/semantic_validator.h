/**
 * @file semantic_validator.h
 * @brief 语义等价性验证器核心引擎
 */

#ifndef HEIMDALL_SEMANTIC_VALIDATOR_H
#define HEIMDALL_SEMANTIC_VALIDATOR_H

#include "logical_plan.h"
#include <string>
#include <vector>

namespace heimdall {
namespace validator {

/**
 * @brief 验证结果
 */
struct ValidationResult {
    bool is_equivalent;           // 是否语义等价
    double confidence;            // 置信度 [0.0, 1.0]
    std::string reason;           // 详细原因
    std::vector<std::string> differences;  // 差异列表

    ValidationResult() : is_equivalent(false), confidence(0.0) {}
};

/**
 * @brief 范式化规则接口
 */
class CanonicalizationRule {
public:
    virtual ~CanonicalizationRule() = default;
    virtual std::shared_ptr<LogicalPlanNode> apply(
        const std::shared_ptr<LogicalPlanNode>& node) const = 0;
    virtual std::string getName() const = 0;
};

/**
 * @brief 语义验证器主类
 */
class SemanticValidator {
public:
    SemanticValidator();
    ~SemanticValidator();

    /**
     * @brief 验证两个SQL查询是否语义等价
     */
    ValidationResult validate(const std::string& original_sql,
                             const std::string& rewritten_sql);

    /**
     * @brief 验证两个逻辑计划是否等价
     */
    ValidationResult validatePlans(const LogicalPlan& plan1,
                                   const LogicalPlan& plan2);

    /**
     * @brief 注册自定义范式化规则
     */
    void registerRule(std::shared_ptr<CanonicalizationRule> rule);

    /**
     * @brief 设置验证模式
     */
    enum class ValidationMode {
        STRICT,      // 严格模式：完全匹配
        RELAXED,     // 宽松模式：允许列顺序等差异
        HEURISTIC    // 启发式：基于规则的推断
    };
    void setValidationMode(ValidationMode mode);

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;

    // 核心验证逻辑
    bool comparePlans(const LogicalPlan& plan1, const LogicalPlan& plan2);
    bool compareNodes(const std::shared_ptr<LogicalPlanNode>& node1,
                     const std::shared_ptr<LogicalPlanNode>& node2);
    bool compareExpressions(const std::shared_ptr<ExpressionNode>& expr1,
                           const std::shared_ptr<ExpressionNode>& expr2);
};

/**
 * @brief 预定义的范式化规则
 */
namespace rules {

// 交换律规则：JOIN顺序标准化
class CommutativeJoinRule : public CanonicalizationRule {
public:
    std::shared_ptr<LogicalPlanNode> apply(
        const std::shared_ptr<LogicalPlanNode>& node) const override;
    std::string getName() const override { return "CommutativeJoin"; }
};

// 关联律规则：连续JOIN重组
class AssociativeJoinRule : public CanonicalizationRule {
public:
    std::shared_ptr<LogicalPlanNode> apply(
        const std::shared_ptr<LogicalPlanNode>& node) const override;
    std::string getName() const override { return "AssociativeJoin"; }
};

// 子查询展开规则
class SubqueryUnnestingRule : public CanonicalizationRule {
public:
    std::shared_ptr<LogicalPlanNode> apply(
        const std::shared_ptr<LogicalPlanNode>& node) const override;
    std::string getName() const override { return "SubqueryUnnesting"; }
};

// 谓词下推规则
class PredicatePushdownRule : public CanonicalizationRule {
public:
    std::shared_ptr<LogicalPlanNode> apply(
        const std::shared_ptr<LogicalPlanNode>& node) const override;
    std::string getName() const override { return "PredicatePushdown"; }
};

// IN表达式展开规则
class InExpressionExpansionRule : public CanonicalizationRule {
public:
    std::shared_ptr<LogicalPlanNode> apply(
        const std::shared_ptr<LogicalPlanNode>& node) const override;
    std::string getName() const override { return "InExpansion"; }
};

} // namespace rules

} // namespace validator
} // namespace heimdall

#endif
