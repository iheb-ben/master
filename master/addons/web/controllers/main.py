from master.core.service.http import route, Controller


class MainC(Controller):
    @route('/')
    def test(self):
        return 'test'
