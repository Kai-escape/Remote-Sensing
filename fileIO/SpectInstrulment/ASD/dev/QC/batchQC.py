from hashlib import md5
from re import A
import sys
import os
import logging
import datetime


# # 将父目录添加到sys.path中
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fileIO.SpectInstrulment.ASD.asdFileHandle_1 import *
from fileIO.SpectInstrulment.ASD.__tests__.testing_batchReadAndWrite import *
# from testing_batchReadAndWrite import *

def setup_logging(log_file):

    # 生成日志文件名，包含日期
    current_date = datetime.datetime.now().strftime('%Y%m%d')
    log_file = os.path.join(os.path.dirname(log_file), os.path.basename(log_file).replace('.log', f'_asd_qc_{current_date}.log'))
    # 配置日志格式和级别
    logging.basicConfig(
        # 日志级别
        level=logging.INFO,
        # 日志格式
        format='%(asctime)s - %(levelname)s - %(message)s',
        # format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - Line: %(lineno)d'  # 日志格式
        # format='%(message)s'  # 日志格式        
        handlers=[
            logging.StreamHandler(),  # 输出到控制台
            logging.FileHandler('asd_qc.log', encoding='utf-8')  # 输出到文件
        ]
    )
# # 配置日志记录
# logging.basicConfig(
#     filename = r'D:\MacBook\MacBookDocument\VSCode\SourceCode\RemoteSensing\fileIO\SpectInstrulment\ASD\__tests__\QC\QC_Result.log',  # 日志文件名
#     level=logging.DEBUG,  # 日志级别
#     # format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - Line: %(lineno)d'  # 日志格式
#     format='%(message)s'  # 日志格式
# )
# logger = logging.getLogger(__name__)

# -------------------设置-------------------
# 要检查的文件夹，包含多个asd文件，读取文件夹及子文件夹下所有asd文件
filePath =r"D:\实测光谱\FieldSpecData_20241021_1103"
# 设置采集时间和参考时间间隔(分钟)，超过这个时间间隔的文件会被记录：建议室内设置为30分钟，室外设置为10分钟
timeInterval_minute = 10
# 设置日志文件
logFile = r'D:\MacBook\MacBookDocument\VSCode\SourceCode\RemoteSensing\fileIO\SpectInstrulment\ASD\__tests__\QC\QC_Result.log'
# 可以指定自定义的日志目录
# -------------------设置结束-------------------




setup_logging(logFile)  # 或者使用其他路径

flag1_vnir_saturation = 1   # Vnir Saturation    0 0 0 0  0 0 0 1   0x01
flag1_swir1_saturation = 2  # Swir1 Saturation   0 0 0 0  0 0 1 0   0x02
flag1_swir2_saturation = 4  # Swir2 Saturation   0 0 0 0  0 1 0 0   0x04
Tec1_alarm = 8  # Swir1 Tec Alarm    0 0 0 0  1 0 0 0   0x08
Tec2_alarm = 16 # Swir2 Tec Alarm    0 0 0 1  0 0 0 0   0x16

class QCresult(ASDFile):
    def __init__(self, file):
        super().__init__()
        self.file = file
        self.filename = os.path.basename(file)
        self.filedictory = os.path.dirname(file)
        self._saturationError = None
        self._md5value = None
        self.qcFlag = False
    # def post_init(self):
    #     self.filename = os.path.basename(self.file)
    #     self.filedictory = os.path.dirname(self.file)
    #     self.hash()
   
    def hash(self):
        hash_func = hashlib.sha256()
        with open(self.file, 'rb') as f:
            while chunk := f.read(2):
                hash_func.update(chunk)
        self._md5value = hash_func.hexdigest()
        return self._md5value
    
    def __getattr__(self, attr):
        if attr == "md5":
            if self._md5value is None:
                self.hash()
                # print(self._md5value)
                return self._md5value
        if attr == "error":
            if self._saturationError is None:
                self._saturationError = self.check_error_type()
                return self._saturationError
        else:
            return None

    def check_error_type(self):
        errors = []
        if self.metadata.flags2 & flag1_vnir_saturation:
            errors.append("VNIR饱和")
        if self.metadata.flags2 & flag1_swir1_saturation:
            errors.append("SWIR1饱和")
        if self.metadata.flags2 & flag1_swir2_saturation:
            errors.append("SWIR2饱和")
        if self.metadata.flags2 & Tec1_alarm:
            errors.append("TEC1 Alarm")
        if self.metadata.flags2 & Tec2_alarm:
            errors.append("TEC2 Alarm")
        return errors




