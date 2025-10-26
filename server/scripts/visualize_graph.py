# server/scripts/visualize_graph.py
"""
Visualize LangGraph workflows
Requires: pip install pygraphviz
"""

from src.workflows.ai_workflow import create_ai_workflow
from src.workflows.record_workflow import create_record_workflow
from src.workflows.hybrid_workflow import create_hybrid_workflow

# Create workflows
ai_workflow = create_ai_workflow()
record_workflow = create_record_workflow()
hybrid_workflow = create_hybrid_workflow()

# Generate Mermaid diagrams
print("AI Workflow:")
print(ai_workflow.get_graph().draw_mermaid())

print("\nRecord Workflow:")
print(record_workflow.get_graph().draw_mermaid())

print("\nHybrid Workflow:")
print(hybrid_workflow.get_graph().draw_mermaid())
