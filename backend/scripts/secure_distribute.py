import os
import subprocess
import sys
from pathlib import Path

def obfuscate_project():
    """
    🏛️ [Spine-Core 商业分发加固]:
    使用 PyArmor 对核心算法进行混淆，并限制运行环境。
    """
    print("🛡️ 正在启动 PyArmor 代码混淆流程...")
    
    # 核心受保护目录
    core_services = "app/services"
    dist_path = "dist"
    
    try:
        # 1. 检查 pyarmor 是否安装
        subprocess.run(["pyarmor", "--version"], check=True, capture_output=True)
    except:
        print("⚠️ 未检测到 pyarmor，正在尝试安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyarmor"], check=True)

    # 2. 执行混淆
    # - recursive: 递归处理目录
    # - output: 输出到 dist 文件夹
    cmd = [
        "pyarmor", "gen", 
        "--recursive", 
        "--output", dist_path,
        core_services
    ]
    
    print(f"🚀 正在执行混淆命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ 混淆完成！受保护的代码已输出至: {Path(dist_path).resolve()}")
        print("💡 商业建议：分发给合作伙伴时，仅提供 dist 目录下的内容，不提供源码。")
    else:
        print(f"❌ 混淆失败: {result.stderr}")

if __name__ == "__main__":
    obfuscate_project()
