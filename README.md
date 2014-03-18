tornado-smack
=====================

Syntactic sugar for tornado
----------------------------

Turns your application from this:

```python
class MainHandler(tornado.web.RequestHandler):
    def get(self, name):
        self.write("Hello, world %s " % name)

application = tornado.web.Application([
    (r"^/foobar/(\w+)/?$", MainHandler),
])

if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
```

to this:

```python
app = App()

@app.route("/foobar/<name>")
def foobar(name):
    return "hello world %s" % name

if __name__ == "__main__":
    app.run(debug=True)
```

using templates is easy

```python
@app.route("/foobar/<name>")
def foobar(name):
    return render_template("foobar.html")
```


also for your async pleasure, you can do this,

```python
@app.route('/async', methods=['GET', 'HEAD'])
@coroutine
def homepage(self):
    http_client = AsyncHTTPClient()
    response = yield http_client.fetch("https://google.com/")
    self.write(response.body)
```

oh and yes, the debugger. we added werkzeug debugger too for development mode.

if you have an exception like this,

```python
@app.route('/foo/<id>')
def foo(self, id):
    if str(id)=='3':
        raise Exception('- 3 -')
    self.write("foo - %s" % id)
```

you can trace it like this.

![debugger](/docs/debugger.png)


also added proxy methods for self so you can do things like this easily

```python

# handler is always the current RequestHandler instance
from tornado_smack.app import handler

def api_method(fn):
    def wrapped(api_key, *args, **kwargs):
        handler.customer = Customer.load(api_key)
        handler.payload = json.loads(handler.request.body)
        return fn(*args, **kwargs)
    return wrapped

@app.route("/api/resize/<api_key>", methods=['POST'])
@api_method
def resize():
    """
    expects
    {'command': 'resize', 'width': 300, 'img_id': 123, 'name': 'blabla.jpg'}
    returns
    {'url': 'http://localhost:8888/12345/blabla.jpg', 'img_id': '12324354'}
    """
    # .... some code here ...
    return {'url': 'http://localhost:8888/img/%s/%s/%s' % (handler.payload['img_id'], cmd_md5, handler.payload['name']), 'img_id': handler.payload['img_id']}

```

Using with your existing application
------------------------------------

you can also combine tornado handlers with smack.

```python
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

```

Installation
-----------------------

You can install it with

```
pip install tornado_smack
```

Documentation
------------------------

Documentation lives here http://tornado-smack.readthedocs.org/en/latest/