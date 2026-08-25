Advantech DAQNavi Linux Drivers
Date: 02/2026

The Readme file contains the following section:


1. Installation
2. Supported distribution
3. Driver note
4. Hardware Support for Linux
5. System requirements
6. What's new 


1. Installation
    1-1. Before installation
        (1) Please make sure that the kernel source and the relevant compilation tools are installed.
            Notes: "gcc", "autoconf", "libtool", "pkg-config", "pkgconf", "build-essential".
        (2) Please make sure that the source of system software is up-to-date.
        (3) Disable comedi driver, please refer to Driver note.
        (4) Uninstall the adsapi32 driver, please refer to Driver note.
        (5) Copy the driver compression package to home folder and decompression it.
        (6) For EtherCAT devices, Please make sure that the "ethtool" and "net-tools" are installed.

    1-2. Common installation steps 
        Regardless of the type of device you're installing, you need to perform the following steps.
        (1) Get root permissions and run executable file. (example: "./linux_driver_source_4.0.0.0_64bit.run")
            Notes: There are three parameters for silent installation, the first parameter means silent installation;
            the second means installer or uninstaller; the last means which driver to be installed, it can be null when the second parameter is "uninstall".
            (example: "./linux_driver_source_4.0.0.0_64bit.run silent install pcie1840")
        (2) Click "Install Linux Drivers and SDK".
        (3) Select the path to install SDK. Strongly recommend using the default path.
        (4) Select the driver you would like to install.
        (5) Wait for the installation to complete and click “Finish” 
        (6) Restart your system.(recommended)   

        Excluding ISA and EtherCAT devices, the SDK and driver have been successfully installed through the aforementioned steps. 
        The drivers will load automatically upon system reboot.
        For ISA device, see 1-3.
        For EtherCAT devices, see 1-4.

    1-3. Additional steps for ISA device    
        If the DAQ device is ISA device, such as PCM-3718, PCM-3725, PCM3730, you must perform the following additional steps.
        (1) Set jumper and switch to config the io port address, irq, dma of PCM-3718HO. (example: PCM-3718HO)
        (2) Config the resource by isa_tools and make sure the resource is consistent with the hardware configuration. (example: cd tools/isa_tool; ./isa_tool -a -n bio3718 -m pcm3718ho -p 0x200 -i 3 -d 1)

    1-4. Additional steps for EtherCAT device    
        If the DAQ device is EtherCAT device, such as Amax-5000 series and Wise-5000 series, you must perform the following additional steps.
        (1) Run /opt/advantech/tools/amax5k-filter-auto-load-enable.sh 
        (2) Please select the Ethernet interface to which the Amax EtherCAT driver will be bound.
        (3) Restart your system.(recommended)

    1-5. Verification         
        After the installation is complete, you can verify if the devices have been detected by executing "/opt/advantech/tools/dndev".
        Use "./dndev /?" to obtain more usage information for the tool.

    1-6. Uninstallation
        (1) Get root permissions and run executable file. (example: "./linux_driver_source_4.0.0.0_64bit.run")
            Notes: There are three parameters for silent installation, the first parameter means silent installation;
            the second means installer or uninstaller; the last means which driver to be installed, it can be null when the second parameter is "uninstall".
            (example: "./linux_driver_source_4.0.0.0_64bit.run silent uninstall")
        (2) Click “Remove Products”.
        (3) Restart your system.


2. Supported distribution
 ------------------------------------------ -------------- ----------------
|             Distribution                 |     Kernel version            |
 ------------------------------------------ -------------------------------
|  Ubuntu 22.04                            |         6.8.0                 |
 ------------------------------------------ -------------------------------
|  Redhat Enterprise Linux Server 9.3      |         5.14.0                |
 ------------------------------------------ -------------------------------
|  OpenSUSE 15.5                           |         5.14.21               |
 ------------------------------------------ -------------------------------
|  Debian 12.5                             |         6.1.0                 |
 ------------------------------------------ -------------------------------
|  CentOS 8.5                              |         4.18.0                |
 ------------------------------------------ -------------------------------

3. Driver note
Please disable comedi driver, because this driver will conflict with some of DAQNavi's driver.
----------------------------------------------
(1) Please get root permissions.
(2) Open /etc/modprobe.d/blacklist.conf file.
(3) Add "blacklist comedi" "blacklist adv_pci_dio" "blacklist adv_pci1710" at end of the file.
(4) reboot system.

Please uninstall adsapi32 driver, because this driver will conflict with some of DAQNavi's driver.
----------------------------------------------
If needed to uninstall adsapi32 driver, please refer to their own uninstall instructions.

User manual
----------------------------------------------
Linux User Interface Manaul has been included in the development plan.If needed,please refer to
\Documents\DAQNavi_User_Interface_Manual_EN\DAQNavi_User_Interface.chm. You can install gnochm to browse
chm manual in linux OS.


4. Hardware Support

Advantech DAQNavi Linux Drivers supports the following devices:
--------------------------------------------------------------------------------------
| Device Name                      |  Driver(Folder) Name                            |
--------------------------------------------------------------------------------------
| PCI-1706U                        |  pci1706                                        |
| ECUP-1706                        |  ecup1706                                       |
| PCI-1710/L/HG/HGL                |  pci1710                                        |
| PCI-1711/U/L/UL                  |  pci1711                                        |
| PCI-1712-B                       |  pci1712b                                       |
| PCI-1713U                        |  pci1713                                        |
| PCI-1714U/UL                     |  pci1714_pcie1744                               |
| PCI-1715U                        |  pci1715                                        |
| PCI-1715U-B                      |  pci1715b                                       |
| PCI-1716/L                       |  pci1716                                        |
| PCI-1716-B                       |  pci1716b                                       |
| PCI-1718HDU/HGU                  |  pci1718                                        |
|------------------------------------------------------------------------------------|
| PCI-1720U                        |  pci1720                                        |
| PCI-1721                         |  pci1721                                        |
| PCI-1721-B                       |  pci1721b                                       |
| PCI-1723                         |  pci1723                                        |
| PCI-1724U                        |  pci1724                                        |
| PCI-1727U                        |  pci1727                                        |
|------------------------------------------------------------------------------------|
| PCI-1730/U                       |  pci1730_pcm3730i                               |
| PCI-1733                         |  pci1733                                        |
| PCI-1734                         |  pci1734                                        |
| PCI-1737                         |  pci1737_pci1739                                |
| PCI-1739                         |  pci1737_pci1739                                |
|------------------------------------------------------------------------------------|
| PCI-1747U                        |  pci1747                                        |
|------------------------------------------------------------------------------------|
| PCI-1750                         |  pci1750                                        |
| PCI-1751                         |  pci1751                                        |
| PCI-1752U/USO                    |  pci1752                                        |
| PCI-1753                         |  pci1753_mic3753_pcm3753i                       |
| PCI-1754                         |  pci1754                                        |
| PCI-1756                         |  pci1756                                        |
| PCI-1757UP                       |  pci1757                                        |
| PCI-1758 series                  |  pci1758                                        |
|------------------------------------------------------------------------------------|
| PCI-1760                         |  pci1760                                        |
| PCI-1761                         |  pci1761_pcm3761i                               |
| PCI-1762                         |  pci1762                                        |
|------------------------------------------------------------------------------------|
| PCI-1780                         |  pci1780                                        |
| PCI-1780-B                       |  pci1780b                                       |
| PCI-1784                         |  pci1784                                        |
| PCI-1784-B                       |  pci1784b                                       |
|------------------------------------------------------------------------------------|
| PCIE-1730                        |  pcigpdc                                        |
| PCIE-1730H                       |  pcigpdc                                        |
| PCIE-1730H-B                     |  pcigpdcx                                       |
| PCIE-1744                        |  pci1714_pcie1744                               |
| PCIE-1747                        |  pcie1747                                       |
| PCIE-1750U                       |  pcigpdcx                                       |
| PCIE-1750UH                      |  pcigpdcx                                       |
| PCIE-1751-B                      |  pcigpdcb                                       |
| PCIE-1752                        |  pcigpdc                                        |
| PCIE-1753                        |  pcigpdc                                        |
| PCIE-1753-B                      |  pcigpdcb                                       |
| PCIE-1756                        |  pcigpdc                                        |
| PCIE-1756H                       |  pcigpdcx                                       |
| PCIE-1756H-B                     |  pcigpdcx                                       |
| PCIE-1758DI/DO/DIO               |  pcigpdcx                                       |
| PCIE-1760                        |  pcigpdc                                        |
| PCIE-1760-B                      |  pcigpdcb                                       |
| PCIE-1761H                       |  pcigpdcx                                       |
| PCIE-1762H                       |  pcigpdcx                                       |
| PCIE-1763AH/DH                   |  pcigpdcx                                       |
| PCIE-1765                        |  pcigpdc                                        |
|------------------------------------------------------------------------------------|
| PCIE-1802                        |  pcie1802                                       |
| PCIE-1803                        |  pcie1803                                       |
| PCIE-1805                        |  pcie1805                                       |
| PCIE-1810                        |  pcie1810                                       |
| PCIE-1810-B                      |  pcie1810b                                      |
| PCIE-1812                        |  pcie1812                                       |
| PCIE-1812-B                      |  pcie1812b                                      |
| PCIE-1816                        |  pcigpscmf                                      |
| PCIE-1816-B                      |  pcie1816b                                      |
| PCIE-1824                        |  pcie1824                                       |
| PCIE-1840                        |  pcie1840                                       |
| PCIE-1841                        |  pcie1841                                       |
| PCIE-1842/L/MIOE-3842/MIOE-3844  |  pcie1842                                       |
| PCIE-1843/L                      |  pcie1842                                       |
| PCIE-1882                        |  pcie1882                                       |
| PCIE-1884                        |  pcie1884                                       |
|------------------------------------------------------------------------------------|
| MIC-1810                         |  pcie1810                                       |
| MIC-1816                         |  pcigpscmf                                      |
|------------------------------------------------------------------------------------|
| PCM-3718                         |  pcm3718                                        |
| PCM-3725                         |  pcm3725                                        |
| PCM-3730                         |  pcm3730                                        |
| PCM-3761I                        |  pci1761_pcm3761i                               |
| PCM-3753I                        |  pci1753_mic3753_pcm3753i                       |
| PCM-3810I                        |  pcm3810i                                       |
| PCM-2731                         |  pcmgpdc                                        |
| PCM-27D24DI                      |  pcmgpdc                                        |
| PCM-37D24DI                      |  pcmgpdc                                        |
|------------------------------------------------------------------------------------|
| USB-4702                         |  usb4702_usb4704                                |
| USB-4704                         |  usb4702_usb4704                                |
| USB-4711A                        |  usb4711a                                       |
| USB-4711-B                       |  usb4711b_4716b                                 |
| USB-4716                         |  usb4716                                        |
| USB-4716-B                       |  usb4711b_4716b                                 |
| USB-4718                         |  usb4718                                        |
| USB-4750                         |  usb4750                                        |
| USB-4750-C                       |  usb4750c                                       |
| USB-4751                         |  usb4751                                        |
| USB-4751/L-B                     |  usb4751b_4751lb                                |
| USB-4761                         |  usb4761                                        |
| USB-4761-B                       |  usb4761b                                       |
|------------------------------------------------------------------------------------|
| USB-5801                         |  usb5801                                        |
| USB-5817                         |  usb5817                                        |
| USB-5820                         |  usb5820                                        |
| USB-5830                         |  usb5800dio                                     |
| USB-5850                         |  usb5800dio                                     |
| USB-5855                         |  usb5800dio                                     |
| USB-5856                         |  usb5800dio                                     |
| USB-5860                         |  usb5800dio                                     |
| USB-5862                         |  usb5800dio                                     |
|------------------------------------------------------------------------------------|
| iDAQ-731                         |  usbidaq                                        |
| iDAQ-751                         |  usbidaq                                        |
| iDAQ-763D                        |  usbidaq                                        |
| iDAQ-784                         |  usbidaq                                        |
| iDAQ-801                         |  usbidaq                                        |
| iDAQ-815                         |  usbidaq                                        |
| iDAQ-817                         |  usbidaq                                        |
| iDAQ-821                         |  usbidaq                                        |
| iDAQ-841                         |  usbidaq                                        |
| iDAQ-868                         |  usbidaq                                        |
| iDAQ-871                         |  usbidaq                                        |
| iDAQ-873                         |  usbidaq                                        |
| iDAQ-Fusion                      |  usbidaq                                        |
|------------------------------------------------------------------------------------|
| MIC-3714                         |  pci1714_pcie1744                               |
| MIC-3716                         |  pci1716                                        |
| MIC-3723                         |  pci1723                                        |
| MIC-3753                         |  pci1753_mic3753_pcm3753i                       |
| MIC-3756                         |  pci1756                                        |
| MOS-1110Y-01                     |  pcmgpdc                                        |
|----------------------------------|-------------------------------------------------|
| AMAX-5000 series module          |  ia_ethercat                                    |
| WISE-5000 series module          |  ia_ethercat                                    |
--------------------------------------------------------------------------------------

