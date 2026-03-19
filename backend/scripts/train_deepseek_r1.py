"""
SpineDoc: DeepSeek-R1 Distill Trainer
=====================================
标准 QLoRA 微调脚本，放弃 Unsloth 以换取绝对稳定性。
支持 4060 (8GB) 训练 7B/8B 级模型。

Author: Yan Junhao (严俊皓)
Architecture: Genius Architect Mode
"""

import os
import torch
import subprocess
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset

# 1. WSL2 代理与存储路径设置
def setup_environment():
    # 强制设置 Hugging Face 缓存到 E 盘 (WSL2 挂载路径)
    cache_path = "/mnt/e/study/code/SpineDoc/.hf_cache"
    os.environ["HF_HOME"] = cache_path
    os.environ["HUGGINGFACE_HUB_CACHE"] = cache_path
    print(f"🚀 Model Cache strictly set to: {cache_path}")

    try:
        result = subprocess.run(["ip", "route"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if "default" in line:
                win_ip = line.split()[2]
                proxy_url = f"http://{win_ip}:7897"
                os.environ["http_proxy"] = proxy_url
                os.environ["https_proxy"] = proxy_url
                print(f"📡 Proxy set: {proxy_url}")
                break
    except: pass

setup_environment()
cache_dir = "/mnt/e/study/code/SpineDoc/.hf_cache"

# ... (后续加载模型时加入 cache_dir 参数) ...

# 2. 配置与模型 (选择 DeepSeek-R1 蒸馏版)
model_id = "deepseek-ai/DeepSeek-R1-Distill-Llama-8B"
# 备选: "Qwen/Qwen2.5-7B-Instruct"

# 3. 4-bit 量化配置 (核心：让 4060 跑起 8B 模型)
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
)

print(f"📦 Loading Model: {model_id}...")
tokenizer = AutoTokenizer.from_pretrained(model_id, cache_dir=cache_dir)
tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
    cache_dir=cache_dir
)

# 4. LoRA 配置 (针对 8GB 显存压榨)
model = prepare_model_for_kbit_training(model)
lora_config = LoraConfig(
    r=8, 
    lora_alpha=16,
    target_modules=["q_proj", "v_proj"], # 仅训练关键层以省显存
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)
model = get_peft_model(model, lora_config)

# 5. 数据处理
def tokenize_function(examples):
    # 构建 Alpaca 格式
    prompts = []
    for i in range(len(examples["instruction"])):
        thought = examples["thought"][i] if examples["thought"][i] else ""
        text = f"### Instruction:\n{examples['instruction'][i]}\n\n### Input:\n{examples['input'][i]}\n\n### Thought:\n{thought}\n\n### Response:\n{examples['output'][i]}"
        prompts.append(text)
    return tokenizer(prompts, truncation=True, max_length=1024, padding="max_length")

dataset = load_dataset("json", data_files={"train": "academic_full_distilled.jsonl"}, split="train")
tokenized_dataset = dataset.map(tokenize_function, batched=True, remove_columns=dataset.column_names)

# 6. 训练参数 (4060 极限优化版)
training_args = TrainingArguments(
    output_dir="./deepseek_spinedoc_results",
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8, # 累计步数以弥补 batch size
    learning_rate=2e-4,
    fp16=not torch.cuda.is_bf16_supported(),
    bf16=torch.cuda.is_bf16_supported(),
    logging_steps=1,
    max_steps=30, # 先跑 30 步验证
    save_steps=10,
    optim="paged_adamw_8bit", # 极其关键：将优化器状态也移出显存
    gradient_checkpointing=True,
    report_to="none"
)

# 7. 启动训练
print("🔥 [SpineDoc] DeepSeek-R1 Distillation Training Ignited!")
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
    data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
)

trainer.train()

# 8. 保存 LoRA 权重
model.save_pretrained("spinedoc_deepseek_lora")
print("✅ Expert DeepSeek Model Saved!")
