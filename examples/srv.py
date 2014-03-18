import tornado.ioloop
import tornado.web
# from flask import render_template, request, ctx
from functools import wraps
from tornado.gen import coroutine
from tornado.httpclient import AsyncHTTPClient

from tornado_smack import App, render_template
from tornado_smack.app import handler
from tornado.stack_context import StackContext, wrap
import time

app2 = App()

@app2.route("/wait/<t>/<id>")
def wait(self, t, id):
    import time
    time.sleep(int(t))
    self.write({"waited": t, "id": id})

from multiprocessing import Process
p = Process(target=app2.run, kwargs={'port': 8889, 'debug':True})
p.start()

p2 = Process(target=app2.run, kwargs={'port': 8890, 'debug':True})
p2.start()

app = App()
import tornado_smack.app
tornado_smack.app.c = 0

req_cnt = 0

@app.route("/somejson", nowrap=True)
def somejson():
    global req_cnt
    req_cnt += 1
    handler.req_cnt = req_cnt
    print ">>> sending ", handler, handler.req_cnt
    @coroutine
    def w():
        http_client = AsyncHTTPClient()
        if req_cnt % 2 == 0:
            response = yield http_client.fetch("http://localhost:8889/wait/%s/%s" % (5, req_cnt))
        else:
            response = yield http_client.fetch("http://localhost:8890/wait/%s/%s" % (1, req_cnt))
        print ">>>> response >>>", response, response.body, handler, handler.req_cnt
    w()
    return {'a':1}

@app.route("/foobar")
def foobar():
    return "hello world"

@app.route("/foobar/<id>")
def foobar2(id):
    return "hello world %s" % id

@app.route("/othertemplate")
def sometemplate(self):
    self.render("example.html", students=[{'name': 'a'}], title="hello")

@app.route("/template")
def someothertemplate():
    return render_template("example.html", students=[{'name': 'a'}], title="hello")

@app.route('/foo/<id>')
def foo(self, id):
    if str(id)=='3':
        raise Exception('- 3 -')
    self.write("foo - %s" % id)

@app.route('/async', methods=['GET', 'HEAD'])
@coroutine
def homepage(self):
    http_client = AsyncHTTPClient()
    response = yield http_client.fetch("https://google.com/")
    self.write(response.body)

if __name__ == "__main__":
    app.run(debug=True)