from typing import Optional, Union, Literal, Dict
from pydantic import validator

from sdks.novavision.src.base.model import (
    Package,
    Input,
    Output,
    Config,
    Inputs,
    Configs,
    Outputs,
    Response,
    Request,
    BinaryFile,
)


# ---------------------------------------------------------------------------
# Data carrier
# ---------------------------------------------------------------------------
# Files travel between packages exactly like images: the raw bytes are stored
# in Redis and only a reference (`r_key`) + metadata ride in the response.
# `BinaryFile` (base model) is that carrier; a downstream package re-hydrates
# the bytes from Redis instead of reading a /storage path.
File = BinaryFile


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
class InputFile(Input):
    name: Literal["inputFile"] = "inputFile"
    value: Union[Dict, BinaryFile]
    type: str = "object"

    @validator("type", pre=True, always=True)
    def set_type_based_on_value(cls, value, values):
        value = values.get("value")
        if isinstance(value, list):
            return "list"
        return "object"

    class Config:
        title = "File"


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
class OutputFile(Output):
    name: Literal["outputFile"] = "outputFile"
    value: Union[Dict, BinaryFile]
    type: str = "object"

    @validator("type", pre=True, always=True)
    def set_type_based_on_value(cls, value, values):
        value = values.get("value")
        if isinstance(value, list):
            return "list"
        return "object"

    class Config:
        title = "File"


# ---------------------------------------------------------------------------
# Shared format parameters (shown as dependent sub-fields under a format option)
#
# cupsWidth / cupsHeight / cupsBitsPerPixel / cupsBytesPerLine are NOT exposed
# here: they are derived in code from the choices below (see utils.py), e.g.
#   cupsWidth        = round(PageSize_pt[0] * dpi / 72)
#   cupsBytesPerLine = cupsWidth * cupsBitsPerPixel / 8   (padded, no remainder)
# ---------------------------------------------------------------------------

# --- Geometry & Resolution --------------------------------------------------
class OptionDpi300(Config):
    name: Literal["300"] = "300"
    value: Literal["300"] = "300"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "300 DPI (Standard)"


class OptionDpi600(Config):
    name: Literal["600"] = "600"
    value: Literal["600"] = "600"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "600 DPI (Photo)"


class ConfigResolution(Config):
    """
        Hardware resolution (HWResolution) in dots per inch. Used to compute the
        pixel canvas size from the physical page size.
    """
    name: Literal["ConfigResolution"] = "ConfigResolution"
    group: Literal["Geometry"] = "Geometry"
    value: Union[OptionDpi300, OptionDpi600]
    type: Literal["object"] = "object"
    field: Literal["dropdownlist"] = "dropdownlist"

    class Config:
        title = "Resolution (DPI)"


class OptionPageA4(Config):
    name: Literal["A4"] = "A4"
    value: Literal["A4"] = "A4"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "A4 (595 x 842 pt)"


class OptionPageLetter(Config):
    name: Literal["Letter"] = "Letter"
    value: Literal["Letter"] = "Letter"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "Letter (612 x 792 pt)"


class ConfigPageSize(Config):
    """
        Physical page size in points (1/72 inch). The pixel canvas is computed
        as (PageSize * DPI) / 72.
    """
    name: Literal["ConfigPageSize"] = "ConfigPageSize"
    group: Literal["Geometry"] = "Geometry"
    value: Union[OptionPageA4, OptionPageLetter]
    type: Literal["object"] = "object"
    field: Literal["dropdownlist"] = "dropdownlist"

    class Config:
        title = "Page Size"


# --- Color & Bit Depth ------------------------------------------------------
class OptionColorSRGB(Config):
    name: Literal["sRGB"] = "sRGB"
    value: Literal["19"] = "19"  # cupsColorSpace 19 = sRGB
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "Color (sRGB)"


class OptionColorSGray(Config):
    name: Literal["Sgray"] = "Sgray"
    value: Literal["18"] = "18"  # cupsColorSpace 18 = Sgray
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "Grayscale"


