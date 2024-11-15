# !/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   asdFileHandle.py
@Time    :   2024/11/15 04:09:34
@Author  :   Kai Cao 
@Version :   2.0
@Contact :   caokai_cgs@163.com
@License :   (C)Copyright 2023-2024
Copyright Statement:   Full Copyright
@Desc    :   According to "ASD File Format version 8: Revision B"
'''

from ast import parse
from calendar import weekday
import os
import struct
import datetime
import re
import logging
from tkinter import N
from anyio import value
from attr import dataclass, field
import numpy as np
import xml.etree.ElementTree as ET
from collections import namedtuple
from dataclasses import dataclass
from enum import Enum

# ASD File constants
# metadata.fileVersion: ASD File Version, at byte offset 0
class FileVersion(Enum):
    INVALID = 0
    ASD = 1
    as2 = 2
    as3 = 3
    as4 = 4
    as5 = 5
    as6 = 6
    as7 = 7
    as8 = 8

 # metadata.instrument: Instrument type that created spectrum, at byte offset 431
class InstrumentType(Enum):
    UNKNOWN_INSTRUMENT = 0
    PSII_INSTRUMENT = 1
    LSVNIR_INSTRUMENT = 2
    FSVNIR_INSTRUMENT = 3
    FSFR_INSTRUMENT = 4
    FSNIR_INSTRUMENT = 5
    CHEM_INSTRUMENT = 6
    LAB_SPEC_PRO = 7
    HAND_HELD_INSTRUMENT = 10

class InstrumentModel(Enum):
    itVnir = 1
    # itDual
    itSwir1 = 4
    itVnirSwir1 = 5
    itSwir2 = 8
    itVnirSwir2 = 9
    itSwir1Swir2 = 12
    itVnirSwir1Swir2 = 13

# metadata.dataType: Spectrum type, at byte offset 186
class SpectraType(Enum):
    RAW = 0
    REFLECTANCE = 1
    RADIANCE = 2
    NO_UNITS = 3
    IRRADIANCE = 4
    QUALITY_INDEX = 5

class SignatureState(Enum):
    NOT_SIGNED = 0
    # SIGNED = 1
    # VERIFIED = 2
    # NOT_VERIFIED = 3

class AuditLogType(Enum):
    AUDIT_EVENT_ELEMENT = "Audit_Event"
    AUDIT_APPLICATION_ELEMENT = "Audit_Application"
    AUDIT_APP_VERSION_ELEMENT = "Audit_AppVersion"
    AUDIT_FUNCTION_ELEMENT = "Audit_Function"
    AUDIT_SOURCE_ELEMENT = "Audit_Source"
    AUDIT_LOGIN_ELEMENT = "Audit_Login"
    AUDIT_NAME_ELEMENT = "Audit_Name"
    AUDIT_TIME_ELEMENT = "Audit_Time"
    AUDIT_NOTES_ELEMENT = "Audit_Notes"

class IT_ms(Enum):
    ms_8_5 = 9
    ms_17 = 17
    ms_34 = 34
    ms_68 = 68
    ms_136 = 136
    ms_272 = 272
    ms_544 = 544
    ms_1088 = 1088
    ms_2176 = 2176
    ms_4352 = 4352
    ms_8704 = 8704
    ms_17408 = 17408
    ms_34816 = 34816
    ms_69632 = 69632
    ms_139264 = 139264
    ms_278528 = 278528
    ms_557056 = 557056

# metadata.dataFormat: Spectrum data format, at byte offset 199
class DataType(Enum):
    FLOAT = 0
    INTEGER = 1
    DOUBLE = 2
    UNKNOWN = 3

# metadata.calibrationSeries: Calibration type, at byte offset 432
class Calibration(Enum):
    ABSOLUTE = 0
    BASE = 1
    LAMP = 2
    FIBER = 3

class DataType_e(Enum):
    dtRAW_TYPE = 0
    # dtREF_TYPE
    # dtRAD_TYPE
    # dtNOUNITS_TYPE
    # dtIRRAD_TYPE
    # dtQI_TYPE
    # dtTRANS_TYPE
    # dtUNKNOWN_TYPE
    # dtABS_TYPE
    # dtADF_TYPE
    # dtADC_TYPE
    # dtMTF_TYPE
    # dtMTC_TYPE
    # dtRTF_TYPE
    # dtRTC_TYPE
    # dtSBF_TYPE
    # dtSBC_TYPE

class Data_Format_e(Enum):
    dfFLOAT_FORMAT = 0
    # dfINTEGER_FORMAT
    # dfDOUBLE_FORMAT
    # dfUNKNOWN_FORMAT

# Classifier Data Type
class ClassiferDataType(Enum):
    SAM = 0
    GALACTIC = 1
    CAMOPREDICT = 2
    CAMOCLASSIFY = 3
    PCAZ = 4
    INFOMETRIX = 5

# Calibration Series
class ColibrationType(Enum):
    ABSOLUTE = 0            # ABS, Absolute Reflectance File;
    BASE = 1                # BSE, Base File
    LAMP = 2                # LMP, Lamp File
    FIBER = 3               # FO, Fiber Optic File

# Error types for flags2 in the metadata
class SauturationError(Enum):
    VNIR_SATURATION = 1         # Vnir Saturation    0 0 0 0  0 0 0 1   0x01
    SWIR1_SATURATION = 2        # Swir1 Saturation   0 0 0 0  0 0 1 0   0x02
    SWIR2_SATURATION = 4        # Swir2 Saturation   0 0 0 0  0 1 0 0   0x04
    SWIR1_TEC_ALARM = 8         # Swir1 Tec Alarm    0 0 0 0  1 0 0 0   0x08
    SWIR2_TEC_ALARM = 16        # Swir2 Tec Alarm    0 0 0 1  0 0 0 0   0x16

@dataclass
class When:
    tmSecond: int = field(default=None, metadata={'unit': 'second',}, validator= lambda v: 0 <= v <= 61)    # seconds [0,61]
    tmMinute: int = field(default=None, metadata={'unit': 'minute'}, validator= lambda v: 0 <= v <= 59)     # minutes [0,59]
    tmHour: int = field(default=None, metadata={'unit': 'hour'}, validator= lambda v: 0 <= v <= 23)         # hours [0,23]
    tmMday: int = field(default=None, metadata={'unit': 'day'}, validator= lambda v: 1 <= v <= 31)          # day of the month [1,31]
    tmMonth: int = field(default=None, metadata={'unit': 'month'}, validator= lambda v: 0 <= v <= 12)       # month of year [0,11]
    tmYear: int = field(default=None, metadata={'unit': 'year'}, validator= lambda v: 0 <= v <= 9999)       # years since 1900
    tmWeekday: int = field(default=None, metadata={'unit': 'weekday'}, validator= lambda v: 0 <= v <= 6)    #(Sunday = 0)
    tmDayInYear: int  = field(default=None, metadata={'unit': 'daysInYear'}, validator= lambda v: 0 <= v <= 365)    # day of year [0,365]
    tmDaylighSavingsFlag: int = field(default=None, metadata={'unit': 'daylighSavingsFlag'}, validator= lambda v: [0, 1])  # daylight savings flag
    tmDateTime: datetime.datetime = field(default=None, metadata={'unit': 'datetime'}, validator= lambda v: isinstance(v, datetime.datetime))
    byteStream: bytes = field(default=None, metadata={'unit': '18 bytes'}, validator= lambda v: len(v) == 18)
    bytelength: 18 = field(default=18)

    def __post_init__(cls, byteStream):
        if byteStream:
            parse(byteStream)
            byteStream
            byteLength = len(byteStream)

    def parse(self, byteStream):
        tmSecond = byteStream[0]               
        tmMinute = byteStream[1]               
        tmHour = byteStream[2]                  # hour [0,23]
        tmMday = byteStream[3]                   # day of the month [1,31]
        tmMonth = byteStream[4]                 # month of year [0,11]
        tmYear = byteStream[5]                  # years since 1900
        tmWeekday = byteStream[6]               # day of week [0,6] (Sunday = 0)
        tmDayInYear = byteStream[7]            # day of year [0,365]
        tmDaylighSavingsFlag = byteStream[8]    # daylight savings flag
        if year < 1900:
            year = year + 1900
        tmDateTime = datetime.datetime(year, month + 1, day, hour, minutes, seconds)
        return self

    def int_to_dateTime(self) -> datetime.datetime:
        if self.tmYear < 1900:
            tmYear_AD = self.tmYear + 1900
        else:
            tmYear_AD = self.tmYear
        self.tmDateTime = datetime.datetime(tmYear_AD, self.tmMonth +1, self.tmMday, self.tmHour, self.tmMinute, self.tmSecond)
        return self

    def tmDateTime_to_int(self) -> int:
        if self.tmDateTime:
            self.tmSecond = self.tmDateTime.second
            self.tmMinute = self.tmDateTime.minute
            self.tmHour = self.tmDateTime.hour
            self.tmMday = self.tmDateTime.day
            self.tmMonth = self.tmDateTime.month - 1
            if self.tmDateTime.year >= 1900:
                self.tmYear = self.tmDateTime.year - 1900
            else:
                self.tmYear = self.tmDateTime.year
            self.tmWeekday = (self.tmDateTime.weekday() + 1) % 7
            self.tmDayInYear = (self.tmDateTime() - datetime.datetime(self.tmDateTime.year, 1, 1)).days
        return self
    
    def parse(self) -> int:
        try:
            if len(self.byteStream) == 18:
                self.tmSecond, self.tmMinute, self.tmHour, self.tmMday, self.tmMonth, Year, self.tmWeekday, self.tmDayInYear, self.tmDaylighSavingsFlag = struct.unpack('9h', self.byteStream)
                if Year < 1900:
                    self.tmYear = Year + 1900
                else:
                    self.tmYear = Year
                self.tmDateTime = datetime.datetime(self.tmYear, self.tmMonth + 1, self.tmMday, self.tmHour, self.tmMinute, self.tmSecond)
                return self
        except Exception as e:
            logger.exception(f"Error in converting byteStream to int.\nError: {e}")
    def wrap(self) -> bytes:
        try:
            self.byteStream = struct.pack('9h', self.tmSecond, self.tmMinute, self.tmHour, self.tmMday, self.tmMonth, self.tmYear, self.tmWeekday, self.tmDayInYear, self.tmDaylighSavingsFlag)
            return self
        except Exception as e:
            logger.exception(f"Error in converting int to byteStream.\nError: {e}")

@dataclass
class GPSdata():
    gpsTrueHeading: float = field(default=None, metadata={'unit': 'degree'}, validator= lambda v: 0 <= v <= 360)
    gpsSpeed: float = field(default=None, metadata={'unit': '?? m/s ??'})   # unit is not defined in the document
    gpsLatitude: float = field(default=None, metadata={'unit': 'degree'})
    gpsLongitude: float = field(default=None, metadata={'unit': 'degree'}, validator= lambda v: -180 <= v <= 180)
    gpsAltitude: float = field(default=None, metadata={'unit': 'meters'})
    gpsNumSatellites: int = field(default=None)
    gpsHardwareMode: int = field(default=None)
    gpsTime_ss: int = field(default=None, metadata={'unit': 'second'})
    gpsDate_mm: int = field(default=None, metadata={'unit': 'minute'})
    gpsDate_hh: int = field(default=None, metadata={'unit': 'hour'})
    gpsFlag1: int = field(default=None)
    gpsFlag2: int = field(default=None)
    gpsSatellites: bytes = field(default=None, metadata={'unit': 'list of satellites'}, validator= lambda v: len(v) == 5)
    gpsFiller1: int = field(default=None)
    gpsFiller2: int = field(default=None)
    byteStream: bytes = field(default=None, metadata={'unit': '57 bytes'}, validator= lambda v: len(v) == 57)
    byteLength: int = field(default=57, metadata={'unit': 'bytes'}, validator= lambda v: v == 57)
    def __post_init__(cls, byteStream):
        if byteStream:
            parse(byteStream)
        return self
    def parse(self) -> bytes:
        try:
            byteStream = struct.pack('<d d d d d h b b b b b h 5s b b', self.gpsTrueHeading, self.gpsSpeed, self.gpsLatitude, self.gpsLongitude, self.gpsAltitude, self.gpsNumSatellites, self.gpsHardwareMode, self.gpsTime_ss, self.gpsDate_mm, self.gpsDate_hh, self.gpsFlag1, self.gpsFlag2, self.gpsSatellites, self.gpsFiller1, self.gpsFiller2)
            return byteStream
        except Exception as e:
            logger.exception(f"Error in converting data to bytes.\nError: {e}")
        return self
    def wrap(self) -> object:
        try:
            if len(self.byteStream) == 57:
                self.gpsTrueHeading, self.gpsSpeed, self.gpsLatitude, self.gpsLongitude, self.gpsAltitude, self.gpsLock, self.gpsNumSatellites, self.gpsHardwareMode, self.gpsTime_ss, self.gpsDate_mm, self.gpsDate_hh, self.gpsFlag1, self.gpsFlag2, self.gpsSatellites, self.gpsFiller = struct.unpack('<d d d d d h b b b b b h 5s b b', self.byteStream)
                return self
        except Exception as e:
            logger.exception(f"Error in converting bytes to data.\nError: {e}")
        return None




@dataclass
class ASDFileMetadata():
    fileVersion: bytes = field(default=b'\x00', metadata={'unit': '3 bytes', 'value': 'ASD File Version'}, validator= lambda v: len(v) == 3)
    comments: str = field(default='', metadata={'unit': '157 bytes', 'value': 'Comments'}, validator= lambda v: len(v) <= 157)
    when: When = field(default=When(), metadata={'unit': '9 bytes', 'value': 'When'}, validator= lambda v: isinstance(v, When))
    programVersion: int = field(default=0, metadata={'unit': 'byte', 'value': 'Program Version'}, validator= lambda v: 0 <= v <= 255)
    fileVersion: int= field(default=0, metadata={'unit': 'byte', 'value': 'File Version'}, validator= lambda v: 0 <= v <= 255)
    iTime: int = field(default=None)
    darkCorrected: int = field(default=None)
    darkTime: datetime.datetime
    dataType: int = field(default=None)
    referenceTime: datetime.datetime
    channel1Wavelength: int = field(default=None)
    dataFormat: int = field(default=None)
    old_darkCurrentCount: int = field(default=None)
    old_refCount: int = field(default=None)
    old_sampleCount: int = field(default=None)
    application: int = field(default=None)
    channels: int = field(default=None)
    appData_str: str = field(default=None)
    gpsData_str: GPSdata = field(default=None)
    intergrationTime_ms: int = field(default=None)
    fo: int = field(default=None)
    darkCurrentCorrention: int = field(default=None)
    calibrationSeries: int = field(default=None)
    instrumentNum: int = field(default=None)
    yMin: int = field(default=None)
    yMax: int = field(default=None)
    xMin: int = field(default=None)
    xMax: int = field(default=None)
    ipNumBits: int = field(default=None)
    xMode: int = field(default=None)
    flags1: int = field(default=None) 
    flags2: int = field(default=None)
    flags3: int = field(default=None)
    flags4: int = field(default=None)
    darkCurrentCount: int = field(default=None)
    refCount: int = field(default=None)
    sampleCount: int = field(default=None)
    instrument: int = field(default=None)
    calBulbID: int = field(default=None)
    swir1Gain: int = field(default=None)
    swir2Gain: int = field(default=None)
    swir1Offset: int = field(default=None)
    swir2Offset: int = field(default=None)
    splice1_wavelength: int = field(default=None)
    splice2_wavelength: int = field(default=None)
    smartDetectorType: str = field(default=None)
    spare1: int = field(default=None)
    spare2: int = field(default=None)
    spare3: int = field(default=None)
    spare4: int = field(default=None)
    spare5: int = field(default=None)
    byteStream: bytes = field(default=b'\x00', metadata={'unit': '484 bytes', 'value': 'Byte Stream'}, validator= lambda v: len(v) == 484)
    byteStreamLength: int = field(default=484, metadata={'unit': 'bytes', 'value': 'Byte Stream Length'}, validator= lambda v: v == 484)

    def version_to_int(self) -> int:
        major = self.fileVersion.value
        minor = self.programVersion
        patch = self.iTime
        return (major << 16) | (minor << 8) | patch

    def int_to_version(self, version_int: int):
        self.fileVersion = FileVersion((version_int >> 16) & 0xFF)
        self.programVersion = (version_int >> 8) & 0xFF
        self.iTime = version_int & 0xFF
    







class ASDFile(object):
    
    def __init__(self):
        self.asdFileVersion = 0
        self.metadata = None
        self.spectrumData = None
        self.referenceFileHeader = None
        self.referenceData = None
        self.classifierData = None
        self.dependants = None
        self.calibrationHeader = None
        self.calibrationSeriesABS = None
        self.calibrationSeriesBSE = None
        self.calibrationSeriesLMP = None
        self.calibrationSeriesFO = None
        self.auditLog = None
        self.signature = None
        self.__asdFileStream = None
        self.__wavelengths = None

    def read(self: object, filePath: str) -> bool:
        readSuccess = False
        if os.path.exists(filePath) and os.path.isfile(filePath):
            try:
                # read in file to memory(buffer)
                with open(filePath, 'rb') as fileHandle:
                    self.__asdFileStream = fileHandle.read()
                    if self.__asdFileStream[-3:] == b'\xFF\xFE\xFD':
                        self.__bom = self.__asdFileStream[-3:]
                        self.__asdFileStream = self.__asdFileStream[:-3]
            except Exception as e:
                logger.exception(f"Error in reading the file.\nError: {e}")
        # refering C# Line 884 to identify the file version
        self.asdFileVersion, offset = self.__validate_fileVersion()
        if self.asdFileVersion > 0:
            try:
                offset = self.__parse_metadata(offset)
                self.__wavelengths = np.arange(self.metadata.channel1Wavelength, self.metadata.channel1Wavelength + self.metadata.channels * self.metadata.wavelengthStep, self.metadata.wavelengthStep)
            except Exception as e:
                logger.exception(f"Error in parsing the metadata.\nError: {e}")
            else:
                try:
                    offset = self.__parse_spectrumData(offset)
                except Exception as e:
                    logger.exception(f"Error in parsing the metadata and spectrum data.\nError: {e}")
        if self.asdFileVersion >= 2:
            try:
                offset = self.__parse_referenceFileHeader(offset)
            except Exception as e:
                logger.exception(f"Error in parsing the reference file header.\nError: {e}")
            else:
                try:
                    offset = self.__parse_referenceData(offset)
                except Exception as e:
                    logger.exception(f"Error in parsing the reference data.\nError: {e}")
        if self.asdFileVersion >= 6:
            try:
                # Read Classifier Data
                offset = self.__parse_classifierData(offset)
            except Exception as e:
                logger.exception(f"Error in parsing the classifier data.\nError: {e}")
            else:    
                try:
                    offset = self.__parse_dependentVariables(offset)
                except Exception as e:
                    logger.exception(f"Error in parsing the depndant variables.\nError: {e}")
        if self.asdFileVersion >= 7:
            try:
                # Read Calibration Header
                offset = self.__parse_calibrationHeader(offset)
            except Exception as e:
                logger.exception(f"Error in parsing the calibration header.\nError: {e}")
            else:
                try:
                    if self.calibrationHeader and (self.calibrationHeader.calibrationNum > 0):
                        # Parsing the calibration data according to 'ASD File Format version 8: Revision B', through the suquence of 'Absolute Calibration Data', 'Base Calibration Data', 'Lamp Calibration Data', 'Fiber Optic Data' successively.
                        for hdr in self.calibrationHeader.calibrationSeries:  # Number of calibrationSeries buffers in the file.
                            if hdr[0] == 0:
                                self.calibrationSeriesABS, _, _, offset = self.__parse_spectra(offset)
                            elif hdr[0] == 1:
                                self.calibrationSeriesBSE, _, _, offset = self.__parse_spectra(offset)
                            elif hdr[0] == 2:
                                self.calibrationSeriesLMP, _, _, offset = self.__parse_spectra(offset)
                            elif hdr[0] == 3:
                                self.calibrationSeriesFO, _, _, offset = self.__parse_spectra(offset)
                    # else:
                    #     logger.info(f"Calibration data is not available.")
                except Exception as e:
                    logger.exception(f"Error in parsing the calibration data.\nError: {e}")       
        if self.asdFileVersion >= 8:
            try:
                # Read Audit Log
                offset = self.__parse_auditLog(offset)
            except Exception as e:
                logger.exception(f"Error in parsing the audit log.\nError: {e}")
                # Read Signature
            else:
                try:
                    offset = self.__parse_signature(offset)
                except Exception as e:
                    logger.exception(f"Error in parsing the signature.\nError: {e}")
        readSuccess = True
        return readSuccess

    def update(self, field_name: str, new_value):
        # TODO: Add the update method to update the fields.
        # TODO: new_vulue should be the same type as the field.
        if self.metadata is not None:
            if not hasattr(self.metadata, field_name):
                raise ValueError(f"{field_name} is not vaild filed in {type(self.metadata).__name__} .")
            self.metadata = self.metadata._replace(**{field_name: new_value})
        if field_name in ['channel1Wavelength', 'channels', 'wavelengthStep']:
            self.__wavelengths = np.arange(self.metadata.channel1Wavelength, self.metadata.channel1Wavelength + self.metadata.channels * self.metadata.wavelengthStep, self.metadata.wavelengthStep)
        
    def write(self: object, file: str) -> bool:
        if os.path.exists(file):
            try:
                os.remove(file)
            except OSError as e:
                logger.exception(f"File remove error:\n{file} : {e}")
        with open(file, 'wb') as fileHandle:
            if self.asdFileVersion > 0:        
                asdFileVersionBytes, offset = self.__setFileVersion()
                fileHandle.write(asdFileVersionBytes)
                if self.metadata:
                    metadataBytes, byteLength = self.__wrap_metadata()
                    offset += byteLength
                    fileHandle.write(metadataBytes)
                    # logger.info(f"Write: Metadata offset: {offset}")
                if self.spectrumData:
                    spectrumDataBytes, byteLength = self.__wrap_spectrumData()
                    offset += byteLength
                    fileHandle.write(spectrumDataBytes)
                    # logger.info(f"Write: Spectrum Data offset: {offset}")
            if self.asdFileVersion >= 2:        
                if self.referenceFileHeader:
                    referenceFileHeaderBytes, byteLength = self.__wrap_referenceFileHeader()
                    offset = offset + byteLength
                    fileHandle.write(referenceFileHeaderBytes)
                    # logger.info(f"Write: Reference File Header offset: {offset}")
                if self.referenceData:
                    referenceDataBytes, byteLength = self.__wrap_referenceData()
                    fileHandle.write(referenceDataBytes)
                    offset = offset + byteLength
                    # logger.info(f"Write: Reference Data offset: {offset}")
                if self.classifierData:
                    classifierDataBytes, byteLength = self.__wrap_classifierData()
                    fileHandle.write(classifierDataBytes)
                    offset = offset + byteLength
                    # logger.info(f"Write: Classifier Data offset: {offset}")
                if self.dependants:
                    dependantsByteStream, byteLength = self.__wrap_dependentVariables()
                    offset = offset + byteLength
                    fileHandle.write(dependantsByteStream)
                    # logger.info(f"Write: Dependants write offset: {offset}")
            if self.asdFileVersion >= 7:
                if self.calibrationHeader:
                    calibrationHeadersBytes, byteLength = self.__wrap_calibrationHeader()
                    offset = offset + byteLength
                    fileHandle.write(calibrationHeadersBytes)
                    # logger.info(f"Write: Calibration Header write offset: {offset}")
                if self.calibrationHeader and self.calibrationHeader.calibrationNum > 0:
                    for i in range(self.calibrationHeader.calibrationNum):
                        if self.calibrationHeader.calibrationSeries[i][0] == 0:
                            calibrationSeriesABSBytes, byteLength = self.__wrap_spectra(self.calibrationSeriesABS)
                            offset = offset + byteLength
                            fileHandle.write(calibrationSeriesABSBytes)
                            # logger.info(f"Write: Calibration Series ABS write offset: {offset}")
                        elif self.calibrationHeader.calibrationSeries[i][0] == 1:
                            calibrationSeriesBSEBytes, byteLength = self.__wrap_spectra(self.calibrationSeriesBSE)
                            offset = offset + byteLength
                            fileHandle.write(calibrationSeriesBSEBytes)
                            # logger.info(f"Write: Calibration Series BSE write offset: {offset}")
                        elif self.calibrationHeader.calibrationSeries[i][0] == 2:
                            calibrationSeriesLMPBytes, byteLength = self.__wrap_spectra(self.calibrationSeriesLMP)
                            offset = offset + byteLength
                            fileHandle.write(calibrationSeriesLMPBytes)
                            # logger.info(f"Write: Calibration Series LMP write offset: {offset}")
                        elif self.calibrationHeader.calibrationSeries[i][0] == 3:
                            calibrationSeriesFOBytes, byteLength = self.__wrap_spectra(self.calibrationSeriesFO)
                            offset = offset + byteLength
                            fileHandle.write(calibrationSeriesFOBytes)
                            # logger.info(f"Write: Calibration Series FO write offset: {offset}")      
            if self.asdFileVersion >= 8:
                auditLogBytes, byteLength = self.__wrap_auditLog()
                fileHandle.write(auditLogBytes)
                offset = offset + len(auditLogBytes)
                # logger.info(f"Write: Audit Log Header write offset: {offset}")
                signatureBytes, byteLength = self.__wrap_signature()
                fileHandle.write(signatureBytes)
                offset = offset + len(signatureBytes)
                # logger.info(f"Write: Signature Header write offset: {offset}")
            if self.__bom:
                fileHandle.write(self.__bom)
            # logger.info(f"{file} write success")
        return True

    def __check_offset(func):
        def wrapper(self, offset, *args, **kwargs):
            if offset is not None and offset < len(self.__asdFileStream):
                return func(self, offset, *args, **kwargs)
            else:
                logger.info("Reached the end of the binary byte stream. offset: {offset}")
                return None, None
        return wrapper
    
    @__check_offset
    def __parse_metadata(self: object, offset: int) -> int:
        asdMetadataFormat = '<157s 18s b b b b l b l f f b b b b b H 128s 56s L h h H H f f f f h b 4b H H H b L H H H H f f 27s 5b'
        asdMetadatainfo = namedtuple('metadata', "comments when daylighSavingsFlag programVersion fileVersion iTime \
        darkCorrected darkTime dataType referenceTime channel1Wavelength wavelengthStep dataFormat \
        old_darkCurrentCount old_refCount old_sampleCount application channels appData_str gpsData_str \
        intergrationTime_ms fo darkCurrentCorrention calibrationSeries instrumentNum yMin yMax xMin xMax \
        ipNumBits xMode flags1 flags2 flags3 flags4 darkCurrentCount refCount sampleCount instrument \
        calBulbID swir1Gain swir2Gain swir1Offset swir2Offset splice1_wavelength splice2_wavelength smartDetectorType \
        spare1 spare2 spare3 spare4 spare5 byteStream byteStreamLength")
        try:
            comments, when, programVersion, fileVersion, iTime, darkCorrected, darkTime, \
            dataType, referenceTime, channel1Wavelength, wavelengthStep, dataFormat, old_darkCurrentCount, old_refCount, old_sampleCount, \
            application, channels, appData, gpsData, intergrationTime_ms, fo, darkCurrentCorrention, calibrationSeries, instrumentNum, \
            yMin, yMax, xMin, xMax, ipNumBits, xMode, flags1, flags2, flags3, flags4, darkCurrentCount, refCount, \
            sampleCount, instrument, calBulbID, swir1Gain, swir2Gain, swir1Offset, swir2Offset, \
            splice1_wavelength, splice2_wavelength, smartDetectorType, \
            spare1, spare2, spare3, spare4, spare5 = struct.unpack_from(asdMetadataFormat, self.__asdFileStream, offset)
            comments = comments.strip(b'\x00') # remove null bytes
            # Parse the time from the buffer, format is year, month, day, hour, minute, second
            when_datetime, daylighSavingsFlag = self.__parse_ASDFilewhen((struct.unpack_from('9h', when)))  # 9 short integers
            darkTime = datetime.datetime.fromtimestamp(darkTime) 
            referenceTime = datetime.datetime.fromtimestamp(referenceTime)
            ByteStream = self.__asdFileStream[:484]
            ByteStreamLength = len(ByteStream)
            offset += 481
            self.metadata = asdMetadatainfo._make(
                (comments, when_datetime, daylighSavingsFlag, programVersion, fileVersion, iTime, darkCorrected, darkTime, \
                dataType, referenceTime, channel1Wavelength, wavelengthStep, dataFormat, old_darkCurrentCount, old_refCount, old_sampleCount, \
                application, channels, appData, gpsData, intergrationTime_ms, fo, darkCurrentCorrention, calibrationSeries, instrumentNum, \
                yMin, yMax, xMin, xMax, ipNumBits, xMode, flags1, flags2, flags3, flags4, darkCurrentCount, refCount, \
                sampleCount, instrument, calBulbID, swir1Gain, swir2Gain, swir1Offset, swir2Offset, \
                splice1_wavelength, splice2_wavelength, smartDetectorType, \
                spare1, spare2, spare3, spare4, spare5 , ByteStream, ByteStreamLength))
        except Exception as e:
            logger.exception(f"Metadata (ASD File Header) parse error: {e}")
            return None
        # logger.info(f"Read: metadata end offset: {offset}")
        return offset
    
    def __wrap_metadata(self: object) -> tuple[bytes, int]:
        asdMetadataFormat = '<157s 18s b b b b l b l f f b b b b b H 128s 56s L h h H H f f f f h b 4b H H H b L H H H H f f 27s 5b'
        try:
            byteStream = struct.pack(
                asdMetadataFormat,
                self.metadata.comments.ljust(157, b'\x00'),
                self.__wrap_ASDFilewhen(self.metadata.when, self.metadata.daylighSavingsFlag),
                self.metadata.programVersion,
                self.metadata.fileVersion,
                self.metadata.iTime,
                self.metadata.darkCorrected,
                int(self.metadata.darkTime.timestamp()),
                self.metadata.dataType,
                int(self.metadata.referenceTime.timestamp()),
                self.metadata.channel1Wavelength,
                self.metadata.wavelengthStep,
                self.metadata.dataFormat,
                self.metadata.old_darkCurrentCount,
                self.metadata.old_refCount,
                self.metadata.old_sampleCount,
                self.metadata.application,
                self.metadata.channels,
                self.metadata.appData_str.ljust(128, b'\x00'),
                self.metadata.gpsData_str.ljust(56, b'\x00'),
                self.metadata.intergrationTime_ms,
                self.metadata.fo,
                self.metadata.darkCurrentCorrention,
                self.metadata.calibrationSeries,
                self.metadata.instrumentNum,
                self.metadata.yMin,
                self.metadata.yMax,
                self.metadata.xMin,
                self.metadata.xMax,
                self.metadata.ipNumBits,
                self.metadata.xMode,
                self.metadata.flags1,
                self.metadata.flags2,
                self.metadata.flags3,
                self.metadata.flags4,
                self.metadata.darkCurrentCount,
                self.metadata.refCount,
                self.metadata.sampleCount,
                self.metadata.instrument,
                self.metadata.calBulbID,
                self.metadata.swir1Gain,
                self.metadata.swir2Gain,
                self.metadata.swir1Offset,
                self.metadata.swir2Offset,
                self.metadata.splice1_wavelength,
                self.metadata.splice2_wavelength,
                self.metadata.smartDetectorType.ljust(27, b'\x00'),
                self.metadata.spare1,
                self.metadata.spare2,
                self.metadata.spare3,
                self.metadata.spare4,
                self.metadata.spare5
                )
            if len(byteStream) == 481:
                return byteStream, 481
            else:
                logger.info(f"Metadata wrap error (not 481 bytes): {len(byteStream)}")
                return None, None
        except Exception as e:
            logger.exception(f"Metadata (ASD File Header) wrap error: {e}")
            return False
        
    @__check_offset
    def __parse_spectrumData(self: object, offset: int) -> int:
        try:
            spectrumDataInfo = namedtuple('spectrumData', 'spectra byteStream byteStreamLength')
            spectra, spectrumDataStream, spectrumDataStreamLength, offset = self.__parse_spectra(offset)
            self.spectrumData = spectrumDataInfo._make((spectra, spectrumDataStream, spectrumDataStreamLength))
            # logger.info(f"Read: spectrum data end offset: {offset}")
            return offset
        except Exception as e:
            logger.exception(f"Spectrum Data parse error: {e}")
            return None
    
    def __wrap_spectrumData(self: object) -> tuple[bytes, int]:
        try:
            byteStream, byteStreamLength = self.__wrap_spectra(self.spectrumData.spectra)
            return byteStream, byteStreamLength
        except Exception as e:
            logger.exception(f"Spectrum Data wrap error: {e}")
            return None, None

    @__check_offset
    def __parse_referenceFileHeader(self: object, offset: int) -> int:
        initOffset = offset
        asdReferenceFormat = 'q q'
        asdreferenceFileHeaderInfo = namedtuple('referenceFileHeader', "referenceFlag referenceTime spectrumTime referenceDescription byteStream byteStreamLength")
        try:
            referenceFlag, offset = self.__parse_Bool(offset)
            referenceTime_llongint, spectrumTime_llongint = struct.unpack_from(asdReferenceFormat, self.__asdFileStream, offset)
            offset += struct.calcsize(asdReferenceFormat)
            referenceDescription, offset = self.__parse_bstr(offset)
            byteStream = self.__asdFileStream[initOffset:offset]
            byteStreamLength = len(byteStream)
            self.referenceFileHeader = asdreferenceFileHeaderInfo._make((referenceFlag, referenceTime_llongint, spectrumTime_llongint, referenceDescription, byteStream, byteStreamLength))
            # logger.info(f"Read: reference file header end offset: {offset}")
            return offset
        except Exception as e:
            logger.exception(f"Reference File Header parse error: {e}")
            return None
    
    def __wrap_referenceFileHeader(self: object) -> tuple[bytes, int]:
        try:
            referenceFlagBytes, byteStreamLength = self.__wrap_Bool(self.referenceFileHeader.referenceFlag)
            asdReferenceFormat = 'q q'
            timeBytes = struct.pack(asdReferenceFormat, self.referenceFileHeader.referenceTime, self.referenceFileHeader.spectrumTime)
            byteStreamLength += struct.calcsize(asdReferenceFormat)
            DescriptionBytes, lengthstr = self.__wrap_bstr(self.referenceFileHeader.referenceDescription)
            byteStream = referenceFlagBytes + timeBytes + DescriptionBytes
            byteStreamLength += lengthstr
            return byteStream, byteStreamLength
        except Exception as e:
            logger.exception(f"Reference File Header wrap error: {e}")
            return None, None

    @__check_offset
    def __parse_referenceData(self: object, offset: int) -> int:
        try:
            referenceDataInfo = namedtuple('referenceData', 'spectra byteStream byteStreamLength')
            spectra, referenceDataStream, referenceDataStreamLength, offset = self.__parse_spectra(offset)
            self.referenceData = referenceDataInfo._make((spectra, referenceDataStream, referenceDataStreamLength))
            # logger.info(f"Read: reference data end offset: {offset}")
            return offset
        except Exception as e:
            logger.exception(f"Reference Data parse error: {e}")
            return None
    
    def __wrap_referenceData(self: object) -> tuple[bytes, int]:
        try:
            byteStream, byteStreamLength = self.__wrap_spectra(self.referenceData.spectra)
            return byteStream, byteStreamLength
        except Exception as e:
            logger.exception(f"Reference Data wrap error: {e}")
            return None, None

    @__check_offset
    def __parse_classifierData(self: object, offset: int) -> int:
        try:
            initOffset = offset
            yCode, yModelType = struct.unpack_from('bb', self.__asdFileStream, offset)
            offset += struct.calcsize('bb')
            title_str, offset = self.__parse_bstr(offset)
            subtitle_str, offset = self.__parse_bstr(offset)
            productName_str, offset = self.__parse_bstr(offset)
            vendor_str, offset = self.__parse_bstr(offset)
            lotNumber_str, offset = self.__parse_bstr(offset)
            sample__str, offset = self.__parse_bstr(offset)
            modelName_str, offset = self.__parse_bstr(offset)
            operator_str, offset = self.__parse_bstr(offset)
            dateTime_str, offset = self.__parse_bstr(offset)
            instrument_str, offset = self.__parse_bstr(offset)
            serialNumber_str, offset = self.__parse_bstr(offset)
            displayMode_str, offset = self.__parse_bstr(offset)
            comments_str, offset = self.__parse_bstr(offset)
            units_str, offset = self.__parse_bstr(offset)
            filename_str, offset = self.__parse_bstr(offset)
            username_str, offset = self.__parse_bstr(offset)
            reserved1_str, offset = self.__parse_bstr(offset)
            reserved2_str, offset = self.__parse_bstr(offset)
            reserved3_str, offset = self.__parse_bstr(offset)
            reserved4_str, offset = self.__parse_bstr(offset)
            constituantCount_int, = struct.unpack_from('H', self.__asdFileStream, offset)
            offset += struct.calcsize('H')
            asdClassifierDataInfo = namedtuple('classifierData', 'yCode yModelType title subtitle productName vendor lotNumber sample modelName operator dateTime instrument serialNumber displayMode comments units filename username reserved1 reserved2 reserved3 reserved4 constituantCount constituantItems byteStream byteStreamLength')
            # Past the constituants
            if constituantCount_int > 0:
                offset += 10
                # logger.info(f"constituant items ")
                constituantItems = []
                for i in range(constituantCount_int):
                    # logger.info(f"constituant items sequence: {i}")
                    item, offset = self.__parse_constituantType(offset)
                    constituantItems.append(item)
            if constituantCount_int == 0:
                constituantItems = []
                offset += 2 
            byteStream = self.__asdFileStream[initOffset:offset]
            byteStreamLength = len(byteStream)
            self.classifierData = asdClassifierDataInfo._make((yCode, yModelType, title_str, subtitle_str, productName_str, vendor_str, lotNumber_str, sample__str, modelName_str, operator_str, dateTime_str, instrument_str, serialNumber_str, displayMode_str, comments_str, units_str, filename_str, username_str, reserved1_str, reserved2_str, reserved3_str, reserved4_str, constituantCount_int, constituantItems, byteStream, byteStreamLength))
            # logger.info(f"Read: classifier Data end offset: {offset}")
            return offset
        except Exception as e:
            logger.exception(f"classifier Data parse error: {e}")
            return None

    def __wrap_classifierData(self: object) -> tuple[bytes, int]:
        try:
            calssifierData_1 = struct.pack('bb', self.classifierData.yCode, self.classifierData.yModelType)
            title_bstr, _ = self.__wrap_bstr(self.classifierData.title)
            subtitle_bstr, _ = self.__wrap_bstr(self.classifierData.subtitle)
            productName_bstr, _ = self.__wrap_bstr(self.classifierData.productName)
            vendor_bstr, _ = self.__wrap_bstr(self.classifierData.vendor)
            lotNumber_bstr, _ = self.__wrap_bstr(self.classifierData.lotNumber)
            sample_bstr, _ = self.__wrap_bstr(self.classifierData.sample)
            modelName_bstr, _ = self.__wrap_bstr(self.classifierData.modelName)
            operator_bstr, _ = self.__wrap_bstr(self.classifierData.operator)
            dateTime_bstr, _ = self.__wrap_bstr(self.classifierData.dateTime)
            instrument_bstr, _ = self.__wrap_bstr(self.classifierData.instrument)
            serialNumber_bstr, _ = self.__wrap_bstr(self.classifierData.serialNumber)
            displayMode_bstr, _ = self.__wrap_bstr(self.classifierData.displayMode)
            comments_bstr, _ = self.__wrap_bstr(self.classifierData.comments)
            units_bstr, _ = self.__wrap_bstr(self.classifierData.units)
            filename_bstr, _ = self.__wrap_bstr(self.classifierData.filename)
            username_bstr, _ = self.__wrap_bstr(self.classifierData.username)
            reserved1_bstr, _ = self.__wrap_bstr(self.classifierData.reserved1)
            reserved2_bstr, _ = self.__wrap_bstr(self.classifierData.reserved2)
            reserved3_bstr, _ = self.__wrap_bstr(self.classifierData.reserved3)
            reserved4_bstr, _ = self.__wrap_bstr(self.classifierData.reserved4)
            constituantCount_bstr = struct.pack('H', self.classifierData.constituantCount)

            constituantByteStream = b''
            if self.classifierData.constituantCount > 0:
                # Number of dimensions in the Array, as reference C# 1374-1379 lines, short, stream, stream
                constituantByteStream += struct.pack('H', 1)
                # Number of elements in each dimension
                constituantByteStream += struct.pack('I', self.classifierData.constituantCount)
                constituantByteStream += struct.pack('I', 0) 
                for i in range(self.classifierData.constituantCount):
                    item_packed, _ = self.__wrap_constituantType(self.classifierData.constituantItems[i])
                    constituantByteStream += item_packed
            if self.classifierData.constituantCount == 0:
                constituantByteStream += b'\x00\x00'
            ByteStream = calssifierData_1 + title_bstr + subtitle_bstr + productName_bstr + vendor_bstr + lotNumber_bstr + sample_bstr + modelName_bstr + operator_bstr + dateTime_bstr + instrument_bstr + serialNumber_bstr + displayMode_bstr + comments_bstr + units_bstr + filename_bstr + username_bstr + reserved1_bstr + reserved2_bstr + reserved3_bstr + reserved4_bstr + constituantCount_bstr + constituantByteStream
            byteStreamLength = len(ByteStream)
            return ByteStream, byteStreamLength
        except Exception as e:
            logger.exception(f"Classifier Data wrap error: {e}")
            return None, None

    @__check_offset
    def __parse_dependentVariables(self: object, offset: int) -> int:
        try:
            initOffset = offset
            dependantInfo = namedtuple('dependants', 'saveDependentVariables dependentVariableCount dependentVariableLabels dependentVariableValue byteStream byteStreamLength')
            saveDependentVariables, offset = self.__parse_Bool(offset)
            dependant_format = 'h'
            dependentVariableCount, = struct.unpack_from(dependant_format, self.__asdFileStream, offset)
            offset += struct.calcsize(dependant_format)
            if dependentVariableCount > 0:
                offset += 10
                dependantVariableLabels_list = []
                for i in range(dependentVariableCount):
                    dependentVariableLabel, offset = self.__parse_bstr(offset)
                    dependantVariableLabels_list.append(dependentVariableLabel)
                offset += 10
                dependantVariableValues_list = []
                for i in range(dependentVariableCount):
                    dependentVariableValue, = struct.unpack_from('<f', self.__asdFileStream, offset)
                    dependantVariableValues_list.append(dependentVariableValue)
                    offset += struct.calcsize('<f')
                self.dependants = dependantInfo._make((saveDependentVariables, dependentVariableCount, dependantVariableLabels_list, dependantVariableValues_list, self.__asdFileStream[initOffset:offset], len(self.__asdFileStream[initOffset:offset])))
            # if there are no dependent variables, skip 4 bytes (corresponding to 4 empty byte positions b'\x00')
            if dependentVariableCount == 0:
                offset += 4
                self.dependants = dependantInfo._make((saveDependentVariables, dependentVariableCount, b'', 0, self.__asdFileStream[initOffset:offset], len(self.__asdFileStream[initOffset:offset])))
            # logger.info(f"Read: dependant variables end offset: {offset}")
            return offset
        except Exception as e:
            logger.exception(f"Dependant variables parse error: {e}")
            return None
    
    def __wrap_dependentVariables(self: object) -> tuple[bytes, int]:
        try:
            byteStream, _ = self.__wrap_Bool(self.dependants.saveDependentVariables)
            dependant_format = 'h'
            byteStream += struct.pack(dependant_format, self.dependants.dependentVariableCount)
            if self.dependants.dependentVariableCount > 0:
                depentVariablesByteStream = b''
                # Number of dimensions in the Array
                depentVariablesByteStream += struct.pack('H', 1)
                # Number of elements in each dimension
                depentVariablesByteStream += struct.pack('I', self.dependants.dependentVariableCount)
                depentVariablesByteStream += struct.pack('I', 0) 
                for i in range(self.dependants.dependentVariableCount):
                    item_packed, _ = self.__wrap_bstr(self.dependants.dependentVariableLabels[i])
                    depentVariablesByteStream += item_packed
                # Number of dimensions in the Array
                depentVariablesByteStream += struct.pack('H', 1)
                # Number of elements in each dimension
                depentVariablesByteStream += struct.pack('I', self.dependants.dependentVariableCount)
                depentVariablesByteStream += struct.pack('I', 0) 
                for i in range(self.dependants.dependentVariableCount):
                    item_packed = struct.pack('<f', self.dependants.dependentVariableValue[i])
                    depentVariablesByteStream += item_packed
                    _ += struct.calcsize('<f')
                byteStream += depentVariablesByteStream
            if self.dependants.dependentVariableCount == 0:
                byteStream += b'\x00\x00\x00\x00'
            byteStreamLength = len(byteStream)
            return byteStream, byteStreamLength
        except Exception as e:
            logger.exception(f"Dependant Variable wrap error: {e}")
            return None, None

    @__check_offset
    def __parse_calibrationHeader(self: object, offset: int) -> int:
        try:
            calibrationHeaderCountNum_format = 'b'
            calibrationSeries_buffer_format = '<b 20s i h h'
            calibrationHeaderInfo = namedtuple('calibrationHeader', 'calibrationNum calibrationSeries, byteStream byteStreamLength')
            calibrationHeaderCount, = struct.unpack_from(calibrationHeaderCountNum_format, self.__asdFileStream, offset)
            byteStream = self.__asdFileStream[offset:offset + struct.calcsize(calibrationHeaderCountNum_format) + struct.calcsize(calibrationSeries_buffer_format)*calibrationHeaderCount]
            byteStreamLength = len(byteStream)
            offset += struct.calcsize(calibrationHeaderCountNum_format)
            if calibrationHeaderCount > 0:
                calibrationSeries = []
                for i in range(calibrationHeaderCount):
                    (cbtype, cbname, cbIntergrationTime_ms, cbSwir1Gain, cbWwir2Gain) = struct.unpack_from(calibrationSeries_buffer_format, self.__asdFileStream, offset)
                    name = cbname.strip(b'\x00')
                    calibrationSeries.append(((cbtype, name, cbIntergrationTime_ms, cbSwir1Gain, cbWwir2Gain)))
                    offset += struct.calcsize(calibrationSeries_buffer_format)
                self.calibrationHeader = calibrationHeaderInfo._make((calibrationHeaderCount, calibrationSeries, byteStream, byteStreamLength))
            else:
                self.calibrationHeader = calibrationHeaderInfo._make((calibrationHeaderCount, [], byteStream, byteStreamLength))
            # logger.info(f"Read: calibration header end offset: {offset}")
            return offset
        except Exception as e:
            logger.exception(f"Calibration Header parse error: {e}")
            return None
    
    def __wrap_calibrationHeader(self: object) -> tuple[bytes, int]:
        try:
            calibrationHeaderCountNum_format = 'b'
            calibrationSeries_buffer_format = '<b 20s i h h'
            calibrationSeriesBytes = struct.pack(calibrationHeaderCountNum_format, self.calibrationHeader.calibrationNum)
            if self.calibrationHeader.calibrationNum > 0:
                for calibrationSerie in self.calibrationHeader.calibrationSeries:
                    cbtype, cbname, cbIntergrationTime_ms, cbSwir1Gain, cbWwir2Gain = calibrationSerie
                    cbname_bytes = cbname.ljust(20, b'\x00')
                    calibrationSeries_packed = struct.pack(calibrationSeries_buffer_format, cbtype, cbname_bytes, cbIntergrationTime_ms, cbSwir1Gain, cbWwir2Gain)
                    calibrationSeriesBytes += calibrationSeries_packed
            byteStreamLength = len(calibrationSeriesBytes)
            return calibrationSeriesBytes, byteStreamLength
        except Exception as e:
            logger.exception(f"Calibration Header wrap error: {e}")
            return None, None

    @__check_offset
    def __parse_auditLog(self: object, offset: int) -> int:
        try:
            initOffset = offset
            auditLogInfo = namedtuple('auditLog', 'auditCount auditEvents byteStream byteStreamLength')
            additCount, = struct.unpack_from('l', self.__asdFileStream, offset)
            offset += struct.calcsize('l')
            if additCount > 0:
                offset += 10
                auditEvents, auditEventsLength = self.__parse_auditEvents(offset)
                offset += auditEventsLength
            self.auditLog = auditLogInfo._make((additCount, auditEvents, self.__asdFileStream[initOffset:offset], len(self.__asdFileStream[initOffset:offset])))
            # logger.info(f"Read: audit log header end offset: {offset}")
            return offset
        except Exception as e:
            logger.exception(f"Audit Log Header parse error: {e}")
            return None
    
    def __wrap_auditLog(self: object) -> tuple[bytes, int]:
        try:
            byteStream = struct.pack('l', self.auditLog.auditCount)
            auditBytes = b''
            if self.auditLog.auditCount > 0:
                auditBytes += struct.pack('H', 1)
                auditBytes += struct.pack('I', self.auditLog.auditCount)
                auditBytes += struct.pack('I', 0)
                auditEventsBytes, auditBytesLength = self.__wrap_auditEvents(self.auditLog.auditEvents)
                auditBytes += auditEventsBytes
            byteStream += auditBytes
            byteStreamLength = len(byteStream)
            return byteStream, byteStreamLength
        except Exception as e:
            logger.exception(f"Audit Log Header wrap error: {e}")
            return None, None

    @__check_offset
    def __parse_signature(self: object, offset: int) -> int:
        try:
            initOffset = offset
            signatureInfo = namedtuple('signature', 'signed, signatureTime, userDomain, userLogin, userName, source, reason, notes, publicKey, signature, byteStream, byteStreamLength')
            signed, = struct.unpack_from('b', self.__asdFileStream, offset)
            offset += struct.calcsize('b')
            signatureTime, = struct.unpack_from('q', self.__asdFileStream, offset)
            offset += struct.calcsize('q')
            userDomain, offset = self.__parse_bstr(offset)
            userLogin, offset = self.__parse_bstr(offset)
            userName, offset = self.__parse_bstr(offset)
            source, offset = self.__parse_bstr(offset)
            reason, offset = self.__parse_bstr(offset)
            notes, offset = self.__parse_bstr(offset)
            publicKey, offset = self.__parse_bstr(offset)
            # signature, offset = self.__parse_bstr(offset)
            signature, = struct.unpack_from('128s', self.__asdFileStream, offset)
            offset += struct.calcsize('128s')
            byteStream = self.__asdFileStream[initOffset:offset]
            byteStreamLength = len(byteStream)
            self.signature = signatureInfo._make((signed, signatureTime, userDomain, userLogin, userName, source, reason, notes, publicKey, signature, byteStream, byteStreamLength))
            # logger.info(f"Read: signature end offset: {offset}")
        except Exception as e:
            logger.exception(f"Signature parse error: {e}")
            return None
        return offset

    def __wrap_signature(self: object) -> tuple[bytes, int]:
        try:
            signedBytes = struct.pack('b', self.signature.signed)
            signatureTimeBytes = struct.pack('q', self.signature.signatureTime)
            userDomainBytes, _ = self.__wrap_bstr(self.signature.userDomain)
            userLoginBytes, _ = self.__wrap_bstr(self.signature.userLogin)
            userNameBytes, _ = self.__wrap_bstr(self.signature.userName)
            sourceBytes, _ = self.__wrap_bstr(self.signature.source)
            reasonBytes, _ = self.__wrap_bstr(self.signature.reason)
            notesBytes, _ = self.__wrap_bstr(self.signature.notes)
            publicKeyBytes, _ = self.__wrap_bstr(self.signature.publicKey)
            signatureBytes = struct.pack("128s", self.signature.signature)
            byteStream = signedBytes + signatureTimeBytes + userDomainBytes + userLoginBytes + userNameBytes + sourceBytes + reasonBytes + notesBytes + publicKeyBytes + signatureBytes
            byteStreamLength = len(byteStream)
            return byteStream, byteStreamLength
        except Exception as e:
            logger.exception(f"Signature wrap error: {e}")
            return None, None

    @__check_offset
    def __parse_spectra(self: object, offset: int) -> tuple[np.array, bytes, int, int]:
        try:
            spectra = np.array(struct.unpack_from('<{}d'.format(self.metadata.channels), self.__asdFileStream, offset))
            offset += (self.metadata.channels * 8)
            spectrumDataStream = self.__asdFileStream[offset:offset + self.metadata.channels * 8]
            spectrumDataStreamLength = len(spectrumDataStream)
            return spectra, spectrumDataStream, spectrumDataStreamLength, offset
        except Exception as e:
            logger.exception(f"Spectrum data parse error: {e}")
            return None, None, None, None
    
    def __wrap_spectra(self: object, spectra: np.array) -> tuple[bytes, int]:
        try:
            spectrumDataBytes = struct.pack('<{}d'.format(self.metadata.channels), *spectra)
            byteLength = self.metadata.channels * 8
            # logger.info(f"Spectrum data bytes length: {byteLength}")
            return spectrumDataBytes, byteLength
        except Exception as e:
            logger.exception(f"Spectrum data wrap error {e}")
            return None, None

    @__check_offset
    def __parse_constituantType(self: object, offset: int) -> tuple[tuple, int]:
        try:
            constituentName, offset = self.__parse_bstr(offset)
            passFail, offset = self.__parse_bstr(offset)
            fmt = '<d d d d d d d d d l d d'
            mDistance, mDistanceLimit, concentration, concentrationLimit, fRatio, residual, residualLimit, scores, scoresLimit, modelType, reserved1, reserved2 = struct.unpack_from(fmt, self.__asdFileStream, offset)
            merterialReportInfo = namedtuple('itemsInMeterialReport', 'constituentName passFail mDistance mDistanceLimit concentration concentrationLimit fRatio residual residualLimit scores scoresLimit modelType reserved1 reserved2')
            itemsInMeterialReport = merterialReportInfo._make((constituentName, passFail, mDistance, mDistanceLimit, concentration, concentrationLimit, fRatio, residual, residualLimit, scores, scoresLimit, modelType, reserved1, reserved2))
            offset += struct.calcsize(fmt)
            # logger.info(f"Read: constituant type end offset: {offset}")
            return itemsInMeterialReport, offset
        except Exception as e:
            logger.exception(f"Constituant Type parse error {e}")
            return None, None
    
    def __wrap_constituantType(self: object, itemsInMeterialReport: tuple) -> tuple[bytes, int]:
        try:
            constituentName_bstr, _ = self.__wrap_bstr(itemsInMeterialReport.constituentName)
            passFail_bstr, _ = self.__wrap_bstr(itemsInMeterialReport.passFail)
            fmt = '<d d d d d d d d d l d d'
            constituentPartial = struct.pack(fmt, itemsInMeterialReport.mDistance, itemsInMeterialReport.mDistanceLimit, itemsInMeterialReport.concentration, itemsInMeterialReport.concentrationLimit, itemsInMeterialReport.fRatio, itemsInMeterialReport.residual, itemsInMeterialReport.residualLimit, itemsInMeterialReport.scores, itemsInMeterialReport.scoresLimit, itemsInMeterialReport.modelType, itemsInMeterialReport.reserved1, itemsInMeterialReport.reserved2)
            byteStream = constituentName_bstr + passFail_bstr + constituentPartial
            byteStreamLength = len(byteStream)
            return byteStream, byteStreamLength
        except Exception as e:
            logger.exception(f"Constituant type wrap error {e}")
            return None, None

    @__check_offset
    def __parse_bstr(self: object, offset: int) -> tuple[str, int]:
        try:
            size, = struct.unpack_from('<h', self.__asdFileStream, offset)
            offset += struct.calcsize('<h')
            bstr_format = '<{}s'.format(size)
            str = ''
            if size >= 0:
                bstr, = struct.unpack_from(bstr_format, self.__asdFileStream, offset)
                str = bstr.decode('utf-8')
            offset += struct.calcsize(bstr_format)
            return str, offset
        except struct.error as err:
            logger.exception(f"Byte string parse error: {err}")
            return None, None
    
    def __wrap_bstr(self: object, string: str) -> tuple[bytes, int]:
        try:
            if isinstance(string, bytes):
                size = len(string)
                bstr_format = '<{}s'.format(size)
                byteStream = struct.pack('h', size) + struct.pack(bstr_format, string)
            elif isinstance(string, str):
                bstr = string.encode('utf-8')
                size = len(bstr)
                bstr_format = '<{}s'.format(size)
                byteStream = struct.pack('h', size) + struct.pack(bstr_format, bstr)
                byteStreamLength = len(byteStream)
            return byteStream, byteStreamLength
        except struct.error as err:
            logger.exception(f"String wrap error: {err}")
            return None, None

    @__check_offset
    def __parse_Bool(self: object, offset: int) -> tuple[bool, int]:
        try:
            buffer = self.__asdFileStream[offset:offset + 2]
            if buffer == b'\xFF\xFF':
                return True, offset + 2
            elif buffer == b'\x00\x00':
                return False, offset + 2
            else:
                raise ValueError("Invalid Boolean value")
        except Exception as e:
            return None, None
    
    def __wrap_Bool(self: object, bool: bool) -> tuple[bytes, int]:
        try:
            buffer = bytearray(2)
            if bool:
                buffer[0] = 0xFF
                buffer[1] = 0xFF
            else:
                buffer[0] = 0x00
                buffer[1] = 0x00
            return buffer, 2
        except Exception as e:
            return None, None
    
    @__check_offset
    def __parse_auditEvents(self: object, offset: int) -> tuple[list, int]:
        try:
            auditEvents_str = self.__asdFileStream[offset:].decode('utf-8', errors='ignore')
            auditPattern = re.compile(r'<Audit_Event>(.*?)</Audit_Event>', re.DOTALL)
            auditEvents = auditPattern.findall(auditEvents_str)
            auditEvents_list = []
            auditEventLength = 0
            for auditEvent in auditEvents:
                auditEvent = "<Audit_Event>" + auditEvent + "</Audit_Event>"
                auditEventLength += len(auditEvent.encode('utf-8')) + 2
                auditEvents_list.append(auditEvent)
            auditEventsTuple_list = []
            for auditEvent in auditEvents_list:
                auditEventtuple = self.__parse_auditLogEvent(auditEvent)
                auditEventsTuple_list.append(auditEventtuple)
            return auditEventsTuple_list, auditEventLength
        except Exception as e:
            logger.exception(f"Audit Event parse error: {e}")
            return None, None
        
    def __wrap_auditEvents(self: object, auditEvents: list) -> tuple[bytes, int]:
        try:
            auditEvents_bstr = b''
            for auditEvent in auditEvents:
                auditEvent_bstr = self.__wrap_auditLogEvent(auditEvent)
                auditEvents_bstr += auditEvent_bstr
            size = len(auditEvent_bstr)
            byteStream = struct.pack('<h', size) + auditEvent_bstr
            byteStreamLength = len(byteStream)
            return byteStream, byteStreamLength
        except Exception as e:
            logger.exception(f"Audit Event wrap error: {e}")
            return None, None
        
    def __parse_auditLogEvent(self: object, event: str) -> tuple:
        try:
            auditInfo = namedtuple('event', 'application appVersion name login time source function notes')
            root = ET.fromstring(event)
            application = root.find('Audit_Application').text
            appVersion = root.find('Audit_AppVersion').text
            name = root.find('Audit_Name').text
            login = root.find('Audit_Login').text
            time = root.find('Audit_Time').text
            source = root.find('Audit_Source').text
            function = root.find('Audit_Function').text
            notes = root.find('Audit_Notes').text
            auditEvents = auditInfo._make((application, appVersion, name, login, time, source, function, notes))
            return auditEvents
        except Exception as e:
            logger.exception(f"Audit Log Data parse error: {e}")
            return None

    def __wrap_auditLogEvent(self: object, event: tuple) -> str:
        try:
            doc = ET.Element('Audit_Event')
            ET.SubElement(doc, 'Audit_Application').text = event.application
            ET.SubElement(doc, 'Audit_AppVersion').text = event.appVersion
            ET.SubElement(doc, 'Audit_Name').text = event.name
            ET.SubElement(doc, 'Audit_Login').text = event.login
            ET.SubElement(doc, 'Audit_Time').text = event.time
            ET.SubElement(doc, 'Audit_Source').text = event.source
            ET.SubElement(doc, 'Audit_Function').text = event.function
            ET.SubElement(doc, 'Audit_Notes').text = event.notes
            auditEvent_xml_str = ET.tostring(doc, encoding='utf-8')
            # logger.info(f"Generated XML: {auditEvent_xml_xtr}")
            return auditEvent_xml_str
        except Exception as e:
            logger.exception(f"Error generating XML: {e}")
            return None

    def __validate_fileVersion(self: object) -> int:
        try:
            # read the file version from the first 3 bytes of the file
            version_data = self.__asdFileStream[:3].decode('utf-8')
            if version_data not in version_dict:
                raise ValueError(f"Unsupport File Version: {version_data}")
            # set the file version based on the version string
            fileversion = version_dict[version_data]
            # logger.info(f"File Version: {fileversion}")
            return fileversion, 3
        except Exception as e:
            logger.exception(f"File Version Validation Error:\n{e}")
            return -1, 3
        
    def __setFileVersion(self: object) -> bytes:
        if self.asdFileVersion == 1:
            versionBytes = "ASD".encode("utf-8")
        elif self.asdFileVersion > 1:
            versionBytes = f"as{self.asdFileVersion}".encode("utf-8")
        # logger.info(f"File Version: {self.asdFileVersion}")
        return versionBytes, 3


    
    def __parse_gps(self: object, gps_field: bytes) -> tuple:
        # Domumentation: ASD File Format Version 8, page 4
        gps_tuple = namedtuple('gpsdata', 'heading speed latitude longitude altitude')
        try:
            gpsDatadFormat = '<d d d d d h b b b b b h 5s b b'
            gpsDataInfo = namedtuple('gpsData', 'trueHeading speed latitude longitude altitude lock hardwareMode ss mm hh flags1 flags2 satellites filler')
            trueHeading, speed, latitude, longitude, altitude, lock, hardwareMode, ss, mm, hh, flags1, flags2, satellites, filler = struct.unpack(gpsDatadFormat, gps_field)
            gpsData = gpsDataInfo._make((trueHeading, speed, latitude, longitude, altitude, lock, hardwareMode, ss, mm, hh, flags1, flags2, satellites, filler))
            return gpsData
        except Exception as e:
            logger.exception(f"GPS parse error: {e}")
            return None
    
    def __wrap_gps(self: object, gpsData: tuple) -> bytes:
        try:
            gpsDatadFormat = '<d d d d d h b b b b b h 5s b b'
            gpsDataBytes = struct.pack(gpsDatadFormat, gpsData.trueHeading, gpsData.speed, gpsData.latitude, gpsData.longitude, gpsData.altitude, gpsData.lock, gpsData.hardwareMode, gpsData.ss, gpsData.mm, gpsData.hh, gpsData.flags1, gpsData.flags2, gpsData.satellites, gpsData.filler)
            return gpsDataBytes
        except Exception as e:
            logger.exception(f"GPS wrap error: {e}")
            return None

    def __parse_SmartDetector(self: object, smartDetectorData: bytes) -> tuple:
        try:
            smartDetectorFormat = '<i f f f h b f f'
            smartDetectorInfo = namedtuple('smartDetector', 'serialNumber signal dark ref status avg humid temp')
            serialNumber, signal, dark, ref, status, avg, humid, temp = struct.unpack(smartDetectorFormat, smartDetectorData)
            smartDetector = smartDetectorInfo._make((serialNumber, signal, dark, ref, status, avg, humid, temp))
            return smartDetector
        except Exception as e:
            logger.exception(f"Smart Detector parse error: {e}")
            return None
    
    def __wrap_SmartDetector(self: object, smartDetectorData: tuple) -> bytes:
        try:
            smartDetectorFormat = '<i f f f h b f f'
            smartDetectorBytes = struct.pack(smartDetectorFormat, smartDetectorData.serialNumber, smartDetectorData.signal, smartDetectorData.dark, smartDetectorData.ref, smartDetectorData.status, smartDetectorData.avg, smartDetectorData.humid, smartDetectorData.temp)
            return smartDetectorBytes
        except Exception as e:
            logger.exception(f"Smart Detector wrap error: {e}")
            return None
    
    def __checkSaturationError(self:object) -> list:
        # To identify Error codes in flags2
        errors = []
        if self.metadata.flags2 & flag1_vnir_saturation:
            errors.append("VNIR saturation")
        if self.metadata.flags2 & flag1_swir1_saturation:
            errors.append("SWIR1 saturation")
        if self.metadata.flags2 & flag1_swir2_saturation:
            errors.append("SWIR2 saturation")
        if self.metadata.flags2 & Tec1_alarm:
            errors.append("TEC1 Alarm")
        if self.metadata.flags2 & Tec2_alarm:
            errors.append("TEC2 Alarm")
        return errors

    def __getattr__(self, item):
        # TODO: Add more properties
        if item == 'reflectance':
            return self.get_reflectance()
        elif item == 'radiance':
            return self.get_radiance()
        elif item == 'white_reference':
            return self.get_white_reference()
        elif item == 'raw':
            return self.spectrumData
        elif item == 'ref':
            return self.reference
        else:
            return None
    
    def get_white_reference(self):
        return self.__normalise_spectrum(self.reference, self.metadata)

    @property
    def reflectance(self):
        if self.asdFileVersion >= 2:
            try:
                # Reflectance calculation, based on the spectrum data and reference data
                if self.metadata.referenceTime > 0 and self.metadata.dataType == 1:
                    reflectance = np.divide(self.__normalise_spectrum(self.spectrumData), self.__normalise_spectrum(self.referenceData, self.metadata), where=self.__normalise_spectrum(self.referenceData, self.metadata) != 0)
                else:
                    logger.info("Reflectance calculation error: Invalid spectral reflectance data")
                return reflectance
            except Exception as e:
                logger.exception(f"Reflectance calculation error: {e}")
                return None
        else:
            logger.info("Reflectance calculation error: Unsupported file version")
            return None
    
    @property
    def radiance(self):
        if self.asdFileVersion >= 7:
            try:
                #
                if self.calibrationHeader.calibrationNum >=3:
                    if self.calibrationSeriesABS is not None and self.calibrationSeriesLMP is not None and self.calibrationSeriesLMP is not None:
                        radiance = self.calibrationSeriesLMP * self.referenceData * self.spectrumData * self.metadata.intergrationTime_ms / (self.calibrationSeriesABS * 500 * 544 * self.calibrationSeriesBSE * np.pi)
                    elif self.calibrationSeriesBSE is not None and self.calibrationSeriesLMP is not None and self.calibrationSeriesFO is not None:
                        radiance = self.calibrationSeriesLMP * self.referenceData * self.spectrumData * self.metadata.intergrationTime_ms / (self.calibrationSeriesBSE  * 500 * 544 * self.calibrationSeriesFO * np.pi)
                    else:
                        logger.info("Radiance calculation error: Invalid spectral radiance data")
            except Exception as e:
                logger.exception(f"Radiance calculation error: {e}")
                return None
        return radiance

    def __normalise_spectrum(self: object, sepctra) -> np.array:
        # normalise the spectrum data, for VNIR and SWIR1, SWIR2, the data is normalised based on the integration time and gain
        sepctra = sepctra.copy()
        splice1_index = int(self.metadata.splice1_wavelength)
        splice2_index = int(self.metadata.splice2_wavelength)
        sepctra[:splice1_index] = sepctra[:splice1_index] / self.metadata.intergrationTime_ms
        sepctra[splice1_index:splice2_index] = sepctra[splice1_index:splice2_index] * self.metadata.swir1Gain / 2048
        sepctra[splice2_index:] = sepctra[splice2_index:] * self.metadata.swir2Gain / 2048
        return sepctra

    @property
    def reflectanceNoDeriv(self):
        return self.reflectance

    @property
    def reflectance1stDeriv(self):
        return np.gradient(self.reflectance)

    @property
    def reflectance2ndDeriv(self):
        return np.gradient(np.gradient(self.reflectance))

    @property
    def derivative(self):
        pass

    @property
    def absoluteReflectance(self):
        pass

    @property
    def log1r(self):
        pass

    @property
    def log1RNoDeriv(self):
        pass

    @property
    def log1R1stDeriv(self):
        pass

    @property
    def log1R2ndDeriv(self):
        pass

# DN
# Reflectance (Transmittance)
# Absolute Reflectance
# Radiometric Calculation
# Log 1/R (Log 1/T)
# 1st Derivative
# 2nd Derivative
# Parabolic Correction
# Splice Correction
# Lambda Integration
# Quantum lntensity
# Interpolate
# Statistics
# NEDL
# ASCll Export
# Import Ascii X,Y
# JCAMP-DX Export
# Bran+Luebbe
# Colorimetry..
# GPS Log
# Convex Hull
# Custom...

# define logger
logging.basicConfig(
    filename=os.path.join(os.path.dirname(__file__), '__testData__', 'asd_file_handle.log'),
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - Line: %(lineno)d'
)

logger = logging.getLogger(__name__)