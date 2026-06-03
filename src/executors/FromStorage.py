
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from sdks.novavision.src.base.component import Component
from sdks.novavision.src.helper.executor import Executor
from sdks.novavision.src.media.file import BinaryFile
from components.FileConverter.src.models.PackageModel import PackageModel
from components.FileConverter.src.utils.response import build_response_from_storage
from components.FileConverter.src.utils.utils import convert_file, download_from_storage, build_options


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
        options = build_options(self.request, self.target_format)
        result = convert_file(source_path, self.target_format, options)

        with open(result["path"], "rb") as f:
            content = f.read()

        self.file = BinaryFile.create(
            name=result["name"],
            mime_type=result["mimeType"],
            value=content,
        )
        self.file = BinaryFile.set_frame(
            self.file, package_uid=self.uID, redis_db=self.redis_db
        )

        try:
            os.remove(result["path"])
        except OSError:
            pass

        return build_response_from_storage(context=self)


if "__main__" == __name__:
    Executor(sys.argv[1]).run()
