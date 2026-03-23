from langgraph.graph import StateGraph, END
from spine_cli.core.agents.state import DocumentState, DocumentType
from spine_cli.core.agents.nodes.classifier import classifier_node
from spine_cli.core.agents.nodes.structure_agent import structure_agent_node
from spine_cli.core.agents.nodes.validator import validator_node
from spine_cli.core.agents.nodes.llm_recovery import llm_recovery_node

def create_spine_graph():
    workflow = StateGraph(DocumentState)
    
    workflow.add_node("classifier", classifier_node)
    workflow.add_node("structure_agent", structure_agent_node)
    workflow.add_node("validator", validator_node)
    workflow.add_node("llm_recovery", llm_recovery_node)
    
    workflow.set_entry_point("classifier")
    
    workflow.add_edge("classifier", "structure_agent")
    workflow.add_edge("structure_agent", "validator")
    
    def routing(state):
        if state["confidence_score"] >= 0.6: return END
        return "llm_recovery"
        
    workflow.add_conditional_edges("validator", routing, {END: END, "llm_recovery": "llm_recovery"})
    workflow.add_edge("llm_recovery", END)
    
    return workflow.compile()
