from frameworks.pytest_adapter import PytestAdapter
from frameworks.jest_adapter import JestAdapter

class FactoryFramework:

    def getAdapter(framework:str):
        if framework == "pytest":
            return PytestAdapter()

        if framework == "jest":
            return JestAdapter()

        raise ValueError(f"Unsupported framework : {framework}")