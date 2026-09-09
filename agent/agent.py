from langchain_groq import ChatGroq

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

import os
from dotenv import load_dotenv

from langchain_core.messages import SystemMessage


from agent.state import AgentState
from agent.tools import (
    discover_framework,
    discover_tests,
    read_test_file,
    run_test,
    apply_patch
)

load_dotenv()


llm = ChatGroq(
    model="qwen/qwen3.6-27b",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
    max_tokens=1000
)


tools = [
    discover_framework,
    run_test,
    discover_tests,
    read_test_file,
    apply_patch
]

llm_with_tools = llm.bind_tools(tools)


def agent_node(state: AgentState):

    print("\n===== STATE =====")
    print(state)

    print("\n===== MESSAGES =====")
    for message in state["messages"]:
        print(type(message))
        print(message)

    response = llm_with_tools.invoke(
        [
             SystemMessage(
                 content= f"""
You are an AI Testing Agent. 

Project Path : {state["project_path"]}

You must complete the testing workflow.

Workflow:
1. Call discover_framework to determine the framework.
2. After receiving the framework, immediately call discover_tests
using the detected framework and project path.
3. Run the discovered tests using run_test
4. If the test fails,use read_test_file to inspect the tests.
5. Analyze the failures.
6. If you identify a safe fix, call apply_patch
7. After apply_patch succeeds, call run test again.
8. Only finish after the test passes or no safe fix can be identified.

Important:
- Do not stop after discover_framework.
- Do not stop after discover_tests.
- Do not stop after run_tests if there is a failure.
- Use tools directly instead of explaining what plan to do.
- When calling apply_patch, use exactly:
        project_path,
        file_path,
        old_text,
        new_text
- Never use new_fix as a parameter.
- old_text must exactly match text in the file.
- Do not modify files outside the project directory.
- Do not modify protected files.
- Maximum 3 repair attempts.

"""
             ),
             *state["messages"]
        ]
      
    )

    return {
        "messages": [response]
    }


def should_agent_continue(state: AgentState):

    last_message = state["messages"][-1]

    if last_message.tool_calls:
        return "tools"

    return END


graph = StateGraph(AgentState)

graph.add_node("agent", agent_node)

graph.add_node(
    "tools",
    ToolNode(tools)
)

graph.add_edge(START, "agent")

graph.add_conditional_edges(
    "agent",
    should_agent_continue,
    {
        "tools": "tools",
        END: END
    }
)

graph.add_edge("tools", "agent")


app = graph.compile()