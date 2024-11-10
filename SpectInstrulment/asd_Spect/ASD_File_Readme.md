#### ASD spectral file read, update, and write

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

#### Reference

"ASD File Format v8"

https://www.malvernpanalytical.com/en/learn/knowledge-center/user-manuals/asd-file-format-v8