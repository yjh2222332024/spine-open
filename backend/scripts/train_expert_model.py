"""
SpineDoc 4060 Turbo Trainer (WSL2 Stable Edition)
=================================================
针对 RTX 4060 (8GB) 优化的极速微调脚本。
解决了 WSL2/Linux 环境下的 Torch Inductor 初始化问题。

Author: Yan Junhao (严俊皓)
Architecture: Genius Architect Mode
"""

import os
import torch
import subprocess

# 🛡️ 架构师核心修正：WSL2 代理穿透逻辑
def set_wsl2_proxy():
    try:
        result = subprocess.run(["ip", "route"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if "default" in line:
                win_ip = line.split()[2]
                proxy_url = f"http://{win_ip}:7897"
                os.environ["http_proxy"] = proxy_url
                os.environ["https_proxy"] = proxy_url
                print(f"📡 WSL2 Proxy Active: {proxy_url}")
                break
    except: pass

set_wsl2_proxy()

# 🛡️ 显式初始化 Inductor 与 Dynamo
try:
    import torch._dynamo
    import torch._inductor.config
except ImportError:
    pass

from unsloth import FastLanguageModel
from datasets import load_dataset
from trl import SFTTrainer
from transformers import TrainingArguments
from unsloth import is_bfloat16_supported

# 1. 配置参数
max_seq_length = 2048 
dtype = None 
load_in_4bit = True 

# 2. 加载模型 (Llama 3.2 3B)
print("📦 Loading base model into VRAM...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "unsloth/Llama-3.2-3B-Instruct",
    max_seq_length = max_seq_length,
    dtype = dtype,
    load_in_4bit = load_in_4bit,
)

# 3. 配置 LoRA
model = FastLanguageModel.get_peft_model(
    model,
    r = 16,
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                      "gate_proj", "up_proj", "down_proj",],
    lora_alpha = 16,
    lora_dropout = 0,
    bias = "none",
    use_gradient_checkpointing = "unsloth",
    random_state = 3407,
)

# 4. 推理模板
alpaca_prompt = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{}

### Input:
{}

### Thought:
{}

### Response:
{}"""

def formatting_prompts_func(examples):
    instructions = examples["instruction"]
    inputs       = examples["input"]
    thoughts     = [t if (t and str(t).strip()) else "Reasoning based on document logic..." for t in examples.get("thought", [])]
    outputs      = examples["output"]
    texts = []
    for instruction, input, thought, output in zip(instructions, inputs, thoughts, outputs):
        text = alpaca_prompt.format(instruction, input, thought, output) + tokenizer.eos_token
        texts.append(text)
    return { "text" : texts, }

# 5. 加载数据集
dataset = load_dataset("json", data_files={"train": "academic_full_distilled.jsonl"}, split="train")
dataset = dataset.map(formatting_prompts_func, batched = True,)

# 6. 开启极速训练
trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = dataset,
    dataset_text_field = "text",
    max_seq_length = max_seq_length,
    dataset_num_proc = 2,
    packing = False,
    args = TrainingArguments(
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,
        warmup_steps = 5,
        max_steps = 20, 
        learning_rate = 2e-4,
        fp16 = not is_bfloat16_supported(),
        bf16 = is_bfloat16_supported(),
        logging_steps = 1,
        optim = "adamw_8bit",
        weight_decay = 0.01,
        lr_scheduler_type = "linear",
        seed = 3407,
        output_dir = "outputs",
    ),
)

# 🚀 启动！
print("🔥 [WSL2] Training ignited on RTX 4060...")
trainer_stats = trainer.train()

# 7. 保存
model.save_pretrained("spinedoc_lora_model")
tokenizer.save_pretrained("spinedoc_lora_model")
print("✅ Expert Model Saved Successfully!")
