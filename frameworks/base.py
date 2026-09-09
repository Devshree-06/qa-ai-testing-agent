from abc import ABC, abstractmethod
#This defines the base of testing frameworkds and what methods are required of them

class TestFramework(ABC):

     @abstractmethod
     def discover_tests(self,project_path:str) -> list[str]:
          pass

     @abstractmethod
     def run_test(self,project_path:str,test_path:str) ->dict:
          pass
     
     @abstractmethod
     def read_test_file(self,project_path:str,test_path:str) -> str:
          pass