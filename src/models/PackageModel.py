from typing import Optional, Union, Literal, List
from pydantic import BaseModel, validator

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
)


# ---------------------------------------------------------------------------
# Data carrier
# ---------------------------------------------------------------------------
# There is no native "File" Nova type, so we define a lightweight model that
# mirrors the metadata other packages expose for media. The converted file is
# written to /storage and only its path + metadata travel in the response, so a
# downstream FileSave package can pick it up from disk.
class File(BaseModel):
    uID: Optional[str] = None
    name: str
    path: str
    mimeType: str
    encoding: Optional[str] = None


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
class InputFile(Input):
    name: Literal["inputFile"] = "inputFile"
    value: Union[List[File], File]
    type: str = "object"

    @validator("type", pre=True, always=True)
    def set_type_based_on_value(cls, value, values):
        value = values.get("value")
        if isinstance(value, File):
            return "object"
        elif isinstance(value, list):
            return "list"

    class Config:
        title = "File"


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
class OutputFile(Output):
    name: Literal["outputFile"] = "outputFile"
    value: Union[List[File], File]
    type: str = "object"

    @validator("type", pre=True, always=True)
    def set_type_based_on_value(cls, value, values):
        value = values.get("value")
        if isinstance(value, File):
            return "object"
        elif isinstance(value, list):
            return "list"

    class Config:
        title = "File"


# ---------------------------------------------------------------------------
# Target format options (dropdownlist)
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
    value: Literal["png"] = "png"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "PNG"


class OptionJpg(Config):
    name: Literal["jpg"] = "jpg"
    value: Literal["jpg"] = "jpg"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "JPG"


class OptionWebp(Config):
    name: Literal["webp"] = "webp"
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
    value: Literal["image/pwg-raster"] = "image/pwg-raster"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "PWG Raster"


class OptionUrf(Config):
    name: Literal["urf"] = "urf"
    value: Literal["image/urf"] = "image/urf"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "Apple URF"


class OptionHpPcl(Config):
    name: Literal["hpPcl"] = "hpPcl"
    value: Literal["application/vnd.hp-pcl"] = "application/vnd.hp-pcl"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "HP PCL"


class OptionPcl(Config):
    name: Literal["pcl"] = "pcl"
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
    value: Literal["application/vnd.hp-pclxl"] = "application/vnd.hp-pclxl"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"

    class Config:
        title = "HP PCL-XL"


class OptionImageJpeg(Config):
    name: Literal["imageJpeg"] = "imageJpeg"
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
        Target format the source document will be converted into.
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
    field: Literal["dropdownlist"] = "dropdownlist"

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
