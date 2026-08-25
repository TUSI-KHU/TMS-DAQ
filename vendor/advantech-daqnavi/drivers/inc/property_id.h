#ifndef _DAQNAVI_PROPERTY_ID_H
#define _DAQNAVI_PROPERTY_ID_H

/*
* Property Attribute and Id
*/
typedef enum PropertyAttribute {
   ReadOnly = 0x0,
   Writable = 0x1,
   Modal    = 0x0,
   Nature   = 0x2,
} PropertyAttribute;

/*
* Property Value Type
*/
typedef enum PropertyType {
   PT_I8     = 0,
   PT_I16    = 1,
   PT_I32    = 2,
   PT_I64    = 3,
   PT_F32    = 4,
   PT_F64    = 5,
   PT_WSTR   = 6,
   PT_S_MI   = 7,

   PT_ARRAY  = 0x10000,
}PropertyType;


typedef enum PropertyId {
   /*-----------------------------------------------------------------
   * common property
   *-----------------------------------------------------------------*/
   CFG_Number,
   CFG_ComponentType,
   CFG_Description,
   CFG_Parent,
   CFG_ChildList,

   /*-----------------------------------------------------------------
   * component specified Property IDs -- group
   *-----------------------------------------------------------------*/
   CFG_DevicesNumber,
   CFG_DevicesHandle,

   /*-----------------------------------------------------------------
   * component specified Property IDs -- device
   *-----------------------------------------------------------------*/
   CFG_DeviceGroupNumber,
   CFG_DeviceProductID,
   CFG_DeviceBoardID,
   CFG_DeviceBoardVersion,
   CFG_DeviceDriverVersion,
   CFG_DeviceDllVersion,
   CFG_DeviceLocation,                       /* Reserved for later using */
   CFG_DeviceBaseAddresses,                  /* Reserved for later using */
   CFG_DeviceInterrupts,                     /* Reserved for later using */
   CFG_DeviceSupportedTerminalBoardTypes,    /* Reserved for later using */
   CFG_DeviceTerminalBoardType,              /* Reserved for later using */
   CFG_DeviceSupportedEvents,
   CFG_DeviceHotResetPreventable,            /* Reserved for later using */
   CFG_DeviceLoadingTimeInit,                /* Reserved for later using */
   CFG_DeviceWaitingForReconnect,
   CFG_DeviceWaitingForSleep,

   /*-----------------------------------------------------------------
   * component specified Property IDs -- AI, AO...
   *-----------------------------------------------------------------*/
   CFG_FeatureResolutionInBit,
   CFG_FeatureDataSize,
   CFG_FeatureDataMask,
   CFG_FeatureChannelNumberMax,
   CFG_FeatureChannelConnectionType,
   CFG_FeatureBurnDetectedReturnTypes,
   CFG_FeatureBurnoutDetectionChannels,
   CFG_FeatureOverallVrgType,
   CFG_FeatureVrgTypes,
   CFG_FeatureExtRefRange,
   CFG_FeatureExtRefAntiPolar,
   CFG_FeatureCjcChannels,
   CFG_FeatureChannelScanMethod,
   CFG_FeatureScanChannelStartBase,
   CFG_FeatureScanChannelCountBase,
   CFG_FeatureConvertClockSources,
   CFG_FeatureConvertClockRateRange,       /* Reserved for later using */
   CFG_FeatureScanClockSources,
   CFG_FeatureScanClockRateRange,         /* Reserved for later using */
   CFG_FeatureScanCountMax,               /* Reserved for later using */
   CFG_FeatureTriggersCount,
   CFG_FeatureTriggerSources,
   CFG_FeatureTriggerActions,
   CFG_FeatureTriggerDelayCountRange,
   CFG_FeatureTrigger1Sources,            /* Reserved for later using */
   CFG_FeatureTrigger1Actions,            /* Reserved for later using */
   CFG_FeatureTrigger1DelayCountRange,    /* Reserved for later using */

   CFG_ChannelCount,
   CFG_ConnectionTypeOfChannels,
   CFG_VrgTypeOfChannels,
   CFG_BurnDetectedReturnTypeOfChannels,
   CFG_BurnoutReturnValueOfChannels,
   CFG_ExtRefValueForUnipolar,         /* Reserved for later using */
   CFG_ExtRefValueForBipolar,          /* Reserved for later using */

   CFG_CjcChannel,
   CFG_CjcUpdateFrequency,             /* Reserved for later using */
   CFG_CjcValue,

   CFG_SectionDataCount,
   CFG_ConvertClockSource,
   CFG_ConvertClockRatePerChannel,
   CFG_ScanChannelStart,
   CFG_ScanChannelCount,
   CFG_ScanClockSource,                /* Reserved for later using */
   CFG_ScanClockRate,                  /* Reserved for later using */
   CFG_ScanCount,                      /* Reserved for later using */
   CFG_TriggerSource,
   CFG_TriggerSourceEdge,
   CFG_TriggerSourceLevel,
   CFG_TriggerDelayCount,
   CFG_TriggerAction,
   CFG_Trigger1Source,                 /* Reserved for later using */
   CFG_Trigger1SourceEdge,             /* Reserved for later using */
   CFG_Trigger1SourceLevel,            /* Reserved for later using */
   CFG_Trigger1DelayCount,             /* Reserved for later using */
   CFG_Trigger1Action,                 /* Reserved for later using */
   CFG_ParentSignalConnectionChannel,
   CFG_ParentCjcConnectionChannel,
   CFG_ParentControlPort,

   /*-----------------------------------------------------------------
   * component specified Property IDs -- DIO
   *-----------------------------------------------------------------*/
   CFG_FeaturePortsCount,
   CFG_FeaturePortsType,
   CFG_FeatureNoiseFilterOfChannels,
   CFG_FeatureNoiseFilterBlockTimeRange,     /* Reserved for later using */
   CFG_FeatureDiintTriggerEdges,
   CFG_FeatureDiintOfChannels,
   CFG_FeatureDiintGateOfChannels,
   CFG_FeatureDiCosintOfChannels,
   CFG_FeatureDiPmintOfChannels,
   CFG_FeatureSnapEventSources,
   CFG_FeatureDiSnapEventSources = CFG_FeatureSnapEventSources, /*For compatible*/
   CFG_FeatureDoFreezeSignalSources,            /* Reserved for later using */
   CFG_FeatureDoReflectWdtFeedIntervalRange,    /* Reserved for later using */

   CFG_FeatureDiPortScanMethod,                 /* Reserved for later using */
   CFG_FeatureDiConvertClockSources,            /* Reserved for later using */
   CFG_FeatureDiConvertClockRateRange,          /* Reserved for later using */
   CFG_FeatureDiScanClockSources,
   CFG_FeatureDiScanClockRateRange,             /* Reserved for later using */
   CFG_FeatureDiScanCountMax,
   CFG_FeatureDiTriggersCount,
   CFG_FeatureDiTriggerSources,
   CFG_FeatureDiTriggerActions,
   CFG_FeatureDiTriggerDelayCountRange,
   CFG_FeatureDiTrigger1Sources,
   CFG_FeatureDiTrigger1Actions,
   CFG_FeatureDiTrigger1DelayCountRange,

   CFG_FeatureDoPortScanMethod,                 /* Reserved for later using */
   CFG_FeatureDoConvertClockSources,            /* Reserved for later using */
   CFG_FeatureDoConvertClockRateRange,          /* Reserved for later using */
   CFG_FeatureDoScanClockSources,
   CFG_FeatureDoScanClockRateRange,             /* Reserved for later using */
   CFG_FeatureDoScanCountMax,
   CFG_FeatureDoTriggersCount,
   CFG_FeatureDoTriggerSources,
   CFG_FeatureDoTriggerActions,
   CFG_FeatureDoTriggerDelayCountRange,
   CFG_FeatureDoTrigger1Sources,
   CFG_FeatureDoTrigger1Actions,
   CFG_FeatureDoTrigger1DelayCountRange,

   CFG_DirectionOfPorts,
   CFG_DiDataMaskOfPorts,
   CFG_DoDataMaskOfPorts,

   CFG_NoiseFilterOverallBlockTime,              /* Reserved for later using */
   CFG_NoiseFilterEnabledChannels,
   CFG_DiintTriggerEdgeOfChannels,
   CFG_DiintGateEnabledChannels,
   CFG_DiCosintEnabledChannels,
   CFG_DiPmintEnabledChannels,
   CFG_DiPmintValueOfPorts,
   CFG_DoInitialStateOfPorts,                   /* Obsoleted, using 'CFG_DoPowerOnStateOfPorts' instead.*/
   CFG_DoPowerOnStateOfPorts = CFG_DoInitialStateOfPorts,
   CFG_DoFreezeEnabled,                         /* Reserved for later using */
   CFG_DoFreezeSignalState,                     /* Reserved for later using */
   CFG_DoReflectWdtFeedInterval,                /* Reserved for later using */
   CFG_DoReflectWdtLockValue,                   /* Reserved for later using */
   CFG_DiSectionDataCount,
   CFG_DiConvertClockSource,
   CFG_DiConvertClockRatePerPort,
   CFG_DiScanPortStart,
   CFG_DiScanPortCount,
   CFG_DiScanClockSource,
   CFG_DiScanClockRate,
   CFG_DiScanCount,
   CFG_DiTriggerAction,
   CFG_DiTriggerSource,
   CFG_DiTriggerSourceEdge,
   CFG_DiTriggerSourceLevel,                    /* Reserved for later using */
   CFG_DiTriggerDelayCount,
   CFG_DiTrigger1Action,
   CFG_DiTrigger1Source,
   CFG_DiTrigger1SourceEdge,
   CFG_DiTrigger1SourceLevel,                   /* Reserved for later using */
   CFG_DiTrigger1DelayCount,

   CFG_DoSectionDataCount,
   CFG_DoConvertClockSource,
   CFG_DoConvertClockRatePerPort,
   CFG_DoScanPortStart,
   CFG_DoScanPortCount,
   CFG_DoScanClockSource,
   CFG_DoScanClockRate,
   CFG_DoScanCount,
   CFG_DoTriggerAction,
   CFG_DoTriggerSource,
   CFG_DoTriggerSourceEdge,
   CFG_DoTriggerSourceLevel,                    /* Reserved for later using */
   CFG_DoTriggerDelayCount,
   CFG_DoTrigger1Action,
   CFG_DoTrigger1Source,
   CFG_DoTrigger1SourceEdge,
   CFG_DoTrigger1SourceLevel,                   /* Reserved for later using */
   CFG_DoTrigger1DelayCount,

   /*-----------------------------------------------------------------
   * component specified Property IDs -- Counter/Timer
   *-----------------------------------------------------------------*/
   /*common feature*/
   CFG_FeatureCapabilitiesOfCounter0 = 174,
   CFG_FeatureCapabilitiesOfCounter1,
   CFG_FeatureCapabilitiesOfCounter2,
   CFG_FeatureCapabilitiesOfCounter3,
   CFG_FeatureCapabilitiesOfCounter4,
   CFG_FeatureCapabilitiesOfCounter5,
   CFG_FeatureCapabilitiesOfCounter6,
   CFG_FeatureCapabilitiesOfCounter7,

   /*primal counter features*/
   CFG_FeatureChipOperationModes = 206,
   CFG_FeatureChipSignalCountingTypes,

   /*timer/pulse features*/
   CFG_FeatureTmrCascadeGroups = 211,

   /*frequency measurement features*/
   CFG_FeatureFmMethods = 213,

   /*Primal counter properties */
   CFG_ChipOperationModeOfCounters = 220,
   CFG_ChipSignalCountingTypeOfCounters,
   CFG_ChipLoadValueOfCounters,
   CFG_ChipHoldValueOfCounters,
   CFG_ChipOverCompareValueOfCounters,
   CFG_ChipUnderCompareValueOfCounters,
   CFG_ChipOverCompareEnabledCounters,
   CFG_ChipUnderCompareEnabledCounters,

   /*frequency measurement properties*/
   CFG_FmMethodOfCounters = 231,
   CFG_FmCollectionPeriodOfCounters,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v1.1
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_DevicePrivateRegionLength,
   CFG_SaiAutoConvertClockRate,
   CFG_SaiAutoConvertChannelStart,
   CFG_SaiAutoConvertChannelCount,
   CFG_ExtPauseSignalEnabled,
   CFG_ExtPauseSignalPolarity,
   CFG_OrderOfChannels,
   CFG_InitialStateOfChannels,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v1.2: new features & properties of counter
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   /*primal counter features*/
   CFG_FeatureChipClkSourceOfCounter0 = 242,
   CFG_FeatureChipClkSourceOfCounter1,
   CFG_FeatureChipClkSourceOfCounter2,
   CFG_FeatureChipClkSourceOfCounter3,
   CFG_FeatureChipClkSourceOfCounter4,
   CFG_FeatureChipClkSourceOfCounter5,
   CFG_FeatureChipClkSourceOfCounter6,
   CFG_FeatureChipClkSourceOfCounter7,

   CFG_FeatureChipGateSourceOfCounter0,
   CFG_FeatureChipGateSourceOfCounter1,
   CFG_FeatureChipGateSourceOfCounter2,
   CFG_FeatureChipGateSourceOfCounter3,
   CFG_FeatureChipGateSourceOfCounter4,
   CFG_FeatureChipGateSourceOfCounter5,
   CFG_FeatureChipGateSourceOfCounter6,
   CFG_FeatureChipGateSourceOfCounter7,

   CFG_FeatureChipValueRegisters,

   /*one-shot features*/
   CFG_FeatureOsClkSourceOfCounter0,
   CFG_FeatureOsClkSourceOfCounter1,
   CFG_FeatureOsClkSourceOfCounter2,
   CFG_FeatureOsClkSourceOfCounter3,
   CFG_FeatureOsClkSourceOfCounter4,
   CFG_FeatureOsClkSourceOfCounter5,
   CFG_FeatureOsClkSourceOfCounter6,
   CFG_FeatureOsClkSourceOfCounter7,

   CFG_FeatureOsGateSourceOfCounter0,
   CFG_FeatureOsGateSourceOfCounter1,
   CFG_FeatureOsGateSourceOfCounter2,
   CFG_FeatureOsGateSourceOfCounter3,
   CFG_FeatureOsGateSourceOfCounter4,
   CFG_FeatureOsGateSourceOfCounter5,
   CFG_FeatureOsGateSourceOfCounter6,
   CFG_FeatureOsGateSourceOfCounter7,

   /*Pulse width measurement features*/
   CFG_FeaturePiCascadeGroups,

   /*Primal counter properties */
   CFG_ChipClkSourceOfCounters = 279,
   CFG_ChipGateSourceOfCounters,

   /*one-shot properties*/
   CFG_OsClkSourceOfCounters,
   CFG_OsGateSourceOfCounters,
   CFG_OsDelayCountOfCounters,

   /*Timer pulse properties*/
   CFG_TmrFrequencyOfCounters,

   /*Pulse width modulation properties*/
   CFG_PoHiPeriodOfCounters,
   CFG_PoLoPeriodOfCounters,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v1.3: new features & properties of counter
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   /*Event counting features & properties*/
   CFG_FeatureEcClkPolarities,
   CFG_FeatureEcGatePolarities,
   CFG_FeatureEcGateControlOfCounters,

   CFG_EcClkPolarityOfCounters,
   CFG_EcGatePolarityOfCounters,
   CFG_EcGateEnabledOfCounters,

   /*one-shot features & properties*/
   CFG_FeatureOsClkPolarities,
   CFG_FeatureOsGatePolarities,
   CFG_FeatureOsOutSignals,

   CFG_OsClkPolarityOfCounters,
   CFG_OsGatePolarityOfCounters,
   CFG_OsOutSignalOfCounters,

   /*timer/pulse features & properties*/
   CFG_FeatureTmrGateControlOfCounters,
   CFG_FeatureTmrGatePolarities,
   CFG_FeatureTmrOutSignals,
   CFG_FeatureTmrFrequencyRange,

   CFG_TmrGateEnabledOfCounters,
   CFG_TmrGatePolarityOfCounters,
   CFG_TmrOutSignalOfCounters,

   /*Pulse width modulation features & properties*/
   CFG_FeaturePoGateControlOfCounters,
   CFG_FeaturePoGatePolarities,
   CFG_FeaturePoHiPeriodRange,
   CFG_FeaturePoLoPeriodRange,
   CFG_FeaturePoOutCountRange,

   CFG_PoGateEnabledOfCounters,
   CFG_PoGatePolarityOfCounters,
   CFG_PoOutCountOfCounters,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v1.4: new features & properties of counter
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureChipClkPolarities,
   CFG_FeatureChipGatePolarities,
   CFG_FeatureChipOutSignals,

   CFG_ChipClkPolarityOfCounters,
   CFG_ChipGatePolarityOfCounters,
   CFG_ChipOutSignalOfCounters,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v1.5: new features & properties of counter
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureOsDelayCountRange,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v1.6: new features & properties of counter
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureUdCountingTypes,
   CFG_FeatureUdInitialValues,
   CFG_UdCountingTypeOfCounters,
   CFG_UdInitialValueOfCounters,
   CFG_UdCountValueResetTimesByIndexs,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v1.7: new features & properties of AI
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureFilterTypes,
   CFG_FeatureFilterCutoffFreqRange,
   CFG_FeatureFilterCutoffFreq1Range,
   CFG_FilterTypeOfChannels,
   CFG_FilterCutoffFreqOfChannels,
   CFG_FilterCutoffFreq1OfChannels,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v1.8: new features & properties of DIO
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureDiOpenStatePorts,
   CFG_FeatureDiOpenStates,
   CFG_DiOpenStatesOfPorts,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v1.9: new features & properties of PWM counter
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeaturePoOutSignals,
   CFG_PoOutSignalOfCounters,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v2.0: new features & properties of AO/AI Trigger
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureTriggerSourceVRG,
   CFG_FeatureTriggerHysteresisIndexMax,
   CFG_FeatureTriggerHysteresisIndexStep,
   CFG_TriggerHysteresisIndex,

   CFG_FeatureTrigger1SourceVRG,
   CFG_FeatureTrigger1HysteresisIndexMax,
   CFG_FeatureTrigger1HysteresisIndexStep,
   CFG_Trigger1HysteresisIndex,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v2.1: new features & properties of AI
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureCouplingTypes,
   CFG_CouplingTypeOfChannels,
   CFG_FeatureImpedanceTypes,
   CFG_ImpedanceTypeOfChannels,
   CFG_RecordCycles,


   CFG_FeatureTriggerFilterTypes,
   CFG_FeatureTriggerFilterCutoffFreqRange,
   CFG_TriggerFilterType,
   CFG_Trigger1FilterType,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v2.2: new features & properties of AI
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_DiInversePorts,
   CFG_FeatureRetriggerable,
   CFG_ScanEnabledChannels,
   CFG_FeatureIepeTypes,
   CFG_IepeTypeOfChannels,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v2.3: new features & properties of AI
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_TriggerFilterCutoffFreq,
   CFG_Trigger1FilterCutoffFreq,
   CFG_FeatureTrigger2Sources,            /* Reserved for later using */
   CFG_FeatureTrigger2Actions,            /* Reserved for later using */
   CFG_FeatureTrigger2DelayCountRange,    /* Reserved for later using */
   CFG_FeatureTrigger2SourceVRG,
   CFG_FeatureTrigger2HysteresisIndexMax,
   CFG_FeatureTrigger2HysteresisIndexStep,

   CFG_Trigger2Source,                    /* Reserved for later using */
   CFG_Trigger2SourceEdge,                /* Reserved for later using */
   CFG_Trigger2SourceLevel,               /* Reserved for later using */
   CFG_Trigger2DelayCount,                /* Reserved for later using */
   CFG_Trigger2Action,                    /* Reserved for later using */
   CFG_Trigger2HysteresisIndex,
   CFG_Trigger2FilterType,
   CFG_Trigger2FilterCutoffFreq,

   CFG_FeatureTrigger3Sources,            /* Reserved for later using */
   CFG_FeatureTrigger3Actions,            /* Reserved for later using */
   CFG_FeatureTrigger3DelayCountRange,    /* Reserved for later using */
   CFG_FeatureTrigger3SourceVRG,
   CFG_FeatureTrigger3HysteresisIndexMax,
   CFG_FeatureTrigger3HysteresisIndexStep,

   CFG_Trigger3Source,                    /* Reserved for later using */
   CFG_Trigger3SourceEdge,                /* Reserved for later using */
   CFG_Trigger3SourceLevel,               /* Reserved for later using */
   CFG_Trigger3DelayCount,                /* Reserved for later using */
   CFG_Trigger3Action,                    /* Reserved for later using */
   CFG_Trigger3HysteresisIndex,
   CFG_Trigger3FilterType,
   CFG_Trigger3FilterCutoffFreq,

   CFG_FeatureTimestampResolution,
   CFG_FeatureTimeStampRes = CFG_FeatureTimestampResolution, /*for compatible*/

   CFG_RecordSectionLength,
   CFG_RecordSectionCount,

   CFG_FeatureConnectionTypes,
   CFG_FeatureOverallConnection,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v2.4: new features & properties of counter
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureMeasurementTimeoutRange,
   CFG_MeasurementTimeout,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v2.5: new features & properties of DIO
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureDoInitialStateDepository,
   CFG_DeviceLocateEnabled,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v2.6: new features & properties of AO
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_VrgExtRefValueOfChannels,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v2.7: new features & properties of AI
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureMeasureTypes,
   CFG_FeatureExcitingVoltageRange,
   CFG_FeatureBridgeResistances,
   CFG_SensorDescriptionOfChannels,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v2.8: new features & properties of buffered counter
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureEcSampleClkSourceOfCounter0,
   CFG_FeatureEcSampleClkSourceOfCounter1,
   CFG_FeatureEcSampleClkSourceOfCounter2,
   CFG_FeatureEcSampleClkSourceOfCounter3,
   CFG_FeatureEcSampleClkSourceOfCounter4,
   CFG_FeatureEcSampleClkSourceOfCounter5,
   CFG_FeatureEcSampleClkSourceOfCounter6,
   CFG_FeatureEcSampleClkSourceOfCounter7,

   CFG_FeaturePiSampleClkSourceOfCounter0,
   CFG_FeaturePiSampleClkSourceOfCounter1,
   CFG_FeaturePiSampleClkSourceOfCounter2,
   CFG_FeaturePiSampleClkSourceOfCounter3,
   CFG_FeaturePiSampleClkSourceOfCounter4,
   CFG_FeaturePiSampleClkSourceOfCounter5,
   CFG_FeaturePiSampleClkSourceOfCounter6,
   CFG_FeaturePiSampleClkSourceOfCounter7,

   CFG_FeaturePoSampleClkSourceOfCounter0,
   CFG_FeaturePoSampleClkSourceOfCounter1,
   CFG_FeaturePoSampleClkSourceOfCounter2,
   CFG_FeaturePoSampleClkSourceOfCounter3,
   CFG_FeaturePoSampleClkSourceOfCounter4,
   CFG_FeaturePoSampleClkSourceOfCounter5,
   CFG_FeaturePoSampleClkSourceOfCounter6,
   CFG_FeaturePoSampleClkSourceOfCounter7,

   CFG_FeatureUdSampleClkSourceOfCounter0,
   CFG_FeatureUdSampleClkSourceOfCounter1,
   CFG_FeatureUdSampleClkSourceOfCounter2,
   CFG_FeatureUdSampleClkSourceOfCounter3,
   CFG_FeatureUdSampleClkSourceOfCounter4,
   CFG_FeatureUdSampleClkSourceOfCounter5,
   CFG_FeatureUdSampleClkSourceOfCounter6,
   CFG_FeatureUdSampleClkSourceOfCounter7,

   CFG_SamplingClockSources,
   CFG_RecordSectionLengthes,
   CFG_RecordSectionCounts,
   CFG_BufferedModeOfCounters,

   CFG_TriggerSources,
   CFG_TriggerSourcesLevel,
   CFG_TriggerSourcesEdge,
   CFG_TriggerSourcesHysteresisIndex,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v2.9: new features & properties of Edge Separation
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureEsTriggerEdges,
   CFG_EsStartCountingEdgeOfCounters,
   CFG_EsStopCountingEdgeOfCounters,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v3.0: new features & properties of device offline watchdog
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_DeviceWdtDoEnabled,
   CFG_DeviceWdtDoPattern,
   CFG_DeviceWdtTime,
   CFG_DeviceWdtFlag,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v3.1: new features of up-down counter
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureUdCountValueResetTimes,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v3.2: new features & properties of DO Circuit Setting
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureDoCircuitSelectableTypes,
   CFG_DoCircuitTypeOfPorts,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v3.3: new features & properties of Event counter
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureEcClkSourceOfCounter0,
   CFG_FeatureEcClkSourceOfCounter1,
   CFG_FeatureEcClkSourceOfCounter2,
   CFG_FeatureEcClkSourceOfCounter3,
   CFG_FeatureEcClkSourceOfCounter4,
   CFG_FeatureEcClkSourceOfCounter5,
   CFG_FeatureEcClkSourceOfCounter6,
   CFG_FeatureEcClkSourceOfCounter7,

   CFG_EcClkSourceOfCounters,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v3.4: new features & properties of Buffered DIO
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureDiTriggerHysteresisIndexMax,
   CFG_FeatureDiTrigger1HysteresisIndexMax,
   CFG_FeatureDiTriggerHysteresisIndexStep,
   CFG_FeatureDiTrigger1HysteresisIndexStep,

   CFG_FeatureDoTriggerHysteresisIndexMax,
   CFG_FeatureDoTrigger1HysteresisIndexMax,
   CFG_FeatureDoTriggerHysteresisIndexStep,
   CFG_FeatureDoTrigger1HysteresisIndexStep,

   CFG_DiTriggerHysteresisIndex,
   CFG_DiTrigger1HysteresisIndex,

   CFG_DoTriggerHysteresisIndex,
   CFG_DoTrigger1HysteresisIndex,

   CFG_DiScanEnabledPort,
   CFG_DiPortSectionLength,
   CFG_DiPortSectionCount,
   CFG_DiPortCycles,

   CFG_DoScanEnabledPort,
   CFG_DoPortSectionLength,
   CFG_DoPortSectionCount,
   CFG_DoPortCycles,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v3.5: new features & properties of AI sendor open/short
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_BurnShortReturnValueOfChannels,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v3.6: new features & properties of Counter continue compare
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureCcpGateControlOfCounters,
   CFG_FeatureCcpGatePolarities,
   CFG_FeatureCcpOutSignals,
   CFG_FeatureCcpHiPeriodRange,
   CFG_FeatureCcpLoPeriodRange,
   CFG_FeatureCcpOutCountRange,

   CFG_CcpGateEnabledOfCounters,
   CFG_CcpGatePolarityOfCounters,
   CFG_CcpOutSignalOfCounters,
   CFG_CcpHiPeriodOfCounters,
   CFG_CcpLoPeriodOfCounters,
   CFG_CcpOutCountOfCounters,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v3.7: new features & properties for iDAQ-Fusion device
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_DeviceSupportedFusionTypes,

   CFG_FeatureDeviceRtProgrammableSignals,
   CFG_DeviceRtProgrammableSignalDirections,

   CFG_FeatureDeviceRtSignalEndpoints,

   CFG_FeatureDeviceRtEndpoint0Sources,
   CFG_FeatureDeviceRtEndpoint1Sources,
   CFG_FeatureDeviceRtEndpoint2Sources,
   CFG_FeatureDeviceRtEndpoint3Sources,
   CFG_FeatureDeviceRtEndpoint4Sources,
   CFG_FeatureDeviceRtEndpoint5Sources,
   CFG_FeatureDeviceRtEndpoint6Sources,
   CFG_FeatureDeviceRtEndpoint7Sources,
   CFG_FeatureDeviceRtEndpoint8Sources,
   CFG_FeatureDeviceRtEndpoint9Sources,
   CFG_FeatureDeviceRtEndpoint10Sources,
   CFG_FeatureDeviceRtEndpoint11Sources,
   CFG_FeatureDeviceRtEndpoint12Sources,
   CFG_FeatureDeviceRtEndpoint13Sources,
   CFG_FeatureDeviceRtEndpoint14Sources,
   CFG_FeatureDeviceRtEndpoint15Sources,

   CFG_DeviceRtEndpoint0Source,
   CFG_DeviceRtEndpoint1Source,
   CFG_DeviceRtEndpoint2Source,
   CFG_DeviceRtEndpoint3Source,
   CFG_DeviceRtEndpoint4Source,
   CFG_DeviceRtEndpoint5Source,
   CFG_DeviceRtEndpoint6Source,
   CFG_DeviceRtEndpoint7Source,
   CFG_DeviceRtEndpoint8Source,
   CFG_DeviceRtEndpoint9Source,
   CFG_DeviceRtEndpoint10Source,
   CFG_DeviceRtEndpoint11Source,
   CFG_DeviceRtEndpoint12Source,
   CFG_DeviceRtEndpoint13Source,
   CFG_DeviceRtEndpoint14Source,
   CFG_DeviceRtEndpoint15Source,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v3.8: new features & properties for PCIe-1882 counter
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeaturePoTriggersCount,
   CFG_FeaturePoTriggerSourcesOfCounter0,
	CFG_FeaturePoTriggerSourcesOfCounter1,
	CFG_FeaturePoTriggerSourcesOfCounter2,
	CFG_FeaturePoTriggerSourcesOfCounter3,
	CFG_FeaturePoTriggerSourcesOfCounter4,
	CFG_FeaturePoTriggerSourcesOfCounter5,
	CFG_FeaturePoTriggerSourcesOfCounter6,
	CFG_FeaturePoTriggerSourcesOfCounter7,
   CFG_FeaturePoTriggerDelayCountRange,
   CFG_FeaturePoTriggerActions,

   CFG_PoTriggerSourceOfCounters,
   CFG_PoTriggerEdgeOfCounters,
   CFG_PoTriggerDelayCountOfCounters,
   CFG_PoTriggerActionOfCounters,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v3.9: new features & properties for USB-4751-B counter
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FmTimeupOfCounters,
   CFG_PiTimeupOfCounters,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v4.0: new features & properties for Absolute counter(AMAX-5082)
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureAbsCodingTypes,
   CFG_FeatureAbsBaudrates,
   CFG_FeatureAbsErrorDetectedReturnTypes,
   CFG_FeatureAbsOutSignals,
   CFG_FeatureAbsLatchSignalEdges,

   CFG_AbsCodingTypeOfCounters,
   CFG_AbsBaudrateOfCounters,
   CFG_AbsErrorDetectedReturnTypeOfCounters,
   CFG_AbsErrorReturnValueOfCounters,
   CFG_AbsLatchSignalEdgeOfCounters,
   CFG_AbsCompareValue0OfCounters,
   CFG_AbsCompareValue1OfCounters,
   CFG_AbsCompare0EnableOfCounters,
   CFG_AbsCompare1EnableOfCounters,
   CFG_AbsOutSignalsOfCounters,
   CFG_AbsLatchedValueofCounters,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v4.1: new features & properties for iDAQ
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureDeviceSignalNoiseFilterBlockTimeRange,
   CFG_DeviceSignalOverallNoiseFilterBlockTime,

   CFG_FeaturePoTriggerEdges,
   CFG_FeatureCcpDataCtrlCodeSupported,
   CFG_CcpDataCtrlCodeEnabled,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v4.2 Buffered AI Down-Sampling
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureDownsamplingMethods,
   CFG_DownsamplingMethodOfChannels,
   CFG_DownsamplingCountOfChannels,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v4.3 new features & properties for Buffered Counter
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureSamplingClockRateRange,
   CFG_SamplingClockRate,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v4.4 new features & properties for iDAQ Chassis LED control
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_DeviceLEDConfig,
   CFG_DeviceLEDOutput,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx 
   // v4.5 new properties for supporting GPU(CUDA) 
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx 
   CFG_DtcTransType,
   CFG_ConvDataType,
   CFG_ConvPermutation,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx 
   // v4.6 new properties for supporting DI/O Power ON Settings
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx 
   CFG_FeatureDioPowerOnDirDepository,
   CFG_DioPowerOnDirOfPorts,

   //
   // <<<---- end of public property ID <<<----
   //

   //////////////////////////////////////////////////////////////////////////
   //                                                                      //
   // INTERNAL USED ONLY property ID starts from here.                     //
   //                                                                      //
   // CAUTION: public property must be inserted before this line.          //
   //                                                                      //
   //////////////////////////////////////////////////////////////////////////
   CFG_FeatureInternalClockSourceOfCounters = 0x60000000,
   CFG_InternalClockSourceOfCounters,
   CFG_FeaturePiClkSourceOfCounters,
   CFG_PiClkSourceOfCounters,
   CFG_DoConfig,
   CFG_TimeBase,
   CFG_EnableFifo,
   CFG_XferMode,
   CFG_AIRangeJumper,
   CFG_Jumper5L,
   CFG_Jumper8,
   CFG_InternalGateSourceOfCounters,
   CFG_BaseClockRate,
   CFG_FeatureSprtEventSources,
   CFG_SimulatorDataFileString,
   CFG_EventPriorityBoost,
} PropertyId;


#endif
