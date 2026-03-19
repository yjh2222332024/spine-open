import pytest
from app.agents.nodes.validator import validator_node
from app.agents.state import DocumentState, DocumentType, DocumentType

def test_validator_loop_prevention():
    """验证重试次数超限后是否能安全停止循环"""
    # 构造一个糟糕的 TOC (页码倒流)
    bad_toc = [
        {"id": "1", "title": "Chap 1", "page": 20},
        {"id": "2", "title": "Chap 2", "page": 10}
    ]
    
    state = DocumentState(
        structured_toc=bad_toc,
        total_pages=100,
        document_type=DocumentType.NATIVE,
        retry_count=3, # 已达到重试上限
        max_retries=3,
        metadata={"conflict_report": []},
        instructions=[]
    )
    
    result = validator_node(state)
    
    print(f"\nLoop Prevention Test Result:")
    print(f"Confidence: {result.get('confidence_score')}")
    print(f"Status: {result.get('metadata', {}).get('status')}")
    
    # 验证是否没有发出新的指令，且状态为超限
    assert result["metadata"]["status"] == "max_retries_exceeded"
    assert "instructions" not in result

def test_validator_adaptive_density():
    """验证 Native 类型在低密度下的评分惩罚"""
    # 100 页只有 1 条目录，对 Native 来说是无法接受的
    low_density_toc = [{"id": "1", "title": "Only One", "page": 1}]
    
    state = DocumentState(
        structured_toc=low_density_toc,
        total_pages=100,
        document_type=DocumentType.NATIVE,
        retry_count=0,
        max_retries=3,
        metadata={"conflict_report": []},
        instructions=[]
    )
    
    result = validator_node(state)
    print(f"\nAdaptive Density Score (Native): {result.get('confidence_score')}")
    
    # 初始 1.0 - 0.5 (密度惩罚) = 0.5
    assert result["confidence_score"] <= 0.6

if __name__ == "__main__":
    test_validator_loop_prevention()
    test_validator_adaptive_density()
