from abc import ABC, abstractmethod

class File(ABC):

    def __init__(self, filePath):

        self.filePath = filePath
    
    @abstractmethod
    def read(self):
        pass
    
    @abstractmethod
    def write(self, content):
        pass
