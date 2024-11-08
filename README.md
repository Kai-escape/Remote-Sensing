The setting up of this repo is for primary methods in processing remote sensing and spectral data.

Including:

- ASD spectral file reading, modifying, and writing.

  | ASD File Structure             |                                                      |      |
  | ------------------------------ | ---------------------------------------------------- | ---- |
  | Spectrum File Header           | self.asdFileVersion; self.metadata                   |      |
  | Spectrum Data                  | self.spectrumData                                    |      |
  | Reference File Header          | self.referenceFileHeader                             |      |
  | Reference Data                 | self.referenceData                                   |      |
  | Classifier Data                | self.classifierData                                  |      |
  | Dependent Variables            | self.dependants                                      |      |
  | Calibration Header             | self.calibrationHeader                               |      |
  | Absolute/Base Calibration Data | self.calibrationSeriesABS; self.calibrationSeriesBSE |      |
  | Lamp Calibration Data          | self.calibrationSeriesLMP                            |      |
  | Fiber Optic Data               | self.calibrationSeriesFO                             |      |
  | Audit Log                      | self.auditLogHeader                                  |      |
  | Signature                      | self.signatureHeader                                 |      |

  
