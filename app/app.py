from langchain_core.messages import HumanMessage

from agent.agent import app

response = app.invoke({
    "messages" : [
        HumanMessage(
            content="Run only the python tests in this project and analyze any failures and suggest and apply fix."
        )
    ],
    "project_path" : "workspace"
})

for message in response["messages"]:
    print("\n============")
    print(type(message))
    print(message)