5. System requirements

Advantech DAQNavi Linux Drivers system requirements:
--------------------------------------------------------------------------------
1. Kernel version must be higher than 2.6.18.
2. The glibc version must be higner than 2.11

6. What's new
1) New Feature: Advantech DKMS Support
       A new feature DKMS(Dynamic Kernel Module Support) is introduced into 
   Advantech DAQNavi Driver since 2024-12-20.
       This feature will help user updating(re-build & re-install) 
   the installed daq drivers automatically whenever the linux kernel is updated.
       This feature will be enabled automatically when user install DAQ drivers, 
   in GUI mode or silent mode, the user need do nothing for this feature.
2)
DAQNavi_SDK:
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.1.15.0   |  2022-11-24  | 1. Bug fix                                                           | libbiodaq.so: V4.1.15.0  | 
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.4.0    |  2021-06-28  | 1. Added: Python class library and example                           | libbiodaq.so: V4.1.8.6   | 
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.1.0    |  2019-03-22  | 1. Modified:Bug 15709：C++ DI_Interrupt ca not work normally and pop | libiodaq.so: V4.0.1.0    |
|               |              |    messages Segmentation fault(core dumped) when finished.           |                          |
|               |              | 2. Modified:Bug 12946: PCIE-1840 DN4 Linux driver developmen.        |                          |
|               |              | 3. Modified:Bug 14747: PCM-2731,MOS-1110Y-01 Linux driver development|                          |
|               |              | 4. Modified:Bug 16123: Package run failed with silent.               |                          |
|               |              | 5. Modified:Bug 14944: ANSI_C build error in ubuntu16.04.            |                          | 
|               |              | 6. Modified:Bug 14591: EventCounter count error in linux system.     |                          |
|               |              | 7. Modified:Bug 16143: Qt example build error in linux.              |                          |
|               |              | 8. Modified:Bug 16295: InstantAI return tomeout in ubuntu18.04.      |                          |
|               |              | 9. Modified:Bug 16286: InstantAI return tomeout in ubuntu18.04.      |                          |
|               |              | 10.Modified:Bug 11154: AO output rate shouldn't limit.(from bugzilla)|                          |
|               |              | 11.Modified:Bug 15982: Uninstall function is error.                  |                          |
|               |              | 12.Modified:Bug 16021: Daqnavi_daemon Service can not copy correctly.|                          |
|               |              | 13.Modified:Bug 14662: Deploy driver source code and request from    |                          |
|               |              |    to /opt/advantech.                                                |                          | 
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1. Update to DN4 SDK.                                                | libiodaq.so: V4.0.0.0    |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1. Modified:fix bug: compiling error under arm-linux                 | libiodaq.so: V3.1.16.0   |
|               |              | 2. Modified:fix bug: updated for Linux DN4 SDK.                      |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1. Modified:Bug 10000: compiling error on linux kernel 4.11.         | libiodaq.so: V3.1.15.0   |
|               |              | 2. Modified:fix bug: Add coupling type and IEPE type ANSI-C API      |                          |
|               |              | 3. Modified:fix bug: compiling error for cross-compiling: amd64      |                          |
|               |              | 4. Modified:Bug 10657.Modify the return value of                     |                          |
|               |              |    AdxGetValueRangeInformation                                       |                          |
|               |              | 5. Modified:Bug 10216. Missing some AI channel methods,              |                          |
|               |              |    such as IEPE and CouplingType.                                    |                          |
|               |              | 6. Modified:Bug 10955: compiling error on kernel v4.13               |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.8.0    |  2016-03-29  | 1. Modified:fix bug: Compile error in linux environment              | libiodaq.so: V3.1.14.0   |
--------------- -------------- ---------------------------------------------------------------------- ---------------------------
|    3.2.7.0    |  2015-09-01  | 1. Modified:Bug 17996.Add parameter verify for method: di/do         | libiodaq.so: V3.1.13.0   |
|               |              |    read/write bit                                                    |                          |
|               |              | 2. Added: ModeWriteShared.                                           |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.6.0    |  2015-07-15  | 1. Modified:Bug 17206.add noise filter setting:blocking time.        | libiodaq.so: V3.1.12.0   |
|               |              | 2. Modified:Bug 17485.Add CouplingType and IEPE to AiFeature and     |                          |
|               |              |     AIChannel                                                        |                          |
|               |              | 3. Modified:Bug 17509.Add property id from trigger                   |                          |
|               |              | 3. Modified:Bug 17744.Modify Coupling&IEPE Property's definition     |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1. Modified:Bug 16823.fix fileno reveal.                             | libiodaq.so: V3.1.11.0   |
|               |              | 2. Modified:Bug 16984.modify DIO programmable method for devices     |                          |
|               |              |     which DIO ports have different programmable feature              |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.4.0    |  2015-01-15  | 1. added device module property/method.(Normal)                      | libiodaq.so: V3.1.10.0   |
|               |              | 2. Modified:Modify return ErrorCode when property CountingType is set|                          |
|               |              |    to invalid value                                                  |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.2.0    |  2014-06-15  | 1. Add: Dio read and write bit port function.(Normal)                | libiodaq.so: V3.1.9.0    |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | 1. Add: CSCL APIs for ANSI-C.(Normal)                                |                          |
|               |              | 2. Add: "ErrorFuncConflictWithBfdAi" and                             |                          |
|               |              |    "ErrorVrgNotAvailableInSeMode" Error code.(Normal)                | libiodaq.so: V3.1.8.0    |
|               |              | 3. Add: Add double trigger example.(Normal)                          |                          |
|               |              | 4. Modified: When driver load failed,will return right error code.   |                          |
|               |              |    (Normal)                                                          |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.7.0    |  2013-07-15  | 1. Add: Double trigger feature.(Normal)                              |                          |
|               |              | 2. Add: Add counter cache for get last data when disconnection.      |                          |
|               |              |    (Normal)                                                          | libiodaq.so: V3.1.7.0    |
|               |              | 3. Modified: Raising overrun and cache overflow event priority.      |                          |
|               |              |    (Normal)                                                          |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.6.0    |  2013-05-15  | 1. Add: example add Counter_ContinueCompare,Counter_SnapCounter,     |                          |
|               |              |    Counter_UpDownCounter.(Normal)                                    | libiodaq.so: V3.1.6.0    |
|               |              | 2. Modified: fix qt and c++ example bug.(Normal)                     |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.5.0    |  2013-03-15  | 1. Modified: fix qt example bug.(Normal)                             | libiodaq.so: V3.1.5.0    |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.4.0    |  2013-01-15  | 1. Modified: Adjust the header file.(Normal)                         | libiodaq.so: V3.1.4.0    |
|               |              | 2. Add: Add remaining qt examples.                                   |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.3.0    |  2012-11-15  | 1. noise filter interface change.                                    |                          |
|               |              | 2. fix cscl thread lock bug.                                         |                          |
|               |              | 3. add feature for PCI1784.                                          | libiodaq.so: V3.1.3.0    |
|               |              | 4. fix multi BufferedAiCtrl's event will receive confusion.          |                          |
|               |              | 5. add up-down counting property.                                    |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.2.0    |  2012-09-15  | 1. Fix triggerEdges feature bug in integration layer.                |                          |
|               |              | 2. Disable TimerEvent OneShotEvent and  OverflowEvent feature.       | libiodaq.so: V3.1.2.0    |
|               |              | 3. fix Linux CSCL open device bug.                                   |                          |
|               |              | 4. Modify the Examples bugs.                                         |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.1.0    |  2012-07-15  | 1. Add 64bit architecture support.                                   | libiodaq.so: V3.1.1.0    |
|               |              | 2. Support Linux Mint12,Redhat Enterprise Linux6.2.                  |                          |
|               |              | 3. Modify the Examples bugs.                                         |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.0.0100   |  2012-05-15  | 1. Linux DAQNavi SDK Initial version.                                | libiodaq.so: V3.0.0100   |
|               |              | 2. Add Java,Qt,C++ examples for Linux.                               |                          |
|               |              | 3. Support Ubuntu10.04,Fedora16,OpenSUSE11.4                         |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------


DAQNavi_PCI1706:support PCI-1706
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1706.ko: V3.1.6.0     |
|               |              |                                                                      | libbio1706.so: V3.1.5.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1706.ko: V3.1.5.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1706.so: V3.1.4.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1706.ko: V3.1.4.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1706.so: V3.1.3.0  |
|               |              | 3.Modified:bug 9679, compiling error due lib api:                    |                          |
|               |              |            daq_umem_alloc/daq_umem_free                              |                          |
|               |              | 4.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 5.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 6.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified:Bug 20240.fix BufferedAI can't start work ,               | bio1706.ko: V3.1.3.0     |
|               |              |     and crashed error.                                               | libbio1706.so: V3.1.2.0  |
|               |              | 2.Modified the thread-safe bugs.                                     |                          |
|               |              | 3.Modified:Bug 19974: Modify the device description bug.             |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16566.fix InstantAO output data error.                | bio1706.ko: V3.1.2.0     |
|               |              | 2.Modified:Bug 16833.Add DO Write Bit Function.                      | libbio1706.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.4.0    |  2015-01-15  | 1.Added: Initial version.                                            | bio1706.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1706.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_ECUP1706:support ECUP-1706
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Added: Initial version.                                            | ecup1706.ko: V3.1.1.1    |
|               |              |                                                                      | libecup1706.so: V3.0.0.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1710:support PCI-1710/L/HG/HGL
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Added: Initial version.                                            | bio1710.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1710.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1711:support PCI-1711/L
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1711.ko: V3.1.8.0     |
|               |              |                                                                      | libbio1711.so: V3.1.9.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1711.ko: V3.1.7.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1711.so: V3.1.8.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1711.ko: V3.1.6.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1711.so: V3.1.7.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified the thread-safe bugs.                                     | bio1711.ko: V3.1.5.0     |
|               |              | 2.Modified:Bug 19974: Modify the device description bug.             | libbio1711.so: V3.1.6.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio1711.ko: V3.1.4.0     |
|               |              | 2.Modified:Bug 16566.fix InstantAO output data error.                | libbio1711.so: V3.1.6.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.4.0    |  2015-01-15  | 1.Modified: Bug 15214. Fix data count error in OneBufferedAI when    | bio1711.ko: V3.1.3.0     |
|               |              |             intervalCount is FIF0/2 and Sample is non integer times  | libbio1711.so: V3.1.5.0  |
|               |              |             to it .(Normal)                                          |                          |
|               |              | 2.Modified: Bug 13979. Add thread locker for FAI event.(Normal)      |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.2.0    |  2014-06-15  | 1.Modified: Bug 14651. Fix Readback ai convert frequency do not equal| bio1711.ko: V3.1.2.0     |
|               |              |             actually frequency after user set some frequency.(Normal)| libbio1711.so: V3.1.4.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | 1.Modified: Fix Delayed Pulse Generation function error.(Critical)   | bio1711.ko: V3.1.2.0     |
|               |              | 2.Modified: Set AO external reference value invalid.(Critical)       | libbio1711.so: V3.1.3.0  |
|               |              | 3.Modified: Bug 13979. Add thread locker for FAI event.(Normal)      |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.2.0    |  2013-07-15  | 1.Modified: Fix frequency measurement method error.(Critical)        | bio1711.ko: V3.1.1.0     |
|               |              | 2.Modified: Fix AO configure can not reset problem.(Normal)          | libbio1711.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.1.0    |  2013-01-15  | 1.Added: Initial version.                                            | bio1711.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1711.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1712B:support PCI-1712B
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.2.0.0    |  2022-12-28  | 1.Added: Initial version.                                            | bio1712b.ko: V4.2.0.0    |
|               |              |                                                                      | libbio1712b.so: V4.2.0.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1713:support PCI-1713/U
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1713.ko: V3.1.5.0     |
|               |              |                                                                      | libbio1713.so: V3.1.4.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1713.ko: V3.1.4.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1713.so: V3.1.3.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1713.ko: V3.1.3.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1713.so: V3.1.2.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified:Bug 19974: Modify the device description bug.             | bio1713.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1713.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.2.0    |  2014-06-15  |  1.Added: Initial version.                                           | bio1713.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1713.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------