class ConfigColorSpace(Config):
    """
        cupsColorSpace. sRGB drives 24 bpp output, Grayscale drives 8 bpp;
        cupsBitsPerColor is fixed at 8.
    """
    name: Literal["ConfigColorSpace"] = "ConfigColorSpace"
    group: Literal["Color"] = "Color"
    value: Union[OptionColorSRGB, OptionColorSGray]
    type: Literal["object"] = "object"
    field: Literal["dropdownlist"] = "dropdownlist"

    class Config:
        title = "Color Space"


# --- Print Job Options ------------------------------------------------------
class OptionDuplexSimplex(Config):
    name: Literal["Simplex"] = "Simplex"
    value: Literal["0"] = "0"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "Simplex (Single-sided)"


class OptionDuplexNoTumble(Config):
    name: Literal["DuplexNoTumble"] = "DuplexNoTumble"
    value: Literal["1"] = "1"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "Duplex - Long Edge (Book)"


class OptionDuplexTumble(Config):
    name: Literal["DuplexTumble"] = "DuplexTumble"
    value: Literal["2"] = "2"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "Duplex - Short Edge (Calendar)"


class ConfigDuplex(Config):
    """Duplex (double-sided) printing mode."""
    name: Literal["ConfigDuplex"] = "ConfigDuplex"
    group: Literal["PrintJob"] = "PrintJob"
    value: Union[OptionDuplexSimplex, OptionDuplexNoTumble, OptionDuplexTumble]
    type: Literal["object"] = "object"
    field: Literal["dropdownlist"] = "dropdownlist"

    class Config:
        title = "Duplex"


class OptionTrayAuto(Config):
    name: Literal["Auto"] = "Auto"
    value: Literal["0"] = "0"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "Auto"


class OptionTrayMain(Config):
    name: Literal["Main"] = "Main"
    value: Literal["1"] = "1"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "Main Tray"


class OptionTrayAlternate(Config):
    name: Literal["Alternate"] = "Alternate"
    value: Literal["2"] = "2"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "Alternate / Photo Tray"


class ConfigMediaPosition(Config):
    """MediaPosition (input tray)."""
    name: Literal["ConfigMediaPosition"] = "ConfigMediaPosition"
    group: Literal["PrintJob"] = "PrintJob"
    value: Union[OptionTrayAuto, OptionTrayMain, OptionTrayAlternate]
    type: Literal["object"] = "object"
    field: Literal["dropdownlist"] = "dropdownlist"

    class Config:
        title = "Media Position"


class OptionMediaPlain(Config):
    name: Literal["Plain"] = "Plain"
    value: Literal["0"] = "0"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "Plain"


class OptionMediaPhoto(Config):
    name: Literal["Photo"] = "Photo"
    value: Literal["1"] = "1"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "Photo"


class ConfigMediaType(Config):
    """MediaType. Photo lets the printer raise quality / reduce droplet size."""
    name: Literal["ConfigMediaType"] = "ConfigMediaType"
    group: Literal["PrintJob"] = "PrintJob"
    value: Union[OptionMediaPlain, OptionMediaPhoto]
    type: Literal["object"] = "object"
    field: Literal["dropdownlist"] = "dropdownlist"

    class Config:
        title = "Media Type"


# --- Image encoding parameters ----------------------------------------------
class ConfigQuality(Config):
    """Lossy encoding quality (JPEG/WEBP), 1-100."""
    name: Literal["ConfigQuality"] = "ConfigQuality"
    value: int = Field(default=90, ge=1, le=100)
    type: Literal["number"] = "number"
    field: Literal["textInput"] = "textInput"

    class Config:
        title = "Quality"


class ConfigCompression(Config):
    """PNG compression level, 0 (fast) - 9 (smallest)."""
    name: Literal["ConfigCompression"] = "ConfigCompression"
    value: int = Field(default=6, ge=0, le=9)
    type: Literal["number"] = "number"
    field: Literal["textInput"] = "textInput"

    class Config:
        title = "Compression Level"


