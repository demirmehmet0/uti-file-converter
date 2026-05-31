
import os
import sys
import uuid

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from sdks.novavision.src.base.component import Component
from sdks.novavision.src.helper.executor import Executor
from components.FileConverter.src.models.PackageModel import PackageModel, File
from components.FileConverter.src.utils.response import build_response_from_storage
from components.FileConverter.src.utils.utils import convert_file, download_from_storage


class FromStorage(Component):
    def __init__(self, request, bootstrap):
        super().__init__(request, bootstrap)
        self.request.model = PackageModel(**(self.request.data))
        self.storage_id = self.request.get_param("storageSource")
        self.target_format = self.request.get_param("ConfigTargetFormat")
        self.file = None

    @staticmethod
    def bootstrap(config: dict) -> dict:
        return {}

    def run(self):
        source_path = download_from_storage(self.storage_id)
        result = convert_file(source_path, self.target_format)
        self.file = File(
            uID=str(uuid.uuid4()),
            name=result["name"],
            path=result["path"],
            mimeType=result["mimeType"],
            encoding="bytes",
        )
        return build_response_from_storage(context=self)


if "__main__" == __name__:
    Executor(sys.argv[1]).run()
