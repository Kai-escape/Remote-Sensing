from abc import ABC, abstractmethod

class FileHandler(ABC):

    def __init__(self, filePath):

        self.filePath = filePath
    
    @abstractmethod
    def read(self):
        pass
    
    @abstractmethod
    def write(self, content):
        pass

    @abstractmethod
    def update(self, content):
        pass
