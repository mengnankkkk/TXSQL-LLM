cmake_minimum_required(VERSION 3.15)
project(Heimdall VERSION 1.0.0 LANGUAGES CXX)

# C++17标准
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 编译选项
if(MSVC)
    add_compile_options(/W4 /WX)
else()
    add_compile_options(-Wall -Wextra -Wpedantic -Werror)
endif()

# 依赖查找
find_package(Threads REQUIRED)

# 可选：JSON库
find_package(jsoncpp QUIET)
if(NOT jsoncpp_FOUND)
    message(STATUS "jsoncpp not found, will use bundled version")
    # 这里可以添加第三方JSON库的路径
endif()

# 可选：HTTP客户端库
find_package(CURL QUIET)
if(CURL_FOUND)
    add_definitions(-DUSE_CURL)
endif()

# 包含目录
include_directories(
    ${PROJECT_SOURCE_DIR}
    ${PROJECT_SOURCE_DIR}/heimdall
    ${PROJECT_SOURCE_DIR}/heimdall/core
)

# 验证器模块
add_library(heimdall_validator
    heimdall/core/validator/logical_plan.cpp
    heimdall/core/validator/semantic_validator.cpp
    heimdall/core/validator/canonicalization_rules.cpp
)
target_link_libraries(heimdall_validator
    Threads::Threads
)

# LLM生成器模块
add_library(heimdall_llm_generator
    heimdall/core/llm_generator/llm_client.cpp
    heimdall/core/llm_generator/prompt_builder.cpp
)
target_link_libraries(heimdall_llm_generator
    Threads::Threads
)
if(CURL_FOUND)
    target_link_libraries(heimdall_llm_generator CURL::libcurl)
endif()

# 优化器集成模块
add_library(heimdall_optimizer
    heimdall/core/optimizer_integration/heimdall_optimizer.cpp
    heimdall/core/optimizer_integration/txsql_integration.cpp
)
target_link_libraries(heimdall_optimizer
    heimdall_validator
    heimdall_llm_generator
    Threads::Threads
)

# 主库
add_library(heimdall SHARED
    $<TARGET_OBJECTS:heimdall_validator>
    $<TARGET_OBJECTS:heimdall_llm_generator>
    $<TARGET_OBJECTS:heimdall_optimizer>
)
target_link_libraries(heimdall
    Threads::Threads
)

# 测试可执行文件
add_executable(heimdall_test
    heimdall/tests/test_main.cpp
    heimdall/tests/test_validator.cpp
    heimdall/tests/test_llm_client.cpp
)
target_link_libraries(heimdall_test
    heimdall
)

# 安装规则
install(TARGETS heimdall
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
)

install(DIRECTORY heimdall/core/
    DESTINATION include/heimdall
    FILES_MATCHING PATTERN "*.h"
)

# CTest集成
enable_testing()
add_test(NAME heimdall_test COMMAND heimdall_test)

# 打包
set(CPACK_PROJECT_NAME ${PROJECT_NAME})
set(CPACK_PROJECT_VERSION ${PROJECT_VERSION})
include(CPack)