DAQNavi_PCI1714_PCIE1744:support PCI-1714/UL,PCIE-1744,MIC-3714
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1714.ko: V3.1.7.0     |
|               |              |                                                                      | libbio1714.so: V3.1.8.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1714.ko: V3.1.6.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1714.so: V3.1.7.0  |
|               |              | 2.Modified:Bug 11922: CacheOverflow occurs frequently                |                          |
|               |              | 3.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1714.ko: V3.1.5.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1714.so: V3.1.6.0  |
|               |              | 3.Modified:bug 9592, Wrong calibration was loaded when change the    |                          |
|               |              |            channel's value range                                     |                          |
|               |              | 4.Modified:bug 10259, wrong trigger edge was used.                   |                          |
|               |              | 5.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 6.Modified:bug 9679, compiling error due lib api:                    |                          |
|               |              |            daq_umem_alloc/daq_umem_free                              |                          |
|               |              | 7.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 8.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified:Bug 19974: Modify the device description bug.             | bio1714.ko: V3.1.4.0     |
|               |              |                                                                      | libbio1714.so: V3.1.5.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.4.0    |  2015-01-15  | 1.Modified: Bug 13979. Add thread locker for FAI event.(Normal)      | bio1714.ko: V3.1.3.0     |
|               |              |                                                                      | libbio1714.so: V3.1.5.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.2.0    |  2014-06-15  | 1.Modified: Bug 14651. Fix Readback ai convert frequency do not equal| bio1714.ko: V3.1.3.0     |
|               |              |             actually frequency after user set some frequency.(Normal)| libbio1714.so: V3.1.4.0  |
--------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | 1.Modified: Bug 13242. Program maybe get data before DelayToStart    | bio1714.ko: V3.1.3.0     |
|               |              |    trigger.(Critical)                                                | libbio1714.so: V3.1.3.0  |
|               |              | 2.Modified: Bug 13979. Add thread locker for FAI event.(Normal)      |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.2.0    |  2013-03-15  | 1.Modified: Bug 10769. fix system crash error on 64bit OS.(Critical) | bio1714.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1714.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.1.0    |  2013-01-15  | 1.Added: Initial version.                                            | bio1714.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1714.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------


DAQNavi_PCI1715:support PCI-1715
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1715.ko: V3.1.7.0     |
|               |              |                                                                      | libbio1715.so: V3.1.6.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1715.ko: V3.1.6.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1715.so: V3.1.5.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1715.ko: V3.1.5.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1715.so: V3.1.4.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified:Bug 19974: Modify the device description bug.             | bio1715.ko: V3.1.4.0     |
|               |              |                                                                      | libbio1715.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.4.0    |  2015-01-15  | 1.Modified: Bug 15214. Fix data count error in OneBufferedAI when    | bio1715.ko: V3.1.3.0     |
|               |              |             intervalCount is FIF0/2 and Sample is non integer times  | libbio1715.so: V3.1.3.0  |
|               |              |             to it .(Normal)                                          |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.2.0    |  2014-06-15  | 1.Modified: Bug 14651. Fix Readback ai convert frequency do not equal| bio1715.ko: V3.1.2.0     |
|               |              |             actually frequency after user set some frequency.(Normal)| libbio1715.so: V3.1.3.0  |
--------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | 1.Modified: Optimize FAI stopping process.(Normal)                   | bio1715.ko: V3.1.2.0     |
|               |              | 2.Modified: Bug 13979. Add thread locker for FAI event.(Normal)      | libbio1715.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

|    3.1.1.0    |  2013-01-15  | 1.Added: Initial version.                                            | bio1715.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1715.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1715B:support PCI-1715B
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.2.0.0    |  2022-12-28  | 1.Added: Initial version.                                            | bio1715b.ko: V4.2.0.0    |
|               |              |                                                                      | libbio1715b.so: V4.2.0.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1716:support PCI1716/L,MIC-3716
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1716.ko: V3.1.7.0     |
|               |              |                                                                      | libbio1716.so: V3.1.6.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1716.ko: V3.1.6.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1716.so: V3.1.5.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1716.ko: V3.1.5.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1716.so: V3.1.4.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified the thread-safe bugs.                                     | bio1716.ko: V3.1.4.0     |
|               |              | 2.Modified:Bug 19974: Modify the device description bug.             | libbio1716.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio1716.ko: V3.1.3.0     |
|               |              | 1.Modified:Bug 16566.fix InstantAO output data error.                | libbio1716.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.4.0    |  2015-01-15  | 1.Modified: Bug 15821. Fix data read by InstantAI function is        | bio1716.ko: V3.1.2.0     |
|               |              |             instable                                                 | libbio1716.so: V3.1.2.0  |
|               |              | 2.Modified: Bug 15214. Fix data count error in OneBufferedAI when    |                          |
|               |              |             intervalCount is FIF0/2 and Sample is non integer times  |                          |
|               |              |             to it .(Normal)                                          |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.2.0    |  2014-06-15  | 1.Modified: Bug 14651. Fix Readback ai convert frequency do not equal| bio1716.ko: V3.1.1.0     |
|               |              |             actually frequency after user set some frequency.(Normal)| libbio1716.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | 1.Added: Initial version.                                            | bio1716.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1716.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1716B:support PCI1716B
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2022-11-24  | 1.Added: Initial version.                                            | bio1716b.ko: V4.0.1.5    |
|               |              |                                                                      | libbio1716b.so: V4.0.1.5 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1718:support PCI1718HDU/HGU
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2022-11-24  | 1.Added: Initial version.                                            | bio1718.ko: V3.1.10.0    |
|               |              |                                                                      | libbio1718.so: V3.1.12.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1720:support PCI-1720
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1720.ko: V3.1.5.0     |
|               |              |                                                                      | libbio1720.so: V3.1.5.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1720.ko: V3.1.4.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1720.so: V3.1.4.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1720.ko: V3.1.3.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1720.so: V3.1.3.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified:Bug 20099.Modify the BUILT_MODULE_NAME.                   | bio1720.ko: V3.1.2.0     |
|               |              | 2.Modified:Bug 19974: Modify the device description bug.             | libbio1720.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16566.fix InstantAO output data error.                | bio1720.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1720.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.4.0    |  2015-01-15  | 1.Added: Initial version.                                            | bio1720.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1720.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1721:support PCI-1721
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1721.ko: V3.1.12.0     |
|               |              |                                                                      | libbio1721.so: V3.1.11.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1721.ko: V3.1.11.0    |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1721.so: V3.1.10.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1721.ko: V3.1.10.0    |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1721.so: V3.1.9.0  |
|               |              | 3.Modified:bug 9679, compiling error due lib api:                    |                          |
|               |              |            daq_umem_alloc/daq_umem_free                              |                          |
|               |              | 4.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 5.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 6.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified the thread-safe bugs.                                     | bio1721.ko: V3.1.9.0     |
|               |              | 2.Modified:Bug 19974: Modify the device description bug.             | libbio1721.so.3.1.8.0    |
--------------- -------------- ---------------------------------------------------------------------- ---------------------------
|    3.2.7.0    |  2015-09-05  | 1.Modified: BUG 18281. AO Updating Rate Cannot Be Set Higher than    | bio1721.ko: V3.1.8.0     |
|               |              |             1MHz in Linux                                            | libbio1721.so.3.1.8.0    |
--------------- -------------- ---------------------------------------------------------------------- ---------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio1721.ko: V3.1.8.0     |
|               |              | 1.Modified:Bug 16566.fix InstantAO output data error.                | libbio1721.so: V3.1.7.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.4.0    |  2015-01-15  | 1.Modified: Bug 16114. Fix Transmitted Event can not be sent.(Normal)| bio1721.ko: V3.1.7.0     |
|               |              | 2.Modified: Bug 14759. Fix program DIO will excite a pules,when      | libbio1721.so: V3.1.6.0  |
|               |              |             execute reset function.(Normal)                          |                          |
|               |              | 3.Modified: Bug 13979. Add thread locker for FAO event.(Normal)      |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.2.0    |  2014-06-15  | 1.Modified: Bug 14651. Fix Readback ao convert frequency do not equal| bio1721.ko: V3.1.7.0     |
|               |              |             actually frequency after user set some frequency.(Normal)| libbio1721.so: V3.1.5.0  |
|               |              | 2.Modified: Bug 14759. Fix program DIO will excite a pules,when      |                          |
|               |              |             execute reset function.(Normal)                          |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | 1.Modified: Add check FAO stopping timeout.(Normal)                  | bio1721.ko: V3.1.7.0     |
|               |              | 2.Modified: Bug 13979. Add thread locker for FAO event.(Normal)      | libbio1721.so: V3.1.4.0  |
|               |              | 3.Modified: Bug 13268. Data maybe output error under StreamingAO mode|                          |
|               |              |   .(Critical)                                                        |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.6.0    |  2013-07-15  | 1.Modified: Fix buffered AO stop and start again AO output error, if | bio1721.ko: V3.1.6.0     |
|               |              |   do not exist problem.(Normal)                                      | libbio1721.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.5.0    |  2013-05-15  | 1.Modified: Bug 12114. Fix buffered AO will bluescreen in some time. | bio1721.ko: V3.1.5.0     |
|               |              |   (Critical)                                                         | libbio1721.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.4.0    |  2013-03-15  | 1.Modified: one-shot can't change to extern clock. (Normal)          | bio1721.ko: V3.1.4.0     |
|               |              |                                                                      | libbio1721.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.3.0    |  2013-01-15  | 1.Modified: Bug 10769. fix dma transfer error on 64bit OS. (Critical)| bio1721.ko: V3.1.3.0     |
|               |              |                                                                      | libbio1721.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.2.0    |  2012-11-15  | 1. fix compiler warning.                                             | bio1721.ko: V3.1.2.0     |
|               |              | 2. counter must reset before device close.                           | libbio1721.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.1.0    |  2012-07-15  | 1. Add 64bit architecture support.                                   | bio1721.ko: V3.1.1.0     |
|               |              | 2. fixed general bugs.(bug 10903, 10908).                            | libbio1721.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.0.0100   |  2012-05-15  | 1. Initial version.                                                  | bio1721.ko: V3.0.0100    |
|               |              |                                                                      | libbio1721.so: V3.0.0100 |
 --------------- -------------- ----------------------------------------------------------------------- --------------------------

