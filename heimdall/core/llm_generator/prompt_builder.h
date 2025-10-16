/**
 * @file prompt_builder.h
 * @brief 智能Prompt构建器
 */

#ifndef HEIMDALL_PROMPT_BUILDER_H
#define HEIMDALL_PROMPT_BUILDER_H

#include <string>
#include <vector>
#include <unordered_map>

namespace heimdall {
namespace llm {

/**
 * @brief Schema信息
 */
struct TableSchema {
    std::string table_name;
    std::vector<std::string> columns;
    std::vector<std::string> primary_keys;
    std::vector<std::string> foreign_keys;
    std::string create_statement;
};

/**
 * @brief Few-shot示例
 */
struct FewShotExample {
    std::string original_sql;
    std::string optimized_sql;
    std::string explanation;
    double speedup_ratio;
};

/**
 * @brief Prompt构建器
 */
class PromptBuilder {
public:
    PromptBuilder();

    /**
     * @brief 构建完整的重写Prompt
     */
    std::string buildRewritePrompt(
        const std::string& original_sql,
        const std::vector<TableSchema>& schemas,
        bool use_few_shot = true) const;

    /**
     * @brief 添加Few-shot示例
     */
    void addFewShotExample(const FewShotExample& example);

    /**
     * @brief 设置系统提示词
     */
    void setSystemPrompt(const std::string& prompt);

    /**
     * @brief 设置优化目标
     */
    enum class OptimizationGoal {
        PERFORMANCE,      // 性能优先
        READABILITY,      // 可读性优先
        BALANCED          // 平衡
    };
    void setOptimizationGoal(OptimizationGoal goal);

    /**
     * @brief 启用特定优化技术提示
     */
    void enableOptimizationHints(const std::vector<std::string>& hints);

private:
    std::string system_prompt_;
    std::vector<FewShotExample> few_shot_examples_;
    OptimizationGoal optimization_goal_;
    std::vector<std::string> optimization_hints_;

    // 辅助函数
    std::string formatSchemas(const std::vector<TableSchema>& schemas) const;
    std::string formatFewShotExamples() const;
    std::string generateConstraints() const;
};

/**
 * @brief 默认Prompt模板
 */
namespace prompts {

extern const char* DEFAULT_SYSTEM_PROMPT;
extern const char* PERFORMANCE_FOCUSED_PROMPT;
extern const char* SAFETY_CONSTRAINTS;

} // namespace prompts

} // namespace llm
} // namespace heimdall

#endif
