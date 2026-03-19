"""
WSL2 GPU & Network Diagnostic
=============================
检查 WSL2 环境下的 GPU 可用性以及 Hugging Face 连接。
"""
import torch
import sys
import os
import subprocess

def set_wsl2_proxy():
    """架构师级补丁：在 WSL2 内部自动探测并设置 Windows 代理"""
    try:
        # 获取宿主机(Windows)的 IP
        result = subprocess.run(["ip", "route"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if "default" in line:
                win_ip = line.split()[2]
                proxy_url = f"http://{win_ip}:7890" # 假设端口 7890
                os.environ["http_proxy"] = proxy_url
                os.environ["https_proxy"] = proxy_url
                print(f"📡 WSL2 Proxy set to: {proxy_url}")
                break
    except Exception as e:
        print(f"⚠️ Proxy auto-config failed: {e}")

def diagnose():
    set_wsl2_proxy()
    from unsloth import FastLanguageModel # 放在设置代理之后导入
    print(f"🐍 Python Version: {sys.version}")
    print(f"🔥 Torch Version: {torch.__version__}")
    print(f"💎 CUDA Available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"🚀 GPU Device: {torch.cuda.get_device_name(0)}")
        
        print("📦 Attempting to load Llama 3.2 3B (Checking Network)...")
        try:
            # 仅加载 tokenizer 测试网络
            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name = "unsloth/Llama-3.2-3B-Instruct",
                load_in_4bit = True,
            )
            print("✅ Network & GPU are both READY!")
        except Exception as e:
            print(f"❌ Network/Download Error: {e}")
            print("💡 Suggestion: Please check your WSL2 proxy settings.")
    else:
        print("❌ GPU not detected inside WSL2.")

if __name__ == "__main__":
    diagnose()
