from enum import Enum
from typing import Any, List
from pydantic import BaseModel


class CZ_LSM_LUTTYPE(Enum):
    NORMAL = 0


class CZ_LSM_SUBBLOCK_TYPE(Enum):
    GAMMA = 1
    BRIGHTNESS = 2
    CONTRAST = 3
    RAMP = 4
    KNOTS = 5
    PALETTE_12_TO_12 = 6


class Laser(BaseModel):
    Name: str
    Acquire: int
    Power: float


class DetectionChannel(BaseModel):
    DetectorGainFirst: float
    DetectorGainLast: float
    AmplifierGainFirst: float
    AmplifierGainLast: float
    AmplifierOffsFirst: float
    AmplifierOffsLast: float
    PinholeDiameter: float
    CountingTrigger: float
    Acquire: int
    IntegrationMode: int
    SpecialMode: int
    PointDetectorName: str
    AmplifierName: str
    PinholeName: str
    FilterSetName: str
    FilterName: str
    Entry0x70000011: str
    Entry0x70000012: str
    IntegratorName: str
    ChannelName: str
    DetectorGainBc1: float
    DetectorGainBc2: float
    AmplifierGainBc1: float
    AmplifierGainBc2: float
    AmplifierOffsetBc1: float
    AmplifierOffsetBc2: float
    SpectralScanChannels: int
    SpiWavelengthStart: float
    SpiWavelengthStop: float
    Entry0x70000024: float
    Entry0x70000025: float
    DyeName: str
    DyeFolder: str
    Entry0x70000028: float
    Entry0x70000029: float
    Entry0x70000030: float


class BeamSplitter(BaseModel):
    FilterSet: str
    Filter: str
    Name: str


class IlluminationChannel(BaseModel):
    Name: str
    Power: float
    Wavelength: float
    Aquire: int
    Entry0x90000009: float
    PowerBc1: float
    PowerBc2: float


class DataChannel(BaseModel):
    Name: str
    Acquire: int
    Color: int
    SampleType: int
    BitsPerSample: int
    RatioType: int
    RatioTrack1: int
    RatioTrack2: int
    RatioChannel1: str
    RatioChannel2: str
    RatioConst1: float
    RatioConst2: float
    RatioConst3: float
    RatioConst4: float
    RatioConst5: float
    RatioConst6: float


class Track(BaseModel):
    PixelTime: float
    TimeBetweenStacks: float
    MultiplexType: int
    MultiplexOrder: int
    SamplingMode: int
    SamplingMethod: int
    SamplingNumber: int
    Acquire: int
    Name: str
    Collimator1Position: int
    Collimator1Name: str
    Collimator2Position: int
    Collimator2Name: str
    IsBleachTrack: int
    IsBleachAfterScanNumber: int
    BleachScanNumber: int
    TriggerIn: str
    TriggerOut: str
    IsRatioTrack: int
    BleachCount: int
    SpiCenterWavelength: float
    Entry0x4000003f: int
    IdCondensorAperture: str
    CondensorAperture: float
    IdCondensorRevolver: str
    CondensorFilter: str
    IdTubelens: str
    IdTubelensPosition: str
    TransmittedLight: float
    ReflectedLight: float
    DetectionChannels: List[DetectionChannel]
    BeamSplitters: List[BeamSplitter]
    IlluminationChannels: List[IlluminationChannel]
    DataChannels: List[DataChannel]


