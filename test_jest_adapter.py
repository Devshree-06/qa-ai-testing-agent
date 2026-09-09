from frameworks.jest_adapter import JestAdapter

adapter = JestAdapter()

project_path = "workspace/jest-demo-project"

test_path = "tests/login.test.js"

# result = adapter.run_test(project_path,test_path)

result_new = adapter.read_test_file(project_path,test_path)

# tests = adapter.discover_tests(project_path)

print("Read file output: ")
print(result_new)