from langchain_core.messages import HumanMessage

from agent.agent import app

response = app.invoke({
    "messages" : [
        HumanMessage(
            content="Run the tests in this project and analyze any failures and suggest and apply fix."
        )
    ],
    "project_path" : "workspace/jest-demo-project"
})

for message in response["messages"]:
    print("\n============")
    print(type(message))
    print(message)