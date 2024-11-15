import hashlib
import os
import logging
import json
import re
import numpy as np
import sys

# 将父目录添加到sys.path中
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fileIO.SpectInstrulment.ASD.asdFileHandle_1 import *

def list_fullpath_of_all_files_with_ext(directory, ext):
    file_paths = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(ext):
                file_paths.append(os.path.join(root, file))
    return file_paths

def file_hash(filepath):
    hash_func = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(2):
            hash_func.update(chunk)
    return hash_func.hexdigest()

def files_are_identical(file1, file2):
    return file_hash(file1) == file_hash(file2)

def files_are_identical_bytes(file1, file2):
    with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
        offset = 0
        while True:
            b1 = f1.read(2)
            b2 = f2.read(2)
            if b1 != b2:
                # 找到不一致的位置
                for i in range(min(len(b1), len(b2))):
                    if b1[i] != b2[i]:
                        logger.info(f"文件在偏移量 {offset + i} 处不一致")
                        return False
                # 如果一个文件比另一个文件短
                if len(b1) != len(b2):
                    logger.info(f"文件在偏移量 {offset + min(len(b1), len(b2))} 处不一致")
                    return False
            if not b1:  # End of file
                return True
            offset += len(b1)

def compare_asd_files(file1, file2):
    attributes1 = vars(file1)
    attributes2 = vars(file2)
    
    for attr in attributes1:
        if attr not in attributes2:
            logger.info(f"Attribute {attr} is missing in the second file")
            return False
        if attributes1[attr] != attributes2[attr]:
            logger.info(f"Attribute {attr} differs between the two files")
            return False
    
    for attr in attributes2:
        if attr not in attributes1:
            logger.info(f"Attribute {attr} is missing in the first file")
            return False
    
    logger.info("All attributes are identical between the two files")
    return True

def compare_json_files(file1_path, file2_path):
    try:
        with open(file1_path, 'r', encoding='utf-8') as file1, open(file2_path, 'r', encoding='utf-8') as file2:
            json1 = json.load(file1)
            json2 = json.load(file2)
            
            if json1 == json2:
                logger.info(f"{file1_path} 和 {file2_path} 两个 JSON 文件完全一致")
                return True
            else:
                logger.info(f"{file1_path} 和 {file2_path} 两个 JSON 文件不一致")
                return False
    except Exception as e:
        logger.error(f"比较 JSON 文件时出错: {e}")
        return False
    
def show_info(asdfile):
    if asdfile.metadata is not None:
        logger.info(f"元数据: \n{asdfile.metadata}")
    if asdfile.classifierData is not None:
        logger.info(f"分类数据数据: \n{asdfile.classifierData}")
    if asdfile.dependants is not None:
        logger.info(f"依赖变量: \n{asdfile.dependants}")
    if asdfile.calibrationHeader is not None:
        logger.info(f"校准文件头: \n{asdfile.calibrationHeader}")
        logger.info(f"校准头数量: \n{asdfile.calibrationHeader.calibrationNum}")
        logger.info(f"校准文件头: \n{asdfile.calibrationHeader.calibrationSeries}")
        if asdfile.calibrationHeader.calibrationSeries is not None:
            for i in range(len(asdfile.calibrationHeader.calibrationSeries)):
                logger.info(f"校准文件头: \n{asdfile.calibrationHeader.calibrationSeries[i]}")
        if asdfile.calibrationSeriesABS is not None:
            logger.info(f"校准文件头: \n{asdfile.calibrationSeriesABS}")
            logger.info(f"校准文件头ABS：\n{len(np.array(asdfile.calibrationSeriesABS))}")
    if asdfile.auditLog is not None:
        logger.info(f"审计文件头: \n{asdfile.auditLog}")
        logger.info(f"审计数量: \n{asdfile.auditLog.auditCount}")
        logger.info(f"审计内容: \n{asdfile.auditLog.auditEvents}")
    if asdfile.signature is not None:
        logger.info(f"签名: \n{asdfile.signature}")
    return True

def batch_read_and_write(filePath):
    for file in list_fullpath_of_all_files_with_ext(filePath, ".asd"):
        try:
            # 读取ASD原始数据
            # logger.info(f"{10*'-'}读取文件{file}{10*'-'}\n")
            with open(file, 'rb') as f:
                asdFileStream = f.read()
                len1 =len(asdFileStream)
                # logger.info(f"读取的文件长度{len1}")

            asdFile1 = asdfh.ASDFile()
            asdFile1.read(file)

            # 存储为新文件
            directory, filename = os.path.split(file)
            name, ext = os.path.splitext(filename)
            outputfile = f"SpectInstrulment\\asd_Spect\\__testData__\\Example_write\\{name}_write{ext}"
            asdFile1.write(outputfile)

        except Exception as e:
            logger.error(f"处理 {file} 时出错:\n{e}", exc_info=True)
            continue

        try:
            # logger.info(f"{10*'-'}读取文件{outputfile}{10*'-'}\n")
            with open(outputfile, 'rb') as f:
                asdFileStream = f.read()
                len2 = len(asdFileStream)
                # logger.info(f"写入的新文件长度{len2}")

            asdFile2 = asdfh.ASDFile()
            asdFile2.read(outputfile)
        except Exception as e:
            logger.error(f"处理 {outputfile} 时出错:\n{e}", exc_info=True)
            continue

        # 比较两个文件
        if len1 != len2:
            logger.info(f"{file}和{outputfile}两个文件长度不一致")
            logger.info(f"{file}长度为{len1}")
            logger.info(f"{outputfile}长度为{len2}")

        if not files_are_identical(file, outputfile):
            logger.info(f"{file}和{outputfile}两个文件哈希校验不一致")
            if not files_are_identical_bytes(file, outputfile):
                logger.info(f"{file}和{outputfile}两个文件逐字节校验不一致")
        logger.info(f"{5*'_'}{file}{5*'_'}")
        show_info(asdFile1)
        logger.info(f"{5*'_'}{outputfile}{5*'_'}")
        show_info(asdFile2)
    return True


# 配置日志记录
logging.basicConfig(
    filename = r'D:\MacBook\MacBookDocument\VSCode\SourceCode\RemoteSensing\SpectInstrulment\asd_Spect\__testData__\asd_file_analysis.log',  # 日志文件名
    level=logging.DEBUG,  # 日志级别
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - Line: %(lineno)d'  # 日志格式
    )

logger = logging.getLogger(__name__)



