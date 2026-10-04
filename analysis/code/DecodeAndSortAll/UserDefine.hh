// UserDefine.hh ---
//
// Description:
// Author: Hongyi Wu(吴鸿毅)
// Email: wuhongyi@qq.com
// Created: 五 10月 20 16:16:28 2017 (+0800)
// Last-Updated: 六 2月 17 13:53:03 2024 (+0800)
//           By: Hongyi Wu(吴鸿毅)
//     Update #: 55
// URL: http://wuhongyi.cn

// The user needs to modify the parameters in this file.

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

#ifndef _USERDEFINE_H_
#define _USERDEFINE_H_

#define WAVEFORM
// #define ENERGYSUM
// #define QDCSUM
// #define EXTERNALTS

#define Crate0
#define Crate1
// #define Crate2
// #define Crate3

#define ROOTFILEPATH "/home/ys/data_401/data/chx_20260622/decode_data/" // The path to generate the ROOT file
#define ROOTFILENAME "data"
#define TimesHist 3600 // second

#define TIMEBUFF 1000000000 // 1s
#define PROCESSBUFF 0.9     //(0,1.0]
//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

#define Crate0RAWFILEPATH "/home/ys/data_401/data/Ge/"                          // Path to the original binary
#define Crate0RAWFILENAME "data"                                                // The file name of the original file
#define Crate0num 5                                                             // Number of modules used in this crate
const unsigned short Crate0SamplingRate[Crate0num] = {250, 250, 250, 250, 500}; // Specify the sampling rate of each modules separately; 100/250/500 sampling rates; 0 to skip the module
const unsigned short Crate0Revision[Crate0num] = {15, 15, 15, 15, 15};          // RevD=13, RevF=15, RevH=17

#define Crate1RAWFILEPATH "/home/ys/data_401/data/CsI/"                                                  // Path to the original binary
#define Crate1RAWFILENAME "data"                                                                         // The file name of the original file
#define Crate1num 10                                                                                     // Number of modules used in this crate
const unsigned short Crate1SamplingRate[Crate1num] = {100, 100, 100, 100, 250, 100, 100, 250, 250, 100}; // Specify the sampling rate of each modules separately; 100/250/500 sampling rates; 0 to skip the module
const unsigned short Crate1Revision[Crate1num] = {15, 15, 15, 15, 15, 15, 15, 15, 15, 15};

#define Crate2RAWFILEPATH "/home/wuhongyi/data/"                                     // Path to the original binary
#define Crate2RAWFILENAME "data"                                                     // The file name of the original file
#define Crate2num 6                                                                  // Number of modules used in this crate
const unsigned short Crate2SamplingRate[Crate2num] = {100, 100, 100, 100, 100, 100}; // Specify the sampling rate of each modules separately; 100/250/500 sampling rates; 0 to skip the module
const unsigned short Crate2Revision[Crate2num] = {15, 15, 15, 15, 15, 15};

#define Crate3RAWFILEPATH "/home/wuhongyi/data/"                                     // Path to the original binary
#define Crate3RAWFILENAME "data"                                                     // The file name of the original file
#define Crate3num 6                                                                  // Number of modules used in this crate
const unsigned short Crate3SamplingRate[Crate3num] = {100, 100, 100, 100, 100, 100}; // Specify the sampling rate of each modules separately; 100/250/500 sampling rates; 0 to skip the module
const unsigned short Crate3Revision[Crate3num] = {15, 15, 15, 15, 15, 15};

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
// Example
// For example, there are 5 100MHz modules

// #define Crate0num 5
// const unsigned short Crate0SamplingRate[Crate0num] = {100,100,100,100,100};
// const unsigned short Crate0Revision[Crate0num] = {15,15,15,15,15};

#endif /* _USERDEFINE_H_ */
//
// UserDefine.hh ends here