qc_dict = {}
md5_set = set()
duplicate_md5_files = []
for file in list_fullpath_of_all_files_with_ext(filePath, ".asd"):
    asdfile = QCresult(file)
    asdfile.read(file)

    # print(f"文件{asdfile.filename}读取完成，开始进行QC检查")


    if asdfile.filename not in qc_dict:

        qc_dict[asdfile.filename] = []

        # 初始化各个校验项的标志
        darkCorrectedFlag = True
        dataTypeFlag = True
        channel1WavelengthFlag = True
        wavelengthStepFlag = True
        dataFormatFlag = True
        channelsFlag = True
        darkCurrentCountFlag = True
        refCountFlag = True
        sampleCountFlag = True
        instrumentFlag = True

        # 检查文件的属性，是否符合要求
        failed_attrItems = ''
        # 进行了暗电流校准，1为Ture
        if asdfile.metadata.darkCorrected != 1:
            darkCorrectedFlag = False
            failed_attrItems += f"暗电流校准：{asdfile.metadata.darkCorrected}\n"
        # 数据类型，0为Raw原始数据
        if asdfile.metadata.dataType != 1:
            dataTypeFlag = False
            failed_attrItems += f"数据类型：{asdfile.metadata.dataType}\n"
        # 光谱长度
        if asdfile.metadata.channel1Wavelength != 350.0:
            channel1WavelengthFlag = False
            failed_attrItems += f"光谱长度：{asdfile.metadata.channel1Wavelength}\n"
        # 光谱步长
        if asdfile.metadata.wavelengthStep != 1.0:
            wavelengthStepFlag = False
            failed_attrItems += f"光谱步长：{asdfile.metadata.wavelengthStep}\n"
        # 采集存储的数据类型，2为双精度
        if asdfile.metadata.dataFormat != 2:
            dataFormatFlag = False
            failed_attrItems += f"数据格式：{asdfile.metadata.dataFormat}\n"
        # 通道数
        if asdfile.metadata.channels != 2151:
            channelsFlag = False
            failed_attrItems += f"通道数：{asdfile.metadata.channels}\n"
        # # 暗电流校准？
        # asdfile.metadata.darkCurrentCorrention == 1
        # # 校准数据？不明
        # asdfile.metadata.calibration
        # 暗电流校准次数，100次
        if asdfile.metadata.darkCurrentCount != 100:
            darkCurrentCountFlag = False
            failed_attrItems += f"暗电流校准次数：{asdfile.metadata.darkCurrentCount}\n"
        # 白板校准次数，25次
        if asdfile.metadata.refCount != 25:
            refCountFlag = False
            failed_attrItems += f"白板校准次数：{asdfile.metadata.refCount}\n"
        # 光谱采集次数，10次
        if asdfile.metadata.sampleCount != 10:
            sampleCountFlag = False
            failed_attrItems += f"光谱采集次数：{asdfile.metadata.sampleCount}\n"
        # 仪器类型，4为FSNIR
        if asdfile.metadata.instrument != 4:
            instrumentFlag = False
            failed_attrItems += f"仪器类型：{asdfile.metadata.instrument}\n"
        # 如果任何一个校验项为 False，则总体校验标志设置为 False
        if not (darkCorrectedFlag and dataTypeFlag and channel1WavelengthFlag and wavelengthStepFlag and dataFormatFlag and channelsFlag and darkCurrentCountFlag and refCountFlag and sampleCountFlag and instrumentFlag):
            asdfile.qcFlag = False
            # print(f"文件{asdfile.filename}属性校验失败：{failed_attrItems}")
            qc_dict[asdfile.filename].append("文件属性校验失败：" + failed_attrItems)
        else:
            qc_dict[asdfile.filename].append("文件属性校验通过")

        qc_dict[asdfile.filename].append(asdfile.md5)
        # print(asdfile.md5)
        qc_dict[asdfile.filename].append(asdfile.error)
        timediff = asdfile.metadata.when - asdfile.metadata.referenceTime
        if timediff.total_seconds() > timeInterval_minute * 60:
            qc_dict[asdfile.filename].append(f"采集时间和白参考时间差值大于{timeInterval_minute}分钟")
        else:
            qc_dict[asdfile.filename].append("采集时间和白参考时间差值校验通过")

        qc_dict[asdfile.filename].append("文件名字唯一")
        asdfile.qcFlag = True
        qc_dict[asdfile.filename].append(asdfile.qcFlag)

    else:
        asdfile.qcFlag = False
        qc_dict[asdfile.filename].append("文件名字重复")
    
    # 检查文件的MD5值是否重复
    if asdfile.md5 not in md5_set:
        md5_set.add(asdfile.md5)
    else:
        duplicate_md5_files.append(asdfile.filename)

if duplicate_md5_files:
    logger.info("以下文件MD5值重复：")
    for file in duplicate_md5_files:
        logger.info(file)

# 遍历字典键值，如果值列表中有False，则将该键值存至新字典qc_failed_dict中
qc_failed_dict = {key: value for key, value in qc_dict.items() if False in value}

for key in qc_failed_dict:
    logger.info(f"{key}: {qc_failed_dict[key]}")
# print(qc_dict)

# if qc_failed_dict:
#     # print(f"QC检查不合格的文件\n{qc_failed_dict}")
# else:
#     print("QC检查通过，所有文件合格")
#     for key in qc_dict:
#         print(f"{key}: {qc_dict[key]}")
#     # print(qc_dict)

# for key in qc_dict:
#     print(f"{key}: {qc_dict[key]}")
# print(qc_dict)
for key in qc_dict:
    logger.info(f"{key}: {qc_dict[key]}")