from master.api import route
from master.core.endpoints import Controller
from master.core.parser import PipelineMode


class Main(Controller):
    @route('/pipeline/git/repository/<string:project>/<string:branch>/build', methods='GET', mode=PipelineMode.MANAGER.value)
    def _pipeline_build_project(self, project: str, branch: str):
        pass

    @route('/pipeline/git/repository/<string:project>/<string:branch>/commit/add', methods='POST', mode=PipelineMode.MANAGER.value)
    def _pipeline_add_commit(self, project: str, branch: str, hexsha: str, message: str, author: dict):
        pass

    @route('/pipeline/repository/<string:project>/<string:branch>/build', methods='GET', auth='user', mode=PipelineMode.MANAGER.value)
    def pipeline_build_project(self, *args, **kwargs):
        return self._pipeline_build_project(*args, **kwargs)

    @route('/pipeline/repository/<string:project>/<string:branch>/commit/add', methods='POST', auth='user', mode=PipelineMode.MANAGER.value)
    def pipeline_add_commit(self, *args, **kwargs):
        return self._pipeline_add_commit(*args, **kwargs)