# ---------------------------------------------------------------------------
# Target format options (dependentDropdownlist)
#
# Each option's `value` is the format key the executor reads. Options that need
# extra settings attach them as dependent sub-fields, which the web form reveals
# only when that format is selected.
# ---------------------------------------------------------------------------
class OptionPdf(Config):
    name: Literal["pdf"] = "pdf"
    value: Literal["pdf"] = "pdf"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "PDF"


class OptionDocx(Config):
    name: Literal["docx"] = "docx"
    value: Literal["docx"] = "docx"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "DOCX"


class OptionTxt(Config):
    name: Literal["txt"] = "txt"
    value: Literal["txt"] = "txt"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "TXT"


class OptionPng(Config):
    name: Literal["png"] = "png"
    configCompression: ConfigCompression
    value: Literal["png"] = "png"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "PNG"


class OptionJpg(Config):
    name: Literal["jpg"] = "jpg"
    configQuality: ConfigQuality
    value: Literal["jpg"] = "jpg"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "JPG"


class OptionWebp(Config):
    name: Literal["webp"] = "webp"
    configQuality: ConfigQuality
    value: Literal["webp"] = "webp"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "WEBP"


class OptionApplicationPdf(Config):
    name: Literal["applicationPdf"] = "applicationPdf"
    value: Literal["application/pdf"] = "application/pdf"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "PDF (application/pdf)"


class OptionPwgRaster(Config):
    name: Literal["pwgRaster"] = "pwgRaster"
    configResolution: ConfigResolution
    configPageSize: ConfigPageSize
    configColorSpace: ConfigColorSpace
    configDuplex: ConfigDuplex
    configMediaPosition: ConfigMediaPosition
    configMediaType: ConfigMediaType
    value: Literal["image/pwg-raster"] = "image/pwg-raster"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "PWG Raster"


class OptionUrf(Config):
    name: Literal["urf"] = "urf"
    configResolution: ConfigResolution
    configPageSize: ConfigPageSize
    configColorSpace: ConfigColorSpace
    configDuplex: ConfigDuplex
    configMediaPosition: ConfigMediaPosition
    configMediaType: ConfigMediaType
    value: Literal["image/urf"] = "image/urf"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "Apple URF"


class OptionHpPcl(Config):
    name: Literal["hpPcl"] = "hpPcl"
    configResolution: ConfigResolution
    configPageSize: ConfigPageSize
    configColorSpace: ConfigColorSpace
    configDuplex: ConfigDuplex
    value: Literal["application/vnd.hp-pcl"] = "application/vnd.hp-pcl"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "HP PCL"


class OptionPcl(Config):
    name: Literal["pcl"] = "pcl"
    configResolution: ConfigResolution
    configPageSize: ConfigPageSize
    configColorSpace: ConfigColorSpace
    configDuplex: ConfigDuplex
    value: Literal["application/pcl"] = "application/pcl"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "PCL"


class OptionPostscript(Config):
    name: Literal["postscript"] = "postscript"
    value: Literal["application/postscript"] = "application/postscript"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "PostScript"


class OptionHpPclxl(Config):
    name: Literal["hpPclxl"] = "hpPclxl"
    configResolution: ConfigResolution
    configPageSize: ConfigPageSize
    configColorSpace: ConfigColorSpace
    configDuplex: ConfigDuplex
    value: Literal["application/vnd.hp-pclxl"] = "application/vnd.hp-pclxl"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "HP PCL-XL"


class OptionImageJpeg(Config):
    name: Literal["imageJpeg"] = "imageJpeg"
    configQuality: ConfigQuality
    value: Literal["image/jpeg"] = "image/jpeg"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "JPEG (image/jpeg)"


class OptionOctetStream(Config):
    name: Literal["octetStream"] = "octetStream"
    value: Literal["application/octet-stream"] = "application/octet-stream"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "Octet Stream"


