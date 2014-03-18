.. tornado-smack documentation master file, created by
   sphinx-quickstart on Mon Mar 17 19:01:25 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Tornado-Smack
=========================================

Syntactic sugar for tornado
----------------------------

Turns your application from this::


    class MainHandler(tornado.web.RequestHandler):
        def get(self, name):
            self.write("Hello, world %s " % name)

    application = tornado.web.Application([
        (r"^/foobar/(\w+)/?$", MainHandler),
    ])

    if __name__ == "__main__":
        application.listen(8888)
        tornado.ioloop.IOLoop.instance().start()

to this::

    from tornado_smack import App

    app = App()

    @app.route("/foobar/<name>")
    def foobar(name):
        return "hello world %s" % name

    if __name__ == "__main__":
        app.run(debug=True)

Using templates
---------------------
you can use ./templates folder - default path - and return a template easily like this::

    from tornado_smack import render_template
    @app.route("/foobar/<name>")
    def foobar(name):
        return render_template('foobar.html', name=name)


Using Async. Handlers
---------------------
also for your async pleasure, you can do this::

    @app.route('/async', methods=['GET', 'HEAD'])
    @coroutine
    def homepage(self):
        http_client = AsyncHTTPClient()
        response = yield http_client.fetch("https://google.com/")
        self.write(response.body)

Using Smack with Tornado together
----------------------------------
you can always use them together like this::

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


Installation
-----------------

You can install it with pip::

    pip install tornado_smack


Api Documentation
------------------

.. autoclass:: tornado_smack.app.App
    :members:


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