DAQNavi_PCI1721B:support PCI1721B
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.2.0.1    |  2023-6-6    | 1.Added: Initial version.                                            | bio1721b.ko: V4.2.0.1    |
|               |              |                                                                      | libbio1721b.so: V4.2.0.1 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------


 DAQNavi_PCI1723:support PCI-1723, MIC-3723
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1723.ko: V3.1.4.0     |
|               |              |                                                                      | libbio1723.so: V3.1.4.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1723.ko: V3.1.3.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1723.so: V3.1.3.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1723.ko: V3.1.2.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1723.so: V3.1.2.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Initial version.                                                   | bio1723.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1723.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1724:support PCI-1724
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1724.ko: V3.1.6.0     |
|               |              |                                                                      | libbio1724.so: V3.1.6.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1724.ko: V3.1.5.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1724.so: V3.1.5.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1724.ko: V3.1.4.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1724.so: V3.1.4.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified:Bug 19974: Modify the device description bug.             | bio1724.ko: V3.1.3.0     |
|               |              |                                                                      | libbio1724.so: V3.1.4.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.9.0    |  2016-07-14  | 1.Modified:Bug 19788.fix InstantAO initial value error.              | bio1724.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1724.so: V3.1.4.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16566.fix InstantAO output data error.                | bio1724.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1724.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | Only update product version.                                         | bio1724.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1724.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.2.0    |  2013-01-15  | 1.Modified: Remove unused variables.(Normal)                         | bio1724.ko: V3.1.2.0     |
|               |              | 2.Modified: Re-arrange the header files structure.(Normal)           | libbio1724.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.1.0    |  2012-11-15  | 1. Initial version.                                                  | bio1724.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1724.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1727:support PCI-1727U
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1727.ko: V3.1.6.0     |
|               |              |                                                                      | libbio1727.so: V3.1.5.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1727.ko: V3.1.5.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1727.so: V3.1.4.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1727.ko: V3.1.4.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1727.so: V3.1.3.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified the thread-safe bugs.                                     | bio1727.ko: V3.1.3.0     |
|               |              | 2.Modified:Bug 19974: Modify the device description bug.             | libbio1727.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio1727.ko: V3.1.2.0     |
|               |              | 1.Modified:Bug 16566.fix InstantAO output data error.                | libbio1727.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | Only update product version.                                         | bio1727.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1727.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.1.0    |  2013-01-15  | 1.Added: Initial version.                                            | bio1727.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1727.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1730:support PCI-1730
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1730.ko: V3.1.8.0     |
|               |              |                                                                      | libbio1730.so: V3.1.6.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1730.ko: V3.1.7.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1730.so: V3.1.5.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1730.ko: V3.1.6.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1730.so: V3.1.4.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified the thread-safe bugs.                                     | bio1730.ko: V3.1.5.0     |
|               |              | 2.Modified:Bug 19974: Modify the device description bug.             | libbio1730.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio1730.ko: V3.1.4.0     |
|               |              |                                                                      | libbio1730.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | Only update product version.                                         | bio1730.ko: V3.1.3.0     |
|               |              |                                                                      | libbio1730.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.3.0    |  2013-07-15  | 1. Modified: Port value is not correct when read back DO .(Normal)   | bio1730.ko: V3.1.3.0     |
|               |              |                                                                      | libbio1730.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.2.0    |  2013-01-15  | 1. Modified: Re-arrange the header files structure.(Normal)          | bio1730.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1730.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.1.0    |  2012-11-15  | 1. Initial version.                                                  | bio1730.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1730.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

 DAQNavi_PCI1733:support PCI-1733
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1733.ko: V3.1.4.0     |
|               |              |                                                                      | libbio1733.so: V3.1.4.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1733.ko: V3.1.3.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1733.so: V3.1.3.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1733.ko: V3.1.2.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1733.so: V3.1.2.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Initial version.                                                   | bio1733.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1733.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1734:support PCI-1734
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1734.ko: V3.1.6.0     |
|               |              |                                                                      | libbio1734.so: V3.1.5.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1734.ko: V3.1.5.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1734.so: V3.1.4.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1734.ko: V3.1.4.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1734.so: V3.1.3.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified the thread-safe bugs.                                     | bio1734.ko: V3.1.3.0     |
|               |              | 2.Modified:Bug 19974: Modify the device description bug.             | libbio1734.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio1734.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1734.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | Only update product version.                                         | bio1734.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1734.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.1.0    |  2013-07-15  | 1.Added: Initial version.                                            | bio1734.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1734.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1737_PCI1739:support PCI-1737,PCI-1739
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1737.ko: V3.1.3.0     |
|               |              |                                                                      | libbio1737.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1737.ko: V3.1.2.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1737.so: V3.1.2.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Added: Initial version.                                            | bio1737.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1737.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
 
