'''
要根据不同的头文件版本适配解析类，可以使用策略模式（Strategy Pattern）来实现。这种模式允许你定义一系列算法或策略，并在运行时选择适当的策略来执行。对于解析不同版本的头文件，可以为每个版本定义一个解析策略，并在运行时根据头文件版本选择相应的解析策略。
1. **定义解析策略接口**：使用抽象基类定义一个解析策略接口，所有具体的解析策略都将实现这个接口。
2. **定义具体的解析策略**：为每个头文件版本定义一个具体的解析策略类，实现解析策略接口。
3. **定义解析器上下文**：定义一个解析器上下文类，根据头文件版本选择适当的解析策略。
4. **使用解析器上下文**：在主解析类中使用解析器上下文，根据头文件版本选择适当的解析策略。

通过这种方式，可以根据不同的头文件版本适配解析类，使代码更加灵活和可维护。
'''

# 参考头文件属性
version_dict = {
    "Invalid": "Version not valid",
    "ASD": "Version 1",
    "as2": "Version 2",
    "as7": "Version 7"
}


from abc import ABC, abstractmethod
import struct

class HeaderParserStrategy(ABC):
    @abstractmethod
    def parse(self, asd: bytes, offset: int) -> tuple:
        pass

class Version1Parser(HeaderParserStrategy):
    def parse(self, asd: bytes, offset: int) -> tuple:
        # 解析版本1的头文件
        header_format = '<3s 157s 18s b b b b l b l f f b b b b b H 128s 56s L h h H H f f f f h b 4b H H H b L H H H H f f f 5b'
        header = struct.unpack_from(header_format, asd, offset)
        return header, offset + struct.calcsize(header_format)

class Version2Parser(HeaderParserStrategy):
    def parse(self, asd: bytes, offset: int) -> tuple:
        # 解析版本2的头文件
        header_format = '<3s 157s 18s b b b b l b l f f b b b b b H 128s 56s L h h H H f f f f h b 4b H H H b L H H H H f f f 5b'
        header = struct.unpack_from(header_format, asd, offset)
        return header, offset + struct.calcsize(header_format)

class Version7Parser(HeaderParserStrategy):
    def parse(self, asd: bytes, offset: int) -> tuple:
        # 解析版本7的头文件
        header_format = '<3s 157s 18s b b b b l b l f f b b b b b H 128s 56s L h h H H f f f f h b 4b H H H b L H H H H f f f 5b'
        header = struct.unpack_from(header_format, asd, offset)
        return header, offset + struct.calcsize(header_format)
    
class HeaderParserContext:
    def __init__(self, version: str):
        self.version = version
        self.parser = self._get_parser(version)

    def _get_parser(self, version: str) -> HeaderParserStrategy:
        if version == 'Version 1':
            return Version1Parser()
        elif version == 'Version 2':
            return Version2Parser()
        elif version == 'Version 7':
            return Version7Parser()
        else:
            raise ValueError(f"Unsupported version: {version}")

    def parse(self, asd: bytes, offset: int) -> tuple:
        return self.parser.parse(asd, offset)
    
    @staticmethod
    def get_parser(version_prefix):
        if os.path.exists(file) and os.path.isfile(file):
            try:
                # 将文件读入内存（缓冲区）
                # read in file to memory(buffer)
                with open(file, 'rb') as fileHandle:
                    self.asd = fileHandle.read()
            except:
                print("文件读取错误")
                return
        
        version_prefix = struct.unpack('<3s', asd)

        if version_prefix == b'as7':  # 版本1的前缀
            print()
            return Version7Parser()
        elif version_prefix == b'as2':  # 版本2的前缀
            print("ASD File Version: "version_dic[version_prefix])

            return Version2Parser()
        elif version_prefix == b'\x03\x00\x00':  # 版本3的前缀
            return Version3Parser()
        else:
            raise ValueError(f"不支持的文件版本前缀: {version_prefix}")
    

class ASDFileHandle:
    def __init__(self, version: str):
        self.parser_context = HeaderParserContext(version)

    def parse_header(self, asd: bytes, offset: int) -> tuple:
        return self.parser_context.parse(asd, offset)

# 示例用法
asd_file_handle = ASDFileHandle('Version 1')00
header, new_offset = asd_file_handle.parse_header(asd_data, 0)