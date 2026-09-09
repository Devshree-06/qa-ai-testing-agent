import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from src.model.ApiTestResponse import ApiTestResponseModel
from src.service.tools_service import get_api_status
from langchain_core.messages import ToolMessage

load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key = os.getenv("GROQ_API_KEY")
)

structure_llm = llm.with_structured_output(ApiTestResponseModel)

llm_with_tools = llm.bind_tools([get_api_status])

response = llm_with_tools.invoke(
    "What is an API?"
)

user_message = "Check the status of https://google.com"

print("LLM TOOL REQUEST---")
print(response)

if response.tool_calls:

    print("TOOL CALLED----")
    tool_call  = response.tool_calls[0]

    tool_result = get_api_status.invoke(tool_call["args"])

    print("\nTOOL RESULT--")
    print(tool_result)

    tool_message_to_llm = ToolMessage(
        content=tool_result,
        tool_call_id=tool_call["id"]
    )

    messages = [
        ("user",user_message),
        response,
        tool_result
    ]

    final_llm_response = llm_with_tools.invoke(messages)

    print("\nFINAL LLM RESPONSE----")
    print(final_llm_response)

else:
    print(response.content)

# result = structure_llm.invoke("""
# Analyze the given endpoint : 
# POST /users

# Create a test plan for this endpoint. Include the HTTP method,endpoint,purpose and three useful
# test cases""")


# print(result)