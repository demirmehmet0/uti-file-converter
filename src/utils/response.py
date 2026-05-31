
from sdks.novavision.src.helper.package import PackageHelper
from components.FileConverter.src.models.PackageModel import (
    PackageModel,
    PackageConfigs,
    ConfigExecutor,
    OutputFile,
    FromInputExecutor,
    FromInputResponse,
    FromInputOutputs,
    FromStorageExecutor,
    FromStorageResponse,
    FromStorageOutputs,
)


def build_response_from_input(context):
    output_file = OutputFile(value=context.file)
    outputs = FromInputOutputs(outputFile=output_file)
    response = FromInputResponse(outputs=outputs)
    executor = FromInputExecutor(value=response)
    config_executor = ConfigExecutor(value=executor)
    package_configs = PackageConfigs(executor=config_executor)
    package = PackageHelper(packageModel=PackageModel, packageConfigs=package_configs)
    return package.build_model(context)


def build_response_from_storage(context):
    output_file = OutputFile(value=context.file)
    outputs = FromStorageOutputs(outputFile=output_file)
    response = FromStorageResponse(outputs=outputs)
    executor = FromStorageExecutor(value=response)
    config_executor = ConfigExecutor(value=executor)
    package_configs = PackageConfigs(executor=config_executor)
    package = PackageHelper(packageModel=PackageModel, packageConfigs=package_configs)
    return package.build_model(context)
