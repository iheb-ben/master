from master.core.service.http import route, Controller


class MainA(Controller):
    @route('/')
    def test(self):
        return 'test'


class MainB(MainA):
    @route('/')
    def test(self):
        return 'test'
