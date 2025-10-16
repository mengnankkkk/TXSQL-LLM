/**
 * @file heimdall_optimizer.h
 * @brief Heimdall优化器集成接口
 */

#ifndef HEIMDALL_OPTIMIZER_H
#define HEIMDALL_OPTIMIZER_H

#include "../validator/semantic_validator.h"
#include "../llm_generator/llm_client.h"
#include "../llm_generator/prompt_builder.h"
#include <string>
#include <memory>
#include <chrono>

namespace heimdall {
namespace optimizer {

/**
 * @brief 优化结果
 */
struct OptimizationResult {
    bool optimized;                    // 是否成功优化
    std::string original_sql;          // 原始SQL
    std::string optimized_sql;         // 优化后SQL
    double estimated_cost_original;    // 原始代价估算
    double estimated_cost_optimized;   // 优化后代价估算
    double improvement_ratio;          // 改进比率
    std::chrono::milliseconds total_time;  // 总耗时

    struct Stats {
        int candidates_generated;      // 生成的候选数
        int candidates_validated;      // 验证通过的候选数
        double llm_time_ms;           // LLM生成时间
        double validation_time_ms;    // 验证时间
        double cost_estimation_time_ms;  // 代价估算时间
    } stats;

    std::string reason;               // 优化/未优化原因
};

/**
 * @brief 优化策略
 */
struct OptimizationStrategy {
    // 触发条件
    bool enable_for_subqueries;       // 包含子查询时触发
    bool enable_for_complex_joins;    // 复杂JOIN时触发
    int min_estimated_cost;           // 最小估算代价阈值

    // 生成配置
    int max_candidates;               // 最大候选数
    double validation_timeout_sec;    // 验证超时

    // 选择策略
    enum class SelectionMode {
        BEST_COST,                    // 选择代价最低
        FIRST_VALID,                  // 选择首个有效
        CONSERVATIVE                  // 保守策略(要求显著改进)
    } selection_mode;

    double min_improvement_ratio;     // 最小改进比率

    OptimizationStrategy()
        : enable_for_subqueries(true),
          enable_for_complex_joins(true),
          min_estimated_cost(1000),
          max_candidates(5),
          validation_timeout_sec(10.0),
          selection_mode(SelectionMode::BEST_COST),
          min_improvement_ratio(1.2) {}
};

/**
 * @brief Heimdall主优化器
 */
class HeimdallOptimizer {
public:
    HeimdallOptimizer();
    ~HeimdallOptimizer();

    /**
     * @brief 初始化优化器
     */
    bool initialize(const std::string& config_path);

    /**
     * @brief 优化SQL查询
     */
    OptimizationResult optimize(const std::string& sql,
                               void* txsql_thd = nullptr);

    /**
     * @brief 设置优化策略
     */
    void setStrategy(const OptimizationStrategy& strategy);

    /**
     * @brief 设置LLM客户端
     */
    void setLLMClient(std::shared_ptr<llm::LLMClient> client);

    /**
     * @brief 设置验证器
     */
    void setValidator(std::shared_ptr<validator::SemanticValidator> validator);

    /**
     * @brief 获取统计信息
     */
    struct Statistics {
        uint64_t total_queries;
        uint64_t optimized_queries;
        uint64_t failed_validations;
        double avg_improvement_ratio;
        double avg_optimization_time_ms;
        uint64_t cache_hits;
    };
    Statistics getStatistics() const;

    /**
     * @brief 重置统计信息
     */
    void resetStatistics();

    /**
     * @brief 启用/禁用优化器
     */
    void setEnabled(bool enabled);
    bool isEnabled() const;

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;

    // 核心流程
    bool shouldOptimize(const std::string& sql);
    std::vector<std::string> generateCandidates(const std::string& sql);
    std::vector<std::string> validateCandidates(
        const std::string& original_sql,
        const std::vector<std::string>& candidates);
    std::string selectBestCandidate(
        const std::string& original_sql,
        const std::vector<std::string>& validated_candidates);
    double estimateCost(const std::string& sql, void* thd);
};

/**
 * @brief TXSQL集成钩子
 */
class TXSQLIntegration {
public:
    /**
     * @brief 在TXSQL优化器中注册Heimdall
     *
     * 该函数应在TXSQL启动时调用，将Heimdall注册为
     * 一个优化Pass
     */
    static bool registerWithTXSQL();

    /**
     * @brief TXSQL优化器回调函数
     *
     * 该函数会被TXSQL在查询优化阶段调用
     */
    static int optimizerCallback(void* thd, void* query_block);

    /**
     * @brief 获取全局优化器实例
     */
    static HeimdallOptimizer& getInstance();

private:
    static std::unique_ptr<HeimdallOptimizer> instance_;
};

} // namespace optimizer
} // namespace heimdall

#endif
