#!/usr/bin/env python3
"""
阶段1环境检查和准备脚本
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from typing import Dict, List, Tuple

class Phase1Setup:
    """阶段1环境准备"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.checks_passed = []
        self.checks_failed = []

    def run_all_checks(self):
        """运行所有环境检查"""
        print("=" * 80)
        print("Heimdall 阶段1环境检查")
        print("=" * 80)
        print()

        checks = [
            ("Python版本", self.check_python),
            ("必要的Python包", self.check_python_packages),
            ("MySQL/TXSQL", self.check_mysql),
            ("CMake", self.check_cmake),
            ("C++编译器", self.check_cpp_compiler),
            ("Git", self.check_git),
            ("项目目录结构", self.check_directories),
        ]

        for name, check_func in checks:
            print(f"检查 {name}...", end=" ")
            try:
                result, message = check_func()
                if result:
                    print(f"[OK] {message}")
                    self.checks_passed.append(name)
                else:
                    print(f"[FAIL] {message}")
                    self.checks_failed.append(name)
            except Exception as e:
                print(f"[ERROR] {str(e)}")
                self.checks_failed.append(name)
            print()

        self.print_summary()
        return len(self.checks_failed) == 0

    def check_python(self) -> Tuple[bool, str]:
        """检查Python版本"""
        version = sys.version_info
        if version.major >= 3 and version.minor >= 8:
            return True, f"Python {version.major}.{version.minor}.{version.micro}"
        return False, f"需要Python 3.8+，当前版本: {version.major}.{version.minor}"

    def check_python_packages(self) -> Tuple[bool, str]:
        """检查必要的Python包"""
        required = ["requests", "pyyaml", "sqlparse", "mysql.connector"]
        missing = []

        for package in required:
            try:
                __import__(package.replace("-", "_"))
            except ImportError:
                missing.append(package)

        if not missing:
            return True, f"所有必要包已安装"
        else:
            return False, f"缺少包: {', '.join(missing)}。运行: pip install -r requirements.txt"

    def check_mysql(self) -> Tuple[bool, str]:
        """检查MySQL/TXSQL是否可用"""
        try:
            result = subprocess.run(
                ["mysql", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                return True, f"已安装: {version}"
            return False, "MySQL未找到"
        except FileNotFoundError:
            return False, "MySQL未安装或不在PATH中"
        except Exception as e:
            return False, f"检查失败: {str(e)}"

    def check_cmake(self) -> Tuple[bool, str]:
        """检查CMake"""
        try:
            result = subprocess.run(
                ["cmake", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.split('\n')[0]
                return True, version
            return False, "CMake未找到"
        except FileNotFoundError:
            return False, "CMake未安装。请从 https://cmake.org/ 下载"
        except Exception as e:
            return False, f"检查失败: {str(e)}"

    def check_cpp_compiler(self) -> Tuple[bool, str]:
        """检查C++编译器"""
        compilers = [
            ("g++", ["g++", "--version"]),
            ("clang++", ["clang++", "--version"]),
            ("cl", ["cl"]),  # MSVC on Windows
        ]

        for name, cmd in compilers:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 or "Microsoft" in result.stderr:
                    return True, f"找到编译器: {name}"
            except:
                continue

        return False, "未找到C++编译器 (g++/clang++/MSVC)"

    def check_git(self) -> Tuple[bool, str]:
        """检查Git"""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            return False, "Git未找到"
        except FileNotFoundError:
            return False, "Git未安装"

    def check_directories(self) -> Tuple[bool, str]:
        """检查项目目录结构"""
        required_dirs = [
            "heimdall/core/validator",
            "heimdall/core/llm_generator",
            "heimdall/core/optimizer_integration",
            "heimdall/utils",
            "heimdall/config",
            "scripts",
            "data/queries",
            "data/results",
            "docs"
        ]

        missing = []
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                missing.append(dir_path)

        if not missing:
            return True, "所有目录已创建"
        else:
            return False, f"缺少目录: {', '.join(missing)}"

    def print_summary(self):
        """打印检查总结"""
        print("\n" + "=" * 80)
        print("环境检查总结")
        print("=" * 80)
        print(f"[OK] 通过: {len(self.checks_passed)}")
        print(f"[FAIL] 失败: {len(self.checks_failed)}")

        if self.checks_failed:
            print("\n需要解决的问题:")
            for item in self.checks_failed:
                print(f"  - {item}")
            print("\n请按照上述提示安装缺失的组件后重新运行此脚本。")
        else:
            print("\n[SUCCESS] 所有检查通过！您可以继续进行阶段1的下一步。")
            print("\n下一步:")
            print("  1. 如果还没有TXSQL源码，运行: python scripts/setup_txsql.py")
            print("  2. 准备TPC-DS数据集: python scripts/setup_tpcds.py")
            print("  3. 运行基线测试: python scripts/benchmark_tpcds.py")

    def create_phase1_guide(self):
        """创建阶段1详细指南"""
        guide_path = self.project_root / "docs" / "PHASE1_GUIDE.md"

        guide_content = """# 阶段1实施指南

## 当前进度

- [ ] 环境检查完成
- [ ] TXSQL源码获取
- [ ] TXSQL编译成功
- [ ] TPC-DS工具准备
- [ ] TPC-DS数据生成
- [ ] 数据导入MySQL
- [ ] 基线基准测试
- [ ] 靶心查询识别
- [ ] 手动优化分析

## 详细步骤

### Step 1: 环境检查
```bash
python scripts/phase1_setup.py
```

### Step 2: 获取TXSQL源码
```bash
# 方案A: 克隆官方仓库
git clone https://github.com/Tencent/TXSQL.git ../TXSQL

# 方案B: 使用MySQL 8.0源码
git clone https://github.com/mysql/mysql-server.git ../mysql-8.0
```

### Step 3: 编译TXSQL（Linux/macOS）
```bash
cd ../TXSQL
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Debug \\
         -DWITH_DEBUG=1 \\
         -DDOWNLOAD_BOOST=1 \\
         -DWITH_BOOST=../boost
make -j$(nproc)
```

### Step 4: 编译TXSQL（Windows）
```cmd
cd ..\\TXSQL
mkdir build && cd build
cmake .. -G "Visual Studio 16 2019" -A x64
cmake --build . --config Debug
```

### Step 5: 准备TPC-DS
```bash
python scripts/setup_tpcds.py --scale 1GB
```

### Step 6: 运行基线测试
```bash
python scripts/benchmark_tpcds.py --num-runs 3
```

### Step 7: 分析结果
```bash
python scripts/analyze_baseline.py
```

## 常见问题

### Q: TXSQL编译失败
A: 检查依赖是否完整安装，参考TXSQL官方文档

### Q: TPC-DS数据生成失败
A: 确保有足够磁盘空间（1GB规模约需5GB空间）

### Q: MySQL连接失败
A: 检查MySQL服务是否运行，端口是否正确

## 里程碑检查点

完成阶段1后，您应该具备：
- [x] 可运行的TXSQL实例
- [x] 完整的TPC-DS数据集
- [x] 基线性能数据
- [x] 3-5个已识别的靶心查询
"""

        guide_path.parent.mkdir(parents=True, exist_ok=True)
        with open(guide_path, 'w', encoding='utf-8') as f:
            f.write(guide_content)

        return guide_path


def main():
    setup = Phase1Setup()

    # 运行环境检查
    success = setup.run_all_checks()

    # 创建指南
    guide_path = setup.create_phase1_guide()
    print(f"\n详细指南已创建: {guide_path}")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