class ConfigTargetFormat(Config):
    """
        Target format the source document will be converted into. Selecting a
        format reveals its format-specific parameters.
    """
    name: Literal["ConfigTargetFormat"] = "ConfigTargetFormat"
    value: Union[
        OptionPdf,
        OptionDocx,
        OptionTxt,
        OptionPng,
        OptionJpg,
        OptionWebp,
        OptionApplicationPdf,
        OptionPwgRaster,
        OptionUrf,
        OptionHpPcl,
        OptionPcl,
        OptionPostscript,
        OptionHpPclxl,
        OptionImageJpeg,
        OptionOctetStream,
    ]
    type: Literal["object"] = "object"
    field: Literal["dependentDropdownlist"] = "dependentDropdownlist"

    class Config:
        title = "Target Format"


# ---------------------------------------------------------------------------
# FromStorage file source (filePicker widget)
# ---------------------------------------------------------------------------
class StorageSource(Config):
    """
        Select a file from the storage to be converted.
    """
    name: Literal["storageSource"] = "storageSource"
    value: str = ""
    type: Literal["string"] = "string"
    field: Literal["filePicker"] = "filePicker"

    class Config:
        json_schema_extra = {
            "class": "\\portalium\\storage\\widgets\\FilePicker",
            "options": {
                "multiple": 0,
                "returnAttribute": ["name"],
                "name": "app::logo_wide"
            }
        }
        title = "Storage Source"


# ---------------------------------------------------------------------------
# FromInput executor: source file arrives through an input
# ---------------------------------------------------------------------------
class FromInputConfigs(Configs):
    configTargetFormat: ConfigTargetFormat


class FromInputInputs(Inputs):
    inputFile: InputFile


class FromInputOutputs(Outputs):
    outputFile: OutputFile


class FromInputRequest(Request):
    inputs: Optional[FromInputInputs] = None
    configs: FromInputConfigs

    class Config:
        json_schema_extra = {
            "target": "configs"
        }


class FromInputResponse(Response):
    outputs: FromInputOutputs


class FromInputExecutor(Config):
    name: Literal["FromInput"] = "FromInput"
    value: Union[FromInputRequest, FromInputResponse]
    type: Literal["object"] = "object"
    field: Literal["option"] = "option"

    class Config:
        title = "From Input"
        json_schema_extra = {
            "target": {
                "value": 0
            }
        }


# ---------------------------------------------------------------------------
# FromStorage executor: source file picked from storage via config
# ---------------------------------------------------------------------------
class FromStorageConfigs(Configs):
    storageSource: StorageSource
    configTargetFormat: ConfigTargetFormat


class FromStorageOutputs(Outputs):
    outputFile: OutputFile


class FromStorageRequest(Request):
    configs: FromStorageConfigs

    class Config:
        json_schema_extra = {
            "target": "configs"
        }


class FromStorageResponse(Response):
    outputs: FromStorageOutputs


class FromStorageExecutor(Config):
    name: Literal["FromStorage"] = "FromStorage"
    value: Union[FromStorageRequest, FromStorageResponse]
    type: Literal["object"] = "object"
    field: Literal["option"] = "option"

    class Config:
        title = "From Storage"
        json_schema_extra = {
            "target": {
                "value": 0
            }
        }


# ---------------------------------------------------------------------------
# Package wiring
# ---------------------------------------------------------------------------
class ConfigExecutor(Config):
    """
        Selects how the source file is provided to the converter.
    """
    name: Literal["ConfigExecutor"] = "ConfigExecutor"
    value: Union[FromInputExecutor, FromStorageExecutor]
    type: Literal["executor"] = "executor"
    field: Literal["dependentDropdownlist"] = "dependentDropdownlist"

    class Config:
        title = "Source Type"


class PackageConfigs(Configs):
    executor: ConfigExecutor


class PackageModel(Package):
    configs: PackageConfigs
    type: Literal["component"] = "component"
    name: Literal["FileConverter"] = "FileConverter"