class ScanInformation(BaseModel):
    Name: str
    Description: str
    Notes: str
    Objective: str
    SpecialScanMode: str
    ScanType: str
    ScanMode: str
    NumberOfStacks: int
    LinesPerPlane: int
    SamplesPerLine: int
    PlanesPerVolume: int
    ImagesWidth: int
    ImagesHeight: int
    ImagesNumberPlanes: int
    ImagesNumberStacks: int
    ImagesNumberChannels: int
    LinscanXySize: int
    ScanDirection: int
    ScanDirectionZ: int
    TimeSeries: int
    OriginalScanData: int
    ZoomX: float
    ZoomY: float
    ZoomZ: float
    Sample0X: float
    Sample0Y: float
    Sample0Z: float
    SampleSpacing: float
    LineSpacing: float
    PlaneSpacing: float
    Rotation: float
    Nutation: float
    Precession: float
    Sample0time: float
    StartScanTriggerIn: str
    StartScanTriggerOut: str
    StartScanEvent: int
    StartScanTime: float
    StopScanTriggerIn: str
    StopScanTriggerOut: str
    StopScanEvent: int
    StopScanTime: float
    UseRois: int
    UseReducedMemoryRois: int
    User: str
    UseBcCorrection: int
    PositionBcCorrection1: float
    PositionBcCorrection2: float
    InterpolationY: int
    CameraBinning: int
    CameraSupersampling: int
    CameraFrameWidth: int
    CameraFrameHeight: int
    CameraOffsetX: float
    CameraOffsetY: float
    RtBinning: int
    Entry0x10000064: int
    RtFrameWidth: int
    RtFrameHeight: int
    RtRegionWidth: int
    RtRegionHeight: int
    RtOffsetX: float
    RtOffsetY: float
    RtZoom: float
    RtLinePeriod: float
    Prescan: int
    Lasers: List[Laser]
    Tracks: List[Track]
    Timers: List[Any]
    Markers: List[Any]


class ChannelColors(BaseModel):
    Mono: bool
    Colors: List[List[int]]
    ColorNames: List[str]


class SubBlock(BaseModel):
    Type: CZ_LSM_SUBBLOCK_TYPE
    Data: Any  # Replace 'Any' with specific type if needed


class Lut(BaseModel):
    LutType: CZ_LSM_LUTTYPE
    Advanced: int
    NumberChannels: int
    CurrentChannel: int
    SubBlocks: List[SubBlock]


class LSMMetadata(BaseModel):
    MagicNumber: int
    StructureSize: int
    DimensionX: int
    DimensionY: int
    DimensionZ: int
    DimensionChannels: int
    DimensionTime: int
    DataType: int
    ThumbnailX: int
    ThumbnailY: int
    VoxelSizeX: float
    VoxelSizeY: float
    VoxelSizeZ: float
    OriginX: float
    OriginY: float
    OriginZ: float
    ScanType: int
    SpectralScan: int
    TypeOfData: int
    OffsetVectorOverlay: int
    OffsetInputLut: int
    OffsetOutputLut: int
    OffsetChannelColors: int
    TimeIntervall: float
    OffsetChannelDataTypes: int
    OffsetScanInformation: int
    OffsetKsData: int
    OffsetTimeStamps: int
    OffsetEventList: int
    OffsetRoi: int
    OffsetBleachRoi: int
    OffsetNextRecording: int
    DisplayAspectX: float
    DisplayAspectY: float
    DisplayAspectZ: float
    DisplayAspectTime: float
    OffsetMeanOfRoisOverlay: int
    OffsetTopoIsolineOverlay: int
    OffsetTopoProfileOverlay: int
    OffsetLinescanOverlay: int
    ToolbarFlags: int
    OffsetChannelWavelength: int
    OffsetChannelFactors: int
    ObjectiveSphereCorrection: float
    OffsetUnmixParameters: int
    OffsetAcquisitionParameters: int
    OffsetCharacteristics: int
    OffsetPalette: int
    TimeDifferenceX: float
    TimeDifferenceY: float
    TimeDifferenceZ: float
    InternalUse1: int
    DimensionP: int
    DimensionM: int
    DimensionsReserved: List[int]
    OffsetTilePositions: int
    f56: List[int]
    OffsetPositions: int
    ScanInformation: ScanInformation
    TimeStamps: List[float]
    EventList: List[Any]
    ChannelColors: ChannelColors
    Positions: List[List[float]]
    TilePositions: List[List[float]]
    InputLut: Lut
    OutputLut: Lut
    ChannelDataTypes: List[int]
    ChannelWavelength: List[List[float]]
