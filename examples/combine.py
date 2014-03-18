from tornado_smack import App
import tornado.web

app = App()

@app.route("/foobar/<id>")
def foobar2(id):
    return "hello world %s" % id

class MainHandler(tornado.web.RequestHandler):
    def get(self, name):
        self.write("Hello, world %s " % name)


application = tornado.web.Application([
    (r"^/foo/(\w+)/?$", MainHandler),
] + app.get_routes())


if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()

