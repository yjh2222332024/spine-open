import sys
import os
# 将 backend 目录加入路径，以便导入 app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.parser import hybrid_parser
import json

def test_parser(file_path):
    print(f"\n--- 测试文件: {os.path.basename(file_path)} ---")
    if not os.path.exists(file_path):
        print(f"错误: 文件 {file_path} 不存在，请确保路径正确。")
        return

    try:
        toc = hybrid_parser.extract_toc(file_path)
        print(f"解析成功！获取到 {len(toc)} 条目录项。")
        
        # 打印前 5 条结果
        for item in toc[:5]:
            print(f"  [Level {item['level']}] Page {item['page']}: {item['title']} (ID: {item['id'][:8]}...)")
            
        if not toc:
            print("警告: 未能提取到任何目录项。")
            
    except Exception as e:
        print(f"测试过程中发生异常: {str(e)}")

if __name__ == "__main__":
    # 路径相对于 backend 目录
    target_pdf = "temp_uploads/cd568458-b938-453b-acf5-be9bc47a6fad.pdf"
    test_parser(target_pdf)