DAQNavi_PCI1741:support PCI-1741
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1741.ko: V3.1.6.0     |
|               |              |                                                                      | libbio1741.so: V3.1.5.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1741.ko: V3.1.5.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1741.so: V3.1.4.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1741.ko: V3.1.4.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1741.so: V3.1.3.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified the thread-safe bugs.                                     | bio1741.ko: V3.1.3.0     |
|               |              | 2.Modified:Bug 19974: Modify the device description bug.             | libbio1741.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio1741.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1741.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.4.1    |  2015-01-07  | 1.Modified:Bug 16566.fix InstantAO output data error.                | bio1741.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1741.so: V3.1.1.1  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.4.0    |  2015-01-15  | 1.Added: Initial version.                                            | bio1741.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1741.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1747:support PCI-1747
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1747.ko: V3.1.7.0     |
|               |              |                                                                      | libbio1747.so: V3.1.7.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1747.ko: V3.1.6.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1747.so: V3.1.6.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1747.ko: V3.1.5.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1747.so: V3.1.5.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified:Bug 19974: Modify the device description bug.             | bio1747.ko: V3.1.4.0     |
|               |              |                                                                      | libbio1747.so: V3.1.4.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.4.0    |  2015-01-15  | 1.Modified: Bug 15214. Fix data count error in OneBufferedAI when    | bio1747.ko: V3.1.3.0     |
|               |              |             intervalCount is FIF0/2 and Sample is non integer times  | libbio1747.so: V3.1.4.0  |
|               |              |             to it .(Normal)                                          |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.2.0    |  2014-06-15  | 1.Modified: Bug 14651. Fix Readback ai convert frequency do not equal| bio1747.ko: V3.1.2.0     |
|               |              |             actually frequency after user set some frequency.(Normal)| libbio1747.so: V3.1.4.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | 1.Modified: Bug 13979. Add thread locker for FAI event.(Normal)      | bio1747.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1747.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.2.0    |  2013-01-15  | 1.Modified: Bug 10769. fix dma transfer error on 64bit OS. (Critical)| bio1747.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1747.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.1.0    |  2012-07-15  | 1. Add 64bit architecture support.                                   | bio1747.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1747.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.0.0100   |  2012-05-15  | 1. Initial version.                                                  | bio1747.ko: V3.0.0100    |
|               |              |                                                                      | libbio1747.so: V3.0.0100 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1750:support PCI-1750
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1750.ko: V3.1.6.0     |
|               |              |                                                                      | libbio1750.so: V3.1.5.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1750.ko: V3.1.6.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1750.so: V3.1.5.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1750.ko: V3.1.5.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1750.so: V3.1.4.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified the thread-safe bugs.                                     | bio1750.ko: V3.1.4.0     |
|               |              | 2.Modified:Bug 19974: Modify the device description bug.             | libbio1750.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio1750.ko: V3.1.3.0     |
|               |              |                                                                      | libbio1750.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | Only update product version.                                         | bio1750.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1750.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.2.0    |  2013-01-15  | 1.Modified: Re-arrange the header files structure.(Normal)           | bio1750.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1750.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.1.0    |  2012-11-15  | 1. Initial version.                                                  | bio1750.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1750.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1751:support PCI-1751
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1751.ko: V3.1.6.0     |
|               |              |                                                                      | libbio1751.so: V3.1.5.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1751.ko: V3.1.5.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1751.so: V3.1.4.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1751.ko: V3.1.4.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1751.so: V3.1.3.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified:Bug 20245.Add board ID support.                           | bio1751.ko: V3.1.3.0     |
|               |              | 2.Modified the thread-safe bugs.                                     | libbio1751.so: V3.1.2.0  |
|               |              | 3.Modified:Bug 19974: Modify the device description bug.             |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio1751.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1751.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.2.0    |  2014-06-15  | 1.Added: Initial version.                                            | bio1751.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1751.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1752:support PCI-1752
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1752.ko: V3.1.6.0     |
|               |              |                                                                      | libbio1752.so: V3.1.5.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1752.ko: V3.1.5.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1752.so: V3.1.4.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1752.ko: V3.1.4.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1752.so: V3.1.3.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified the thread-safe bugs.                                     | bio1752.ko: V3.1.3.0     |
|               |              | 2.Modified:Bug 19974: Modify the device description bug.             | libbio1752.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio1752.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1752.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | Only update product version.                                         | bio1752.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1752.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.1.0    |  2013-01-15  | 1.Added: Initial version.                                            | bio1752.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1752.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1753/PCM3753I:support PCI-1753,PCM-3753I,MIC-3753
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1753.ko: V3.1.6.0     |
|               |              |                                                                      | libbio1753.so: V3.1.6.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1753.ko: V3.1.5.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1753.so: V3.1.5.0  |
|               |              | 2.Modified:Bug 11914: modify the default state of DO as high         |                          |
|               |              | 3.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1753.ko: V3.1.4.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1753.so: V3.1.4.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified the thread-safe bugs.                                     | bio1753.ko: V3.1.3.0     |
|               |              | 2.Modified:Bug 19974: Modify the device description bug.             | libbio1753.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio1753.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1753.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.2.0    |  2014-06-15  | 1.Modified: Bug 14759. Fix program DIO will excite a pules,when      | bio1753.ko: V3.1.1.0     |
|               |              |             execute reset function.(Normal)                          | libbio1753.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | 1.Added: Initial version.                                            | bio1753.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1753.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

 DAQNavi_PCI1754:support PCI1754
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1754.ko: V3.1.5.0     |
|               |              |                                                                      | libbio1754.so: V3.1.4.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1754.ko: V3.1.4.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1754.so: V3.1.3.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-09-14  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1754.ko: V3.1.3.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1754.so: V3.1.2.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified the thread-safe bugs.                                     | bio1754.ko: V3.1.2.0     |
|               |              | 2.Modified:Bug 19974: Modify the device description bug.             | libbio1754.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.8.0    |  2016-03-29  | 1. Initial version.                                                  | bio1754.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1754.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

 DAQNavi_PCI1756:support PCI-1756,MIC-3756
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1756.ko: V3.1.7.0     |
|               |              |                                                                      | libbio1756.so: V3.1.6.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1756.ko: V3.1.6.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1756.so: V3.1.5.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1756.ko: V3.1.5.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1756.so: V3.1.4.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:Bug 8555:Fix wrong error code is returned                 |                          |
|               |              |            when dll driver doesn't match with kernel driver.         |                          |
|               |              | 5.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 6.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified the thread-safe bugs.                                     | bio1756.ko: V3.1.4.0     |
|               |              | 2.Modified:Bug 19974: Modify the device description bug.             | libbio1756.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.7.0    |  2015-6-29   | 1.Added: ModeWriteShared.                                            | bio1756.ko: V3.1.3.0     |
|               |              |                                                                      | libbio1756.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio1756.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1756.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | 1.Added: Initial version.                                            | bio1756.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1756.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1757:support PCI-1757
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1757.ko: V3.1.6.0     |
|               |              |                                                                      | libbio1757.so: V3.1.6.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1757.ko: V3.1.5.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1757.so: V3.1.5.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1757.ko: V3.1.4.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1757.so: V3.1.4.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified the thread-safe bugs.                                     | bio1757.ko: V3.1.3.0     |
|               |              | 2.Modified:Bug 19974: Modify the device description bug.             | libbio1757.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio1757.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1757.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.4.0    |  2015-01-15  | 1.Modified: Bug 15268. Fix read&Write EEPROM error                   | bio1757.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1757.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.2.0    |  2014-06-15  | 1.Added: Initial version.                                            | bio1757.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1757.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1758:support PCI-1758UDI,PCI-1758UDIO,PCI-1758UDO
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1758.ko: V3.1.7.0     |
|               |              |                                                                      | libbio1758.so: V3.1.7.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1758.ko: V3.1.6.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1758.so: V3.1.6.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1758.ko: V3.1.5.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1758.so: V3.1.5.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:Bug 8581:Fix DO status would be impacted by other channel.|                          |
|               |              | 5.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 6.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified the thread-safe bugs.                                     | bio1758.ko: V3.1.4.0     |
|               |              | 2.Modified:Bug 19974: Modify the device description bug.             | libbio1758.so: V3.1.4.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  |  1.Modified:Bug 16833.Add Do write bit.                              | bio1758.ko: V3.1.3.0     |
|               |              |                                                                      | libbio1758.so: V3.1.4.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | Only update product version.                                         | bio1758.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1758.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.3.0    |  2013-01-15  | 1.Modified: Re-arrange the header files structure.(Normal)           | bio1758.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1758.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.2.0    |  2012-11-15  | 1. Remove unused variables.                                          | bio1758.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1758.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.1.0    |  2012-07-15  | 1. Add 64bit architecture support.                                   | bio1758.ko: V3.1.1.0     |
|               |              | 2. Disable Interrupt feature.                                        | libbio1758.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.0.0100   |  2012-05-15  | 1. Initial version.                                                  | bio1758.ko: V3.0.0100    |
|               |              |                                                                      | libbio1758.so: V3.0.0100 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1760:support PCI-1760
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2022-11-24  | 1.Initial version.                                                   | bio1760.ko: V3.1.9.0     |
|               |              |                                                                      | libbio1760.so: V3.1.5.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1761:support PCI-1761,PCM-3761I,MIC-3761
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1761.ko: V3.1.8.0     |
|               |              |                                                                      | libbio1761.so: V3.1.8.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1761.ko: V3.1.7.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1761.so: V3.1.7.0  |
|               |              | 2.Modified:Bug 11665: failed to register access                      |                          |
|               |              | 3.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1761.ko: V3.1.6.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1761.so: V3.1.6.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified the thread-safe bugs.                                     | bio1761.ko: V3.1.5.0     |
|               |              | 2.Modified:Bug 19974: Modify the device description bug.             | libbio1761.so: V3.1.5.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio1761.ko: V3.1.4.0     |
|               |              |                                                                      | libbio1761.so: V3.1.5.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.4.0    |  2015-01-15  | 1.Added: support PCM-3761I.                                          | bio1761.ko: V3.1.3.0     |
|               |              |                                                                      | libbio1761.so: V3.1.4.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | Only update product version.                                         | bio1761.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1761.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.3.0    |  2013-01-15  | 1.Modified: Re-arrange the header files structure.(Normal)           | bio1761.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1761.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.2.0    |  2012-11-15  | 1. Improve performanc.                                               | bio1761.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1761.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.1.0    |  2012-09-15  | 1. Initial version.                                                  | bio1761.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1761.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCI1762:support PCI-1762
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1762.ko: V3.1.7.0     |
|               |              |                                                                      | libbio1762.so: V3.1.6.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1762.ko: V3.1.6.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1762.so: V3.1.5.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1762.ko: V3.1.5.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1762.so: V3.1.4.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified the thread-safe bugs.                                     | bio1762.ko: V3.1.4.0     |
|               |              | 2.Modified:Bug 19974: Modify the device description bug.             | libbio1762.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio1762.ko: V3.1.3.0     |
|               |              |                                                                      | libbio1762.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | Only update product version.                                         | bio1762.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1762.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.2.0    |  2013-01-15  | 1.Modified: Re-arrange the header files structure.(Normal)           | bio1762.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1762.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.1.0    |  2012-11-15  | 1. Initial version.                                                  | bio1762.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1762.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

 DAQNavi_PCI1780:support PCI1780
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1. Initial version.                                                  | bio1780.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1780.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

 DAQNavi_PCI1780-B:support PCI1780-B
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.2.1.0    |  2024-12-20  | 1. Initial version.                                                  | bio1780b.ko: V4.2.1.0    |
|               |              |                                                                      | libbio1780b.so: V4.2.1.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

 DAQNavi_PCI1784:support PCI1784
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1784.ko: V3.1.5.0     |
|               |              |                                                                      | libbio1784.so: V3.1.4.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1784.ko: V3.1.4.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1784.so: V3.1.3.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1784.ko: V3.1.3.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1784.so: V3.1.2.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified the thread-safe bugs.                                     | bio1784.ko: V3.1.2.0     |
|               |              | 2.Modified:Bug 19974: Modify the device description bug.             | libbio1784.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.8.0    |  2016-03-29  | 1. Initial version.                                                  | bio1784.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1784.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

 DAQNavi_PCI1784-B:support PCI1784-B
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.2.1.0    |  2024-12-20  | 1. Initial version.                                                  | bio1784b.ko: V4.2.1.0    |
|               |              |                                                                      | libbio1784b.so: V4.2.1.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCM3810I:support PCM-3810I
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio3810.ko: V3.1.8.0     |
|               |              |                                                                      | libbio3810.so: V3.1.7.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio3810.ko: V3.1.7.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio3810.so: V3.1.6.0  |
|               |              | 2.Modified:Bug 11665: failed to register access                      |                          |
|               |              | 3.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio3810.ko: V3.1.6.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio3810.so: V3.1.5.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:bug 9715. Fix a compiling error because of missing i387.h |                          |
|               |              | 5.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 6.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified the thread-safe bugs.                                     | bio3810.ko: V3.1.5.0     |
|               |              | 2.Modified:Bug 19974: Modify the device description bug.             | libbio3810.so: V3.1.4.0  |
 --------------- -------------- ---------------------------------------------------------------------- -------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio3810.ko: V3.1.4.0     |
