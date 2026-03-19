import fitz
import os
import sys

# 将 app 所在目录添加到 Python 路径，确保能导入 app.services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.parser import hybrid_parser

def create_test_pdf(path: str):
    """创建一个包含目录的简单 PDF 文件用于测试"""
    doc = fitz.open()
    
    # 第一页
    page1 = doc.new_page()
    page1.insert_text((50, 50), "Chapter 1: Introduction")
    
    # 第二页
    page2 = doc.new_page()
    page2.insert_text((50, 50), "Chapter 2: Deep Dive")
    
    # 第三页 (子章节)
    page3 = doc.new_page()
    page3.insert_text((50, 50), "Section 2.1: Technical Details")
    
    # 设置目录 (TOC)
    # 格式: [层级, 标题, 页码]
    toc = [
        [1, "Chapter 1: Introduction", 1],
        [1, "Chapter 2: Deep Dive", 2],
        [2, "Section 2.1: Technical Details", 3]
    ]
    doc.set_toc(toc)
    doc.save(path)
    doc.close()

def test_parsing():
    test_pdf = "test_sample.pdf"
    try:
        print(f"--- 步骤 1: 生成测试 PDF ({test_pdf}) ---")
        create_test_pdf(test_pdf)
        
        print(f"--- 步骤 2: 调用 PDFParser 解析 ---")
        results = hybrid_parser.extract_toc(test_pdf)
        
        print("--- 步骤 3: 验证结果 ---")
        for i, entry in enumerate(results):
            print(f"层级: {entry['level']}, 标题: {entry['title']}, 页码: {entry['page']}")
            
        # 简单断言
        assert len(results) == 3
        assert results[0]["title"] == "Chapter 1: Introduction"
        assert results[2]["level"] == 2
        
        print("\n✅ 测试通过！解析器能够正确读取 PDF 目录。")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理临时文件
        if os.path.exists(test_pdf):
            os.remove(test_pdf)

if __name__ == "__main__":
    test_parsing()
