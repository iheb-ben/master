from app import api
from flask_restx import Namespace, Resource

commit_ns: Namespace = api.namespace(name='Commits', path='/commits', description='Commit management operations')


# noinspection PyMethodMayBeStatic
@commit_ns.route('/webhook')
class WebHook(Resource):
    def post(self):
        print(commit_ns.payload)
        return {'message': 'Commit was added'}, 200