|               |              |                                                                      | libbio3810.so: V3.1.4.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.4.0    |  2015-01-15  | 1.Modified: Bug 15214. Fix data count error in OneBufferedAI when    | bio3810.ko: V3.1.3.0     |
|               |              |             intervalCount is FIF0/2 and Sample is non integer times  | libbio3810.so: V3.1.3.0  |
|               |              |             to it .(Normal)                                          |                          |
|               |              | 2.Modified: Bug 13603. Fix AI Trigger delay time error(Normal)       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.2.0    |  2014-06-15  | 1.Modified: Bug 14759. Fix program DIO will excite a pules,when      | bio3810.ko: V3.1.2.0     |
|               |              |             execute reset function.(Normal)                          | libbio3810.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | 1.Modified: Bug 13979. Add thread locker for FAO,FAI event.(Normal)  | bio3810.ko: V3.1.2.0     |
|               |              |                                                                      | libbio3810.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.2.0    |  2013-07-15  | 1.Modified: Fix buffered AO stop and start again AO output error, if | bio3810.ko: V3.1.2.0     |
|               |              |   do not exist problem.(Normal)                                      | libbio3810.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.1.0    |  2013-05-15  | 1. Initial version.                                                  | bio3810.ko: V3.1.1.0     |
|               |              |                                                                      | libbio3810.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCIGPDC:support PCIE-1730,PCIE-1751,PCIE-1752,PCIE-1753,PCIE-1756,PCIE-1760,PCIE-1765
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.8.0    |  2023-11-06  | 1.Modified: Firmware Download                                        | biogpdc.ko: V4.0.8.0     |
|               |              |                                                                      | libbiogpdc.so: V4.0.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.2.0    |  2022-11-24  | 1.Added: PCIE-1756/1760/1765                                         | biogpdc.ko: V4.0.7.0     |
|               |              |                                                                      | libbiogpdc.so: V4.0.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.1.1    |  2019-05-28  | 1.Added: support PCIE-1753                                           | biogpdc.ko: V3.1.12.0    |
|               |              |                                                                      | libbiogpdc.so: V3.1.10.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | biogpdc.ko: V3.1.11.0    |
|               |              |                                                                      | libbiogpdc.so: V3.1.10.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.13.0   |  2018-06-01  | 1.Modified:Bug 12738. No interrupt when using TimerPulse function.   | biogpdc.ko: V3.1.10.0    |
|               |              |                                                                      | libbiogpdc.so: V3.1.9.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | biogpdc.ko: V3.1.9.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbiogpdc.so: V3.1.9.0  |
|               |              | 2.Modified:Bug 11665: failed to register access                      |                          |
|               |              | 3.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | biogpdc.ko: V3.1.8.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbiogpdc.so: V3.1.8.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified the thread-safe bugs.                                     | biogpdc.ko: V3.1.7.0     |
|               |              | 2.Modified:Bug 19974: Modify the device description bug.             | libbiogpdc.so: V3.1.7.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.8.0    |  2016-03-29  | 1.Added: support PCIE-1752.                                          | biogpdc.ko: V3.1.6.0     |
|               |              |                                                                      | libbiogpdc.so: V3.1.6.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.6.0    |  2015-07-15  | 1.Added: support PCIE-1751.                                          | biogpdc.ko: V3.1.5.0     |
|               |              |                                                                      | libbiogpdc.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | biogpdc.ko: V3.1.4.0     |
|               |              |                                                                      | libbiogpdc.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.4.0    |  2015-01-15  | 1.Added: support PCIE-1730.                                          | biogpdc.ko: V3.1.3.0     |
|               |              |                                                                      | libbiogpdc.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.2.0    |  2014-06-15  | 1.Added: support PCIE-1756.                                          | biogpdc.ko: V3.1.2.0     |
|               |              | 2.Modified: Bug 14759. Fix program DIO will excite a pules,when      | libbiogpdc.so: V3.1.2.0  |
|               |              |             execute reset function.(Normal)                          |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | 1.Added: Initial version, support PCIE-1760                          | biogpdc.ko: V3.1.1.0     |
|               |              |                                                                      | libbiogpdc.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCIGPDCB:support PCIE-1760B/PCIE-1751B/PCIE-1753B
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.2.2.0    |  2023-11-6    | 1.Modified: Firmware Download.                                      | biogpdcb.ko: V4.2.2.0    |
|               |              |                                                                      | libbiogpdcb.so: V4.2.1.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.2.0.1    |  2023-6-6    | 1.Added: PCIE-1751-B, PCIE-1753-B.                                   | biogpdcb.ko: V4.2.0.1    |
|               |              |                                                                      | libbiogpdcb.so: V4.2.0.1 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.2.0.0    |  2022-12-28  | 1.Added: Initial version.                                            | biogpdcb.ko: V4.2.0.0    |
|               |              |                                                                      | libbiogpdcb.so: V4.2.0.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

 DAQNavi_PCIGPDCX:support PCIE-1730H/1730H-B/1750U/1750UH/1756H/1756H-B/1758DI/1758DO/1758DIO/1761H/1762H/1763AH/1763DH
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.7.0    |  2023-11-06  | 1.Modified:Firmware Download.                                        | biogpdcx.ko: V4.0.7.0    |
|               |              |                                                                      | libbiogpdcx.so: V4.0.6.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | biogpdcx.ko: V4.0.2.0    |
|               |              |                                                                      | libbiogpdcx.so: V4.0.2.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.13.0   |  2018-06-15  | 1.Added: Initial version, support PCIE-1756H                         | biogpdcx.ko: V3.1.1.0    |
|               |              |                                                                      | libbiogpdcx.so: V3.1.1.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

 DAQNavi_PCIE1747:support PCIE-1747
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2026-1-14   | 1.Added: Initial version, support PCIE-1747                          | bio1747a.ko: V4.0.0.0    |
|               |              |                                                                      | libbio1747a.so: V4.0.0.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

 DAQNavi_PCIE1802:support PCIE1802
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.10.0   |  2023-11-06  | 1.Modified:Firmware Download.                                        | bio1802.ko: V4.0.10.0    |
|               |              |                                                                      | libbio1802.so: V4.0.8.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1802.ko: V3.1.4.0     |
|               |              |                                                                      | libbio1802.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1802.ko: V3.1.3.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1802.so: V3.1.2.0  |
|               |              | 2.Modified:Bug 11665: failed to register access                      |                          |
|               |              | 3.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
|               |              | 4.Modified:Bug 12459: kernel error occurs when running StreamingAI   |                          |
|               |              |            for a long time.                                          |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Initial version.                                                   | bio1802.ko: V3.1.2.0     |
|               |              |                                                                      | libbio1802.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

 DAQNavi_PCIE1803:support PCIE-1803
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.3.3    |  2021-01-08  | 1.Added: Initial version, support PCIE-1803                          | bio1803.ko: V4.0.1.1     |
|               |              |                                                                      | libbio1803.so: V4.0.2.2  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

 DAQNavi_PCIE1805:support PCIE-1805
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.7.0    |  2023-11-06  | 1.Modified: Firmware Download                                        | bio1805.ko: V4.0.6.0     |
|               |              |                                                                      | libbio1805.so: V4.0.7.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.2.5    |  2020-09-03  | 1.Added: Initial version, support PCIE-1805                          | bio1805.ko: V4.0.1.1     |
|               |              |                                                                      | libbio1805.so: V4.0.1.1  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCIE1810:support PCIE1810,MIC-1810
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.1.0    |  2022-11-24  | 1.Upgraded to DN4.                                                   | bio1810.ko: V4.0.10.0    |
|               |              |                                                                      | libbio1810.so: V4.0.9.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio1810.ko: V3.1.5.0     |
|               |              |                                                                      | libbio1810.so: V3.1.5.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio1810.ko: V3.1.4.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio1810.so: V3.1.4.0  |
|               |              | 2.Modified:Bug 11665: failed to register access                      |                          |
|               |              | 3.Modified:Bug 10631: wrong AO output on boundary value              |                          |
|               |              | 4.Modified:Bug 12105: The MIOe-3810 is renamed MIC-1810.             |                          |
|               |              | 5.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio1810.ko: V3.1.3.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio1810.so: V3.1.3.0  |
|               |              | 3.Modified:bug 10685, wrong trigger edge for ch8,ch16                |                          |
|               |              | 4.Add support of MIOe3810                                            |                          |
|               |              | 5.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 6.Modified:fix bug: Fix 1810 AI data has no SN field                 |                          |
|               |              | 7.Modified:fix bug: compiling error for cross-compiling: amd64.      |                          |
|               |              | 8.Modified:bug 10734. The description of PCIE1810 is wrong.          |                          |
|               |              | 9.Modified:bug 10679. Failed to set the trigger1 source              |                          |
|               |              |            as SigExtDigTrigger1.                                     |                          |
|               |              | 10.Modified:bug 10660. The AO out is wrong when using multi-channel. |                          |
|               |              | 11.Modified:bug 10652. The funciton of channel reentry is wrong.     |                          |
|               |              | 12.Modified:bug 10625. Failed to set the trigger1 source.            |                          |
|               |              | 13.Modified:bug 10546. Failed to update datas when                   |                          |
|               |              |            modifying valueRange.                                     |                          |
|               |              | 14.Modified:bug 10535. The return value of valueRange count is wrong.|                          |
|               |              | 15.Modified:Bug 10955: compiling error on kernel v4.13               |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1. Modified:Bug 20252.Fix crashed error when set DIO port direction. | bio1810.ko: V3.1.2.0     |
|               |              | 2. Modified the thread-safe bugs.                                    | libbio1810.so: V3.1.2.0  |
|               |              | 3. Modified:Bug 19974: Modify the device description bug.            |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.8.0    |  2016-03-29  | 1. Initial version.                                                  | bio1810.ko: V3.1.1.0     |
|               |              |                                                                      | libbio1810.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCIE1810B:support PCIE-1810B
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.2.1.0    |  2023-11-6   | 1.Modified: Firmware Download                                        | bio1810b.ko: V4.2.0.0    |
|               |              |                                                                      | libbio1810b.so: V4.2.1.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.1    |  2023-6-6    | 1.Added: Initial version, support PCIE-1810-B                        | bio1810b.ko: V4.0.0.1    |
|               |              |                                                                      | libbio1810b.so: V4.0.0.1 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCIE1812:support PCIE1812
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2022-11-24  | 1.Initial version.                                                   | bio1812.ko: V4.1.5.0     |
|               |              |                                                                      | libbio1812.so: V4.1.4.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCIE1812-B:support PCIE1812-B
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.2.1.0    |  2024-12-20  | 1.Modified: Add time up setting for counter                          | bio1812b.ko: V4.2.1.0    |
|               |              |                                                                      | libbio1812b.so: V4.2.1.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2024-6-12   | 1.Initial version.                                                   | bio1812b.ko: V4.0.0.0    |
|               |              |                                                                      | libbio1812b.so: V4.0.0.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCIGPSCMF:support PCIE-1816,MIC-1816
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.1.0    |  2022-11-24  | 1.Upgraded to DN4.                                                   | biogpscmf.ko: V4.0.11.0  |
|               |              |                                                                      | libbiogpscmf.so: V4.0.8.0|
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | biogpscmf.ko: V3.1.6.0   |
|               |              |                                                                      | libbiogpscmf.so: V3.1.6.0|
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | biogpscmf.ko: V3.1.5.0   |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbiogpscmf.so: V3.1.5.0|
|               |              | 2.Modified:Bug 11665: failed to register access                      |                          |
|               |              | 3.Modified:Bug 10631: wrong AO output on boundary value              |                          |
|               |              | 4.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
|               |              | 5.Modified:Bug 12105: The MIOe-3816 is renamed MIC-1816.             |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | biogpscmf.ko: V3.1.4.0   |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbiogpscmf.so: V3.1.4.0|
|               |              | 3.Modified:bug 10685, wrong trigger edge for ch8,ch16                |                          |
|               |              | 4.Add support of MIOe3816                                            |                          |
|               |              | 5.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 6.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 7.Modified:Bug 10955: compiling error on kernel 840v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1. Modified:Bug 20252.Fix crashed error when set DIO port direction. | biogpscmf.ko: V3.1.3.0   |
|               |              | 2. Modified the thread-safe bugs.                                    | libbiogpscmf.so: V3.1.3.0|
|               |              | 3. Modified:Bug 19974: Modify the device description bug.            |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.8.0    |  2016-03-29  | 1. Modified: Bug of MUX calculation                                  | biogpscmf.ko: V3.1.2.0   |
|               |              |                                                                      | libbiogpscmf.so: V3.1.2.0|
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.7.0    |  2015-09-17  | 1. Initial version.                                                  | biogpscmf.ko: V3.1.1.0   |
|               |              |                                                                      | libbiogpscmf.so: V3.1.1.0|
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCIE1816B:support PCIE-1816B
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.2.1.0    |  2023-11-06  | 1.Modified: Firmware Download                                        | bio1816b.ko: V4.2.1.0    |
|               |              |                                                                      | libbio1816b.so: V4.2.1.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2023-06-06  | 1.Added: Initial version, support PCIE-1816-B                        | bio1816b.ko: V4.0.0.0    |
|               |              |                                                                      | libbio1816b.so: V4.0.0.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

 DAQNavi_PCIE1824:support PCIE-1824
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.5.0    |  2023-11-06  | 1.Modified: Firmware Download                                        | bio1824.ko: V4.0.5.0     |
|               |              |                                                                      | libbio1824.so: V4.0.4.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.2.5    |  2020-09-03  | 1.Added: Initial version, support PCIE-1824                          | bio1824.ko: V4.0.2.1     |
|               |              |                                                                      | libbio1824.so: V4.0.1.2  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

 DAQNavi_PCIE1840:support PCIE-1840
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.9.0    |  2024-12-20  | 1.Modified: fix bug: DMA transfer                                    | bio1840.ko: V4.0.8.1     |
|               |              |                                                                      | libbio1840.so: V4.0.6.2  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.1.0    |  2019-09-26  | 1.Initial version.                                                   | bio1840.ko: V4.0.1.1     |
|               |              |                                                                      | libbio1840.so: V4.0.1.1  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCIE1841:support PCIE-1841
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.2.0    |  2023-6-6    | 1.Modified: Firmware Download                                        | bio1841.ko: V4.0.1.0     |
|               |              |                                                                      | libbio1841.so: V4.0.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.1    |  2023-6-6    | 1.Initial version.                                                   | bio1841.ko: V4.0.0.1     |
|               |              |                                                                      | libbio1841.so: V4.0.0.1  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCIE1842:support PCIE-1842/L/PCIE-1843/L/MIOE-3842/MIOE-3844
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.1.1    |  2022-05-31  | 1.Initial version.                                                   | bio1842.ko: V4.0.1.1     |
|               |              |                                                                      | libbio1842.so: V4.0.1.1  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCIE1882:support PCIE1882
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2022-11-24  | 1.Initial version.                                                   | bio1882.ko: V4.0.1.0     |
|               |              |                                                                      | libbio1882.so: V4.0.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCIE1884:support PCIE1884
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.1.8.0    |  2023-11-06  | 1.Modified:fix bug#34820: Output Frequency is not correct.           | bio1884.ko: V4.1.8.0     |
|               |              |                                                                      | libbio1884.so: V4.1.7.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Initial version.                                                   | bio1884.ko: V4.0.4.0     |
|               |              |                                                                      | libbio1884.so: V4.0.4.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_USB4702/4704:support USB-4702,USB-4704
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.2.6    |  2020-09-15  | 1.Modified:fix bug 22149: Frequency measurement error.               | bio4704.ko: V3.1.7.1     |
|               |              |                                                                      | libbio4704.so: V3.1.11.1 |  
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio4704.ko: V3.1.6.0     |
|               |              |                                                                      | libbio4704.so: V3.1.5.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.13.0   |  2018-06-01  | 1.Modified:bug 12921: Failed to compile the driver.                  | bio4704.ko: V3.1.8.0     |
|               |              |                                                                      | libbio4704.so: V3.1.8.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio4704.ko: V3.1.7.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio4704.so: V3.1.7.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio4704.ko: V3.1.6.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio4704.so: V3.1.6.0  |
|               |              | 3.Modified:fix bug: kernel warning of DO write port                  |                          |
|               |              | 4.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 5.Modified:bug 10099. compiling error due to the absence of i387.h   |                          |
|               |              | 6.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 7.Modified:bug 10100. usb communication error on kernel v4.11        |                          |
|               |              | 8.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified:Bug 19974: Modify the device description bug.             | bio4704.ko: V3.1.5.0     |
|               |              |                                                                      | libbio4704.so: V3.1.5.0  |
--------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio4704.ko: V3.1.4.0     |
|               |              | 1.Modified:Bug 16566.fix InstantAO output data error.                | libbio4704.so: V3.1.5.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | 1.Modified: Bug 13979. Add thread locker for FAI event.(Normal)      | bio4704.ko: V3.1.3.0     |
|               |              |                                                                      | libbio4704.so: V3.1.4.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.3.0    |  2013-03-15  | 1.Modified:Bug 11889.Fix device can't run on max pacer rate.(Critical|                          |
|               |              |   )                                                                  | bio4704.ko: V3.1.3.0     |
|               |              | 2.Modified:Bug 12296.Fix device can't set convert clock rate.(Critica| libbio4704.so: V3.1.3.0  |
|               |              |   l)                                                                 |                          |
|               |              | 3.Modified:BUg 12329.Fix can not recive data ready event.(Critical)  |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.2.0    |  2013-01-15  | 1.Modified: Bug 11731.Fix interval count can't be 2 exponential power| bio4704.ko: V3.1.2.0     |
|               |              |   bug.(Critical)                                                     | libbio4704.so: V3.1.2.0  |
|               |              | 2.Modified: Bug 11114.If ai start after stopped faster, ai may be can|                          |
|               |              |   not start.(Critical)                                               |                          |
|               |              | 3.Modified: Bug 10769. fix dma transfer error on 64bit OS. (Critical)|                          |
|               |              | 4.Modified: Re-arrange the header files structure.(Normal)           |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.1.0    |  2012-09-15  | 1. Initial version.                                                  | bio4704.ko: V3.1.1.0     |
|               |              |                                                                      | libbio4704.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_USB4711A:support USB-4711A
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio4711a.ko: V3.1.7.0    |
|               |              |                                                                      | libbio4711a.so: V3.1.7.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.13.0   |  2018-06-01  | 1.Modified:bug 12921: Failed to compile the driver.                  | bio4711a.ko: V3.1.6.0    |
|               |              |                                                                      | libbio4711a.so: V3.1.6.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio4711a.ko: V3.1.5.0    |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio4711a.so: V3.1.5.0 |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio4711a.ko: V3.1.4.0    |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio4711a.so: V3.1.4.0 |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:bug 10100. usb communication error on kernel v4.11        |                          |
|               |              | 6.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified:Bug 19974: Modify the device description bug.             | bio4711a.ko: V3.1.3.0    |
|               |              |                                                                      | libbio4711a.so: V3.1.3.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio4711a.ko: V3.1.2.0    |
|               |              | 1.Modified:Bug 16566.fix InstantAO output data error.                | libbio4711a.so: V3.1.3.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | 1.Modified: Bug 13979. Add thread locker for FAI event.(Normal)      | bio4711a.ko: V3.1.1.0    |
|               |              |                                                                      | libbio4711a.so: V3.1.2.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.1.0    |  2013-07-15  | 1.Added: Initial version.                                            | bio4711a.ko: V3.1.1.0    |
|               |              |                                                                      | libbio4711a.so: V3.1.1.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_USB4716:support USB-4716
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio4716.ko: V3.1.9.0     |
|               |              |                                                                      | libbio4716.so: V3.1.10.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.13.0   |  2018-06-01  | 1.Modified:bug 12921: Failed to compile the driver.                  | bio4716.ko: V3.1.8.0     |
|               |              |                                                                      | libbio4716.so: V3.1.9.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio4716.ko: V3.1.7.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio4716.so: V3.1.8.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio4716.ko: V3.1.6.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio4716.so: V3.1.7.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:bug 10100. usb communication error on kernel v4.11        |                          |
|               |              | 6.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified:Bug 19974: Modify the device description bug.             | bio4716.ko: V3.1.5.0     |
|               |              |                                                                      | libbio4716.so: V3.1.6.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio4716.ko: V3.1.4.0     |
|               |              | 1.Modified:Bug 16566.fix InstantAO output data error.                | libbio4716.so: V3.1.6.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | 1.Modified: Bug 13979. Add thread locker for FAI event.(Normal)      | bio4716.ko: V3.1.3.0     |
|               |              |                                                                      | libbio4716.so: V3.1.5.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.4.0    |  2013-07-15  | 1.Modified: Bug 12605.If use extern clock, sometime last data maybe  |                          |
|               |              |   lost.(Critical)                                                    |                          |
|               |              | 2.Modified: Update Reconnection way.(Normal)                         | bio4716.ko: V3.1.3.0     |
|               |              | 3.Modified: Bug 13244.Setting SignalType error.(Normal)              | libbio4716.so: V3.1.4.0  |
|               |              | 4.Modified: Bug 13250.AI data error,when singal type is Differential.|                          |
|               |              |   (Critical)                                                         |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.3.0    |  2013-03-15  | 1.Modified:Bug 12296.Fix device can't set convert clock rate.(Critica| bio4716.ko: V3.1.2.0     |
|               |              |   l)                                                                 | libbio4716.so: V3.1.3.0  |
|               |              | 2.Modified:BUg 12329.Fix can not recive data ready event.(Critical)  |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.2.0    |  2013-01-15  | 1.Modified: Bug 11731.Fix interval count can't be 2 exponential power| bio4716.ko: V3.1.2.0     |
|               |              |   bug.(Critical)                                                     | libbio4716.so: V3.1.2.0  |
|               |              | 2.Modified: Bug 11114.If ai start after stopped faster, ai may be can|                          |
|               |              |   not start.(Critical)                                               |                          |
|               |              | 3.Modified: Bug 10769. fix dma transfer error on 64bit OS. (Critical)|                          |
|               |              | 4.Modified: Re-arrange the header files structure.(Normal)           |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.1.0    |  2012-07-15  | 1. Add 64bit architecture support.                                   | bio4716.ko: V3.1.1.0     |
|               |              | 2. fixed general bugs.(bug 10897, 10895).                            | libbio4716.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.0.0100   |  2012-05-15  | 1. Initial version.                                                  | bio4716.ko: V3.0.0100    |
|               |              |                                                                      | libbio4716.so: V3.0.0100 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_USB4711B/4716B:support USB-4711B/4716B
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.1.0    |  2022-04-20  | 1.Initial version.                                                   | bio4716b.ko: V4.0.1.0    |
|               |              |                                                                      | libbio4716b.so: V4.0.1.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_USB4718:support USB4718
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio4718.ko: V3.1.8.0     |
|               |              |                                                                      | libbio4718.so: V3.1.7.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.13.0   |  2018-06-01  | 1.Modified:bug 12921: Failed to compile the driver.                  | bio4718.ko: V3.1.7.0     |
|               |              |                                                                      | libbio4718.so: V3.1.6.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio4718.ko: V3.1.6.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio4718.so: V3.1.5.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio4718.ko: V3.1.5.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio4718.so: V3.1.4.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:bug 10100. usb communication error on kernel v4.11        |                          |
|               |              | 6.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified:Bug 19974: Modify the device description bug.             | bio4718.ko: V3.1.4.0     |
|               |              |                                                                      | libbio4718.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio4718.ko: V3.1.3.0     |
|               |              | 2.Modified:Bug 16826.Add DeviceRemoved event                         | libbio4718.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | Only update product version.                                         | bio4718.ko: V3.1.2.0     |
|               |              |                                                                      | libbio4718.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.2.0    |  2013-01-15  | 1.Modified: Re-arrange the header files structure.(Normal)           | bio4718.ko: V3.1.2.0     |
|               |              |                                                                      | libbio4718.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.1.0    |  2012-07-15  | 1. Add 64bit architecture support.                                   | bio4718.ko: V3.1.1.0     |
|               |              | 2. fixed general bugs.(bug 10906).                                   | libbio4718.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.0.0100   |  2012-05-15  | 1. Initial version.                                                  | bio4718.ko: V3.0.0100    |
|               |              |                                                                      | libbio4718.so: V3.0.0100 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_USB4750:support USB-4750
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio4750.ko: V3.1.9.0     |
|               |              |                                                                      | libbio4750.so: V3.1.7.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.13.0   |  2018-06-01  | 1.Modified:bug 12921: Failed to compile the driver.                  | bio4750.ko: V3.1.8.0     |
|               |              |                                                                      | libbio4750.so: V3.1.6.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio4750.ko: V3.1.7.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio4750.so: V3.1.5.0  |
|               |              | 2.Modified:Bug 11797: The value of DI is incorrect.                  |                          |
|               |              | 3.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio4750.ko: V3.1.6.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio4750.so: V3.1.4.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:bug 10100. usb communication error on kernel v4.11        |                          |
|               |              | 6.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified:Bug 19974: Modify the device description bug.             | bio4750.ko: V3.1.5.0     |
|               |              |                                                                      | libbio4750.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio4750.ko: V3.1.4.0     |
|               |              |                                                                      | libbio4750.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.2.0    |  2014-06-15  | 1.Modified: Bug 14167. Change DO default state from 0xFF to 0x0.     | bio4750.ko: V3.1.3.0     |
|               |              |             (Normal)                                                 | libbio4750.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | Only update product version.                                         | bio4750.ko: V3.1.2.0     |
|               |              |                                                                      | libbio4750.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.2.0    |  2013-01-15  | 1.Modified: Re-arrange the header files structure.(Normal)           | bio4750.ko: V3.1.2.0     |
|               |              |                                                                      | libbio4750.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.1.0    |  2012-07-15  | 1. Add 64bit architecture support.                                   | bio4750.ko: V3.1.1.0     |
|               |              | 2. fixed general bugs.(bug 10905).                                   | libbio4750.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.0.0100   |  2012-05-15  | 1. Initial version.                                                  | bio4750.ko: V3.0.0100    |
|               |              |                                                                      | libbio4750.so: V3.0.0100 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_USB4750C:support USB-4750C
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2022-11-24  | 1.Initial version.                                                   | bio4750c.ko: V4.2.0.1    |
|               |              |                                                                      | libbio4750c.so: V4.2.0.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_USB4751:support USB4751/L
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio4751.ko: V3.1.8.0     |
|               |              |                                                                      | libbio4751.so: V3.1.7.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.13.0   |  2018-06-01  | 1.Modified:bug 12921: Failed to compile the driver.                  | bio4751.ko: V3.1.7.0     |
|               |              |                                                                      | libbio4751.so: V3.1.6.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio4751.ko: V3.1.6.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio4751.so: V3.1.5.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio4751.ko: V3.1.5.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio4751.so: V3.1.4.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:bug 10100. usb communication error on kernel v4.11        |                          |
|               |              | 6.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified:Bug 19974: Modify the device description bug.             | bio4751.ko: V3.1.4.0     |
|               |              |                                                                      | libbio4751.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio4751.ko: V3.1.3.0     |
|               |              |                                                                      | libbio4751.so: V3.1.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.2.0    |  2014-06-15  | 1. Initial version.                                                  | bio4751.ko: V3.1.2.0     |
|               |              |                                                                      | libbio4751.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_USB4751B:support USB4751B/L
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.2.3.0    |  2022-11-24  | 1. Modified: Firmware Download                                       | bio4751b.ko: V4.2.3.0    |
|               |              |                                                                      | libbio4751b.so: V4.2.2.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2022-11-24  | 1. Initial version.                                                  | bio4751b.ko: V4.0.2.1    |
|               |              |                                                                      | libbio4751b.so: V4.0.2.2 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_USB4761:support USB-4761
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio4761.ko: V3.1.7.0     |
|               |              |                                                                      | libbio4761.so: V3.1.6.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.13.0   |  2018-06-01  | 1.Modified:bug 12921: Failed to compile the driver.                  | bio4761.ko: V3.1.6.0     |
|               |              |                                                                      | libbio4761.so: V3.1.5.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio4761.ko: V3.1.5.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio4761.so: V3.1.4.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio4761.ko: V3.1.4.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio4761.so: V3.1.3.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:bug 10100. usb communication error on kernel v4.11        |                          |
|               |              | 6.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified:Bug 19974: Modify the device description bug.             | bio4761.ko: V3.1.3.0     |
|               |              |                                                                      | libbio4761.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio4761.ko: V3.1.2.0     |
|               |              |                                                                      | libbio4761.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.1.0    |  2014-02-15  | Only update product version.                                         | bio4761.ko: V3.1.1.0     |
|               |              |                                                                      | libbio4761.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.1.1.0    |  2013-07-15  | 1.Added: Initial version.                                            | bio4761.ko: V3.1.1.0     |
|               |              |                                                                      | libbio4761.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_USB4761B:support USB-4761B
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.2.1.0    |  2023-11-06  | 1.Modified: Firmware Download.                                       | bio4761b.ko: V4.2.0.0    |
|               |              |                                                                      | libbio4761b.so: V4.2.1.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2022-11-24  | 1.Added: Initial version.                                            | bio4761b.ko: V4.2.0.0    |
|               |              |                                                                      | libbio4761b.so: V4.2.0.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_USB5800:support USB-5830,USB-5850,USB-5855,USB-5856,USB-5860,USB-5862
 --------------- -------------- ---------------------------------------------------------------------- ---------------------------
