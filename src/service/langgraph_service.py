from langgraph.graph import StateGraph,START,END,MessagesState
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv
from src.service.tools_service import get_api_status,test_api
from langchain_core.messages import ToolMessage
from src.service.qa_api_test_tool_service import run_test_api


load_dotenv()

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key = os.getenv("GROQ_API_KEY")
)

llm_with_tools = llm.bind_tools([run_test_api])

class State(MessagesState):
    pass
    

def greet(state: State):

    print("\n===== GREET NODE =====")

    print("Number of messages:", len(state["messages"]))

    for i, message in enumerate(state["messages"]):

        print(f"\nMESSAGE {i}")
        print("TYPE:", type(message).__name__)

        if hasattr(message, "content"):
            print("CONTENT TYPE:", type(message.content).__name__)
            print("CONTENT LENGTH:", len(str(message.content)))

        if hasattr(message, "tool_calls"):
            print("TOOL CALL COUNT:", len(message.tool_calls))

        if hasattr(message, "additional_kwargs"):
            print(
                "ADDITIONAL KWARGS LENGTH:",
                len(str(message.additional_kwargs))
            )

    print("========================\n")

    response = llm_with_tools.invoke(
        state["messages"]
    )

    return {
        "messages": [response]
    }

def execute_tool_node(state: State):

    last_message = state["messages"][-1]
    tool_call = last_message.tool_calls[0]

    tool_response = run_test_api.invoke(tool_call["args"])

    tool_message = ToolMessage(
        content=tool_response,
        tool_call_id = tool_call["id"]
    )

    return {
        "messages" : [tool_message]
    }


def conditional_node(state : State):
    latest_message = state["messages"][-1]

    print("Number of messages : " , len(state["messages"]))

    if latest_message.tool_calls:
        print("LLM requested a tool call")
        return "execute_tool"
    else:
        print("LLM did not call the tool.Ending the graph")
        return END




graph = StateGraph(State)
graph.add_node("greet",greet)
graph.add_node("execute_tool",execute_tool_node)

graph.add_edge(START,"greet")
graph.add_conditional_edges(
    "greet",
    conditional_node,
    {
        "execute_tool" : "execute_tool",
        END: END
    }
)
graph.add_edge("execute_tool","greet")

app = graph.compile()

result = app.invoke({
    "messages" : [("user","Test https://httpbin.org/status/200. The expected HTTP status is 200.")]
})

print(result)