import pytest
from app.agents.nodes.llm_recovery import llm_recovery_node
from app.agents.state import DocumentState

def test_llm_recovery_healing():
    """验证语义修复节点是否能修正页码倒流和层级断崖"""
    # 模拟一个极其破碎的 TOC
    broken_toc = [
        {"id": "1", "title": "Section 1", "page": 10, "level": 1},
        {"id": "2", "title": "Section 1.1", "page": 5, "level": 3}, # 1. 页码倒流(10->5) 2. 层级跳跃(1->3)
        {"id": "3", "title": "Section 1.2", "page": 12, "level": 2}
    ]
    
    state = DocumentState(
        structured_toc=broken_toc,
        metadata={"conflict_report": [{"msg": "Critical data inconsistency"}]}
    )
    
    result = llm_recovery_node(state)
    
    print(f"\nLLM Recovery Test Result:")
    recovered = result.get("structured_toc", [])
    for item in recovered:
        print(f"Node: {item['title']} | Page: {item['page']} | Level: {item['level']} | Recovered: {item.get('is_llm_recovered')}")

    # 验证 1: 页码倒流修复 (5 -> 10)
    assert recovered[1]["page"] == 10
    assert recovered[1]["is_llm_recovered"] is True
    
    # 验证 2: 层级跳跃修复 (3 -> 2)
    assert recovered[1]["level"] == 2
    
    # 验证 3: 状态标记
    assert result["metadata"]["status"] == "recovered_by_llm"
    assert result["confidence_score"] == 0.65

if __name__ == "__main__":
    test_llm_recovery_healing()
