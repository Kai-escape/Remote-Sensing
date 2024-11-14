#### ASD spectral file read, update, and write



##### Version 1 (asdFileHandle_1.py)

| ASD File Structure             | class ASDFile()                                        |
| ------------------------------ | ---------------------------------------------------- |
| Spectrum File Header           | self.asdFileVersion; self.metadata                   |
| Spectrum Data                  | self.spectrumData                                    |
| Reference File Header          | self.referenceFileHeader                             |
| Reference Data                 | self.referenceData                                   |
| Classifier Data                | self.classifierData                                  |
| Dependent Variables            | self.dependants                                      |
| Calibration Header             | self.calibrationHeader                               |
| Absolute/Base Calibration Data | self.calibrationSeriesABS; self.calibrationSeriesBSE |
| Lamp Calibration Data          | self.calibrationSeriesLMP                            |
| Fiber Optic Data               | self.calibrationSeriesFO                             |
| Audit Log                      | self.auditLog                                        |
| Signature                      | self.signature                                       |

##### Upcoming Version 2 (asdFileHandle_2.py)

All data is wrapped in Python `@dataclass` to support validation and new features for QA/QC check of spectral database building.

##### Reference

"ASD File Format v8"

https://www.malvernpanalytical.com/en/learn/knowledge-center/user-manuals/asd-file-format-v8