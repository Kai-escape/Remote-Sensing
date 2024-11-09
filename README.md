The setting up of this repo is for primary methods in processing spectral and remote sensing data.

Including:

- ASD spectral file reading, modifying, and writing.

  | ASD File Structure             | ASDFile class                                       |
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

  
