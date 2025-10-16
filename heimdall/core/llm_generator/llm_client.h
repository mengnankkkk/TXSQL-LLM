/**
 * @file llm_client.h
 * @brief LLM API客户端封装
 */

#ifndef HEIMDALL_LLM_CLIENT_H
#define HEIMDALL_LLM_CLIENT_H

#include <string>
#include <vector>
#include <memory>
#include <functional>

namespace heimdall {
namespace llm {

/**
 * @brief LLM生成配置
 */
struct GenerationConfig {
    std::string model_name;       // 模型名称
    float temperature;            // 温度参数 [0.0, 2.0]
    int max_tokens;               // 最大token数
    int num_candidates;           // 生成候选数量
    bool use_few_shot;            // 是否使用few-shot示例

    GenerationConfig()
        : model_name("gpt-4"),
          temperature(0.3),
          max_tokens(2000),
          num_candidates(3),
          use_few_shot(true) {}
};

/**
 * @brief LLM响应
 */
struct LLMResponse {
    std::vector<std::string> candidates;  // SQL候选列表
    std::string raw_response;             // 原始响应
    bool success;                         // 是否成功
    std::string error_message;            // 错误信息
    double latency_ms;                    // 延迟(毫秒)

    LLMResponse() : success(false), latency_ms(0.0) {}
};

/**
 * @brief LLM提供商接口
 */
class LLMProvider {
public:
    virtual ~LLMProvider() = default;

    virtual LLMResponse generate(const std::string& prompt,
                                const GenerationConfig& config) = 0;
    virtual std::string getName() const = 0;
    virtual bool isAvailable() const = 0;
};

/**
 * @brief OpenAI API实现
 */
class OpenAIProvider : public LLMProvider {
public:
    explicit OpenAIProvider(const std::string& api_key);

    LLMResponse generate(const std::string& prompt,
                        const GenerationConfig& config) override;
    std::string getName() const override { return "OpenAI"; }
    bool isAvailable() const override;

private:
    std::string api_key_;
    std::string base_url_;
};

/**
 * @brief 本地模型提供商（通过HTTP API）
 */
class LocalModelProvider : public LLMProvider {
public:
    explicit LocalModelProvider(const std::string& endpoint);

    LLMResponse generate(const std::string& prompt,
                        const GenerationConfig& config) override;
    std::string getName() const override { return "LocalModel"; }
    bool isAvailable() const override;

private:
    std::string endpoint_;
};

/**
 * @brief LLM客户端管理器
 */
class LLMClient {
public:
    LLMClient();
    ~LLMClient();

    /**
     * @brief 注册LLM提供商
     */
    void registerProvider(std::shared_ptr<LLMProvider> provider);

    /**
     * @brief 设置当前使用的提供商
     */
    void setProvider(const std::string& provider_name);

    /**
     * @brief 生成SQL重写候选
     */
    LLMResponse generateRewrites(const std::string& original_sql,
                                const std::string& schema_context,
                                const GenerationConfig& config = GenerationConfig());

    /**
     * @brief 设置缓存机制
     */
    void enableCache(bool enable, size_t max_size = 1000);

    /**
     * @brief 获取缓存统计
     */
    struct CacheStats {
        size_t hits;
        size_t misses;
        double hit_rate;
    };
    CacheStats getCacheStats() const;

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

} // namespace llm
} // namespace heimdall

#endif