|    Version    |     Date     |                             Description                              |          Updated          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.6.0    |  2023-11-06  | 1.Modified:Firmware Download.                                        | bio5800dio.ko: V4.0.6.0   |
|               |              |                                                                      | libbio5800dio.so: V4.0.6.0|
 --------------- -------------- ---------------------------------------------------------------------- ---------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio5800dio.ko: V4.0.0.0   |
|               |              |                                                                      | libbio5800dio.so: V4.0.0.0|
 --------------- -------------- ---------------------------------------------------------------------- ---------------------------
|    3.2.13.0   |  2018-06-01  | 1.Added: Initial version.                                            | bio5800dio.ko: V3.1.1.0   |
|               |              |                                                                      | libbio5800dio.so: V3.1.1.0|
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_USB5801:support USB-5801
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.9.0    |  2023-11-06  | 1.Modified: Firmware Download                                        | bio5801.ko: V4.0.9.0     |
|               |              |                                                                      | libbio5801.so: V4.0.8.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.2.5    |  2020-09-03  | 1.Added: Initial version, support USB-5801                           | bio5801.ko: V4.0.3.1     |
|               |              |                                                                      | libbio5801.so: V4.0.2.1  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_USB5817:support USB-5817
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.5.0    |  2023-11-06  | 1.Modified: Firmware download                                        | bio5817.ko: V4.0.5.0     |
|               |              |                                                                      | libbio5817.so: V4.0.5.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.2.7    |  2020-11-06  | 1.Added: Initial version, support USB-5817                           | bio5817.ko: V4.0.2.0     |
|               |              |                                                                      | libbio5817.so: V4.0.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_USB5820:support USB-5820
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.2.7    |  2020-11-06  | 1.Added: Initial version, support USB-5820                           | bio5820.ko: V4.0.7.0     |
|               |              |                                                                      | libbio5820.so: V4.0.6.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_USB5820:support USB-5820
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.3.0    |  2020-12-07  | 1.Added: Initial version, support USB-5820                           | bio5820.ko: V4.0.3.0     |
|               |              |                                                                      | libbio5820.so: V4.0.3.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_USBiDAQ:support iDAQ-731/751/763D/784/801/815/817/821/841/868/871/873/Fusion/974ClientLibrary
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.11.0   |  2026-2-11   | 1.Added: iDAQ-974 Client Library                                     | bioidaq.ko: V4.0.11.0    |
|               |              |                                                                      | libbioidaq.so: V4.0.10.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.10.0   |  2024-12-20  | 1.Added: iDAQ-868                                                    | bioidaq.ko: V4.0.10.0    |
|               |              |                                                                      | libbioidaq.so: V4.0.10.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.9.0    |  2024-07-20  | 1.Added: iDAQ-784/871/873                                            | bioidaq.ko: V4.0.9.0     |
|               |              |                                                                      | libbioidaq.so: V4.0.9.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.7.0    |  2023-11-6   | 1.Modified: Improve the USB transfer performance                     | bioidaq.ko: V4.0.7.0     |
|               |              | 2.Modified: fix bug#35096: iDAQ-801&iDAQ-841 Fusion                  | libbioidaq.so: V4.0.7.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.5.3    |  2023-6-6    | 1.Added: iDAQ-938 Chassis                                            | bioidaq.ko: V4.0.5.3     |
|               |              |                                                                      | libbioidaq.so: V4.0.5.3  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.4.0    |  2020-12-07  | 1.Added: Initial version, support USB iDAQ Series                    | bioidaq.ko: V4.0.4.0     |
|               |              |                                                                      | libbioidaq.so: V4.0.4.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCM3718:support PCM-3718,PCM-3718H,PCM-3718HG,PCM-3718HO
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio3718.ko: V3.2.8.0     |
|               |              |                                                                      | libbio3718.so: V3.2.7.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.13.0   |  2018-06-01  | 1.Modified:bug 12921: Failed to compile the driver.                  | bio3718.ko: V3.2.7.0     |
|               |              |                                                                      | libbio3718.so: V3.2.6.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio3718.ko: V3.2.6.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio3718.so: V3.2.5.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio3718.ko: V3.2.5.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio3718.so: V3.2.4.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified the thread-safe bugs.                                     |  bio3718.ko: V3.2.4.0    |
|               |              | 2.Modified:Bug 19974: Modify the device description bug.             |  libbio3718.so: V3.2.3.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.8.0    |  2016-03-29  | 1.Modified:Bug 18431. Some channel return error code when set signal |  bio3718.ko: V3.2.3.0    |
|               |              |   type. Some channel return the same value with the start channel's  |  libbio3718.so: V3.2.3.0 |
|               |              |   when scanning multi channel                                        |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio3718.ko: V3.1.2.0     |
|               |              | 2.Modified:Bug 16946.Fix DMA Channel setting error                   | libbio3718.so: V3.1.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.4.0    |  2015-01-15  | 1. Initial version.                                                  | bio3718.ko: V3.1.1.0     |
|               |              |                                                                      | libbio3718.so: V3.1.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCM3725:support PCM-3725
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio3725.ko: V3.2.7.0     |
|               |              |                                                                      | libbio3725.so: V3.2.6.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.13.0   |  2018-06-01  | 1.Modified:bug 12921: Failed to compile the driver.                  | bio3725.ko: V3.2.6.0     |
|               |              |                                                                      | libbio3725.so: V3.2.5.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio3725.ko: V3.2.5.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio3725.so: V3.2.4.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio3725.ko: V3.2.4.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio3725.so: V3.2.3.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified the thread-safe bugs.                                     | bio3725.ko: V3.2.3.0     |
|               |              | 2.Modified:Bug 19974: Modify the device description bug.             | libbio3725.so: V3.2.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio3725.ko: V3.2.2.0     |
|               |              |                                                                      | libbio3725.so: V3.2.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.4.0    |  2015-01-15  | 1. Initial version.                                                  | bio3725.ko: V3.2.1.0     |
|               |              |                                                                      | libbio3725.so: V3.2.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCM3730:support PCM-3730
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.0    |  2018-10-12  | 1.Modified:fix bug: updated for Linux DN4 SDK.                       | bio3730.ko: V3.2.7.0     |
|               |              |                                                                      | libbio3730.so: V3.2.6.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.13.0   |  2018-06-01  | 1.Modified:bug 12921: Failed to compile the driver.                  | bio3730.ko: V3.2.6.0     |
|               |              |                                                                      | libbio3730.so: V3.2.5.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.12.0   |  2018-04-01  | 1.Modified:fix bug: compiling error for                              | bio3730.ko: V3.2.5.0     |
|               |              |            cross-compiling: arm64 oecore and amd64                   | libbio3730.so: V3.2.4.0  |
|               |              | 2.Modified:fix bug: updated for Linux DN4 SDK.                       |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.11.0   |  2017-10-17  | 1.Modified:fix bug: compiling error on linux kernel 4.11             | bio3730.ko: V3.2.4.0     |
|               |              | 2.Modified:fix bug: compiling error for cross-compiling: arm64 oecore| libbio3730.so: V3.2.3.0  |
|               |              | 3.Modified:bug 8825. Fix a compiling error after the kernel upgraded |                          |
|               |              | 4.Modified:fix bug: compiling error for cross-compiling: amd64       |                          |
|               |              | 5.Modified:Bug 10955: compiling error on kernel v4.13                |                          |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.10.0   |  2016-12-21  | 1.Modified the thread-safe bugs.                                     | bio3730.ko: V3.2.3.0     |
|               |              | 2.Modified:Bug 19974: Modify the device description bug.             | libbio3730.so: V3.2.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.5.0    |  2015-04-01  | 1.Modified:Bug 16833.Add Do write bit.                               | bio3730.ko: V3.2.2.0     |
|               |              |                                                                      | libbio3730.so: V3.2.2.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    3.2.4.0    |  2015-01-15  | 1. Initial version.                                                  | bio3730.ko: V3.2.1.0     |
|               |              |                                                                      | libbio3730.so: V3.2.1.0  |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_PCMGPDC:support PCM-2731,MOS-1110Y-01,PCM-27D24DI,PCM-37D24DI
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.3.0    |  2024-12-20  | 1.Added: PCM-37D24DI.                                                | biopcmgpdc.ko: V4.0.3.0   |
|               |              |                                                                      | libbiopcmgpdc.so: V4.0.2.0|
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.1    |  2018-11-06  | 1.Added: Initial version.                                            | biopcmgpdc.ko: V4.0.0.1   |
|               |              |                                                                      | libbiopcmgpdc.so: V4.0.0.1|
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

DAQNavi_AMAX5000:support AMAX-5000 & WISE-5000 series modules
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    Version    |     Date     |                             Description                              |          Updated         |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.1.8.0    |  2024-07-20  | 1.Added: AMAX-5081.                                                  | amax5000s.ko: V4.1.8.0   |
|               |              |                                                                      | libamax5000.so: V4.1.8.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.1.7.0    |  2023-11-06  | 1.Added: AMAX-5060.                                                  | amax5000s.ko: V4.1.7.0   |
|               |              |                                                                      | libamax5000.so: V4.1.7.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------
|    4.0.0.1    |  2020-11-17  | 1.Added: Initial version.                                            | amax5000s.ko: V4.0.0.1   |
|               |              |                                                                      | libamax5000.so: V4.0.4.0 |
 --------------- -------------- ---------------------------------------------------------------------- --------------------------

Other device driver by request.