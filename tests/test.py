from tornado_smack import App
from tornado_smack.app import handler
import unittest
import re
import requests
import time
from multiprocessing import Process
from tornado.gen import coroutine
from tornado.httpclient import AsyncHTTPClient
import json

import logging
logging.basicConfig(level=logging.DEBUG)


req_cnt = 0
statuses = {}

def wait_until(fn, timeout=15):
    t = timeout
    while True:
        if fn():
            break
        print "sleeping", t
        time.sleep(1)
        t -= 1
        if t < 0:
            raise Exception('timeout waiting function')


class TestRouting(unittest.TestCase):

    def test_route(self):
        app = App()
        assert not app.is_werkzeug_route(r"/entry/([^/]+)")
        assert app.is_werkzeug_route(r'/foo/<int:year>')
        assert app.is_werkzeug_route(r'/foo/<year>')

    def test_proxy_method(self):
        """
        we create two servers, and we'll make them sleep with different times.
        then we create our app, which makes a request to those sleeping servers,
        then we send multiple requests to our app, and see if everything went well
        """
        app2 = App()

        @app2.route("/wait/<t>/<id>")
        def wait(self, t, id):
            import time
            time.sleep(int(t))
            self.write({"waited": t, "id": id})

        p1 = Process(target=app2.run, kwargs={'port': 8889, 'debug':True})
        p1.start()

        p2 = Process(target=app2.run, kwargs={'port': 8890, 'debug':True})
        p2.start()

        # now we create a server for ourselves...
        app = App()

        @app.route("/statuses")
        def get_statuses():
            return statuses

        @app.route("/somejson", nowrap=True)
        def somejson():
            global req_cnt, statuses
            req_cnt += 1
            handler.req_cnt = req_cnt
            statuses[req_cnt] = None
            @coroutine
            def w():
                http_client = AsyncHTTPClient()
                if req_cnt % 2 == 0:
                    response = yield http_client.fetch("http://localhost:8889/wait/%s/%s" % (5, req_cnt))
                else:
                    response = yield http_client.fetch("http://localhost:8890/wait/%s/%s" % (1, req_cnt))
                # we wait until the request complete, though at the same time we make more requests,
                # the first req. completes later than the second. we'll see if we can keep the context
                resp_result = json.loads(response.body)
                status = resp_result['id'] == str(handler.req_cnt)
                statuses[handler.req_cnt] = status
            w()
            return {'req': handler.req_cnt}

        p3 = Process(target=app.run, kwargs={'debug':True})
        p3.start()
        time.sleep(1)

        try:
            waiting_statuses = []
            for i in range(1,5):
                r1 = requests.get('http://localhost:8888/somejson')
                waiting_statuses.append(json.loads(r1.content))

            def wait_all_complete():
                r2 = requests.get('http://localhost:8888/statuses')
                results = json.loads(r2.content)
                print results
                if len(results) == 4:
                    all_true = True
                    for i in range(1,5):
                        if results[str(i)] != True:
                            all_true = False
                    if all_true:
                        return all_true

            wait_until(wait_all_complete, 50)

        finally:
            p1.terminate()
            p2.terminate()
            p3.terminate()


    def test_add_route(self):

        app = App()

        @app.route("/foo")
        def foo2(self):
            self.write('foo2')

        @app.route("/foo/<slug>")
        def foo(self, slug):
            self.write(slug)

        @app.route("/get/<int:id>/<int:w>")
        def get(self, id, w):
            self.write(id)

        @app.route("/post/<id>", methods=['POST'])
        def postmethod(self, id):
            self.write(id)

        from multiprocessing import Process
        p = Process(target=app.run, kwargs={'debug':True})
        p.start()
        time.sleep(1)
        try:
            r = requests.get('http://localhost:8888/foo/bar')
            assert r.content == 'bar'
            r = requests.get('http://localhost:8888/foo')
            assert r.content == 'foo2'
            r = requests.get('http://localhost:8888/get/1/2')
            assert r.content == '1'

            r = requests.get('http://localhost:8888/post/1')
            assert r.status_code == 405
            r = requests.post('http://localhost:8888/post/1', {'c':1})
            assert r.content == '1'
        finally:
            p.terminate()


if __name__ == '__main__':
    unittest.main()