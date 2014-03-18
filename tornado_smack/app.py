"""
    smack.app
    ~~~~~~~~~

    debug interface stolen from: https://gist.github.com/rduplain/4983839
"""

import tornado.ioloop
import tornado.web
import tornado.wsgi
import contextlib
import functools
from tornado.stack_context import StackContext
from functools import partial
from werkzeug.routing import Map, Rule, _rule_re
import os
import inspect
from werkzeug.local import LocalStack, LocalProxy
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

def _lookup_handler_object(name):
    top = _handler_ctx_stack.top
    if top is None:
        raise RuntimeError('working outside of request context')
    return top

_handler_ctx_stack = LocalStack()

"""
proxy to the current request handler object.
"""
handler = LocalProxy(partial(_lookup_handler_object, 'handler'))

@contextlib.contextmanager
def ctx_man(ctx):
    _handler_ctx_stack.push(ctx)
    yield
    _handler_ctx_stack.pop()


def get_current_traceback():
    "Get the current traceback in debug mode, using werkzeug debug tools."
    # Lazy import statement, as debugger is only used in development.
    from werkzeug.debug.tbtools import get_current_traceback
    # Experiment with skip argument, to skip stack frames in traceback.
    traceback = get_current_traceback(skip=2, show_hidden_frames=False,
                                      ignore_system_exceptions=True)
    return traceback

class DebuggableHandler(tornado.web.RequestHandler):

    def initialize(self):
        if isinstance(self.application, DebugApplication):
            self.get_error_html = self.get_debugger_html

    def get_debugger_html(self, status_code, **kwargs):
        assert isinstance(self.application, DebugApplication)
        traceback = self.application.get_current_traceback()
        keywords = self.application.get_traceback_renderer_keywords()
        html = traceback.render_full(**keywords).encode('utf-8', 'replace')
        return html.replace(b'WSGI', b'tornado')

class DebugApplication(tornado.web.Application):
    "Tornado Application supporting werkzeug interactive debugger."

    # This supports get_error_html in Handler above.

    def __init__(self, *args, **kwargs):
        from werkzeug.debug import DebuggedApplication
        self.debug_app = DebuggedApplication(self.debug_wsgi_app, evalex=True)
        self.debug_container = tornado.wsgi.WSGIContainer(self.debug_app)
        super(DebugApplication, self).__init__(*args, **kwargs)

    def __call__(self, request):
        if '__debugger__' in request.uri:
            # Do not call get_current_traceback here, as this is a follow-up
            # request from the debugger. DebugHandler loads the traceback.
            return self.debug_container(request)
        return super(DebugApplication, self).__call__(request)

    @classmethod
    def debug_wsgi_app(cls, environ, start_response):
        "Fallback WSGI application, wrapped by werkzeug's debug middleware."
        status = '500 Internal Server Error'
        response_headers = [('Content-type', 'text/plain')]
        start_response(status, response_headers)
        return ['Failed to load debugger.\n']

    def get_current_traceback(self):
        "Get the current Python traceback, keeping stack frames in debug app."
        traceback = get_current_traceback()
        for frame in traceback.frames:
            self.debug_app.frames[frame.id] = frame
        self.debug_app.tracebacks[traceback.id] = traceback
        return traceback

    def get_traceback_renderer_keywords(self):
        "Keep consistent debug app configuration."
        # DebuggedApplication generates a secret for use in interactions.
        # Otherwise, an attacker could inject code into our application.
        # Debugger gives an empty response when secret is not provided.
        return dict(evalex=self.debug_app.evalex, secret=self.debug_app.secret)

class TemplateProxy(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

def render_template(*args, **kwargs):
    return TemplateProxy(*args, **kwargs)


class App(object):

    """

    Example usage::

        from tornado_smack import App

        app = App(debug=True)

        @app.route("/hello")
        def foo():
            return "hello"

    :param debug: enables werkzeug debugger
    :param template_path: we normally look for template in ./templates folder of your app.py
                          you can explicitly set for some other template path
    """
    def __init__(self, debug=False, template_path=None):
        self.registery = {}
        self.url_map = Map()
        self.mapper = self.url_map.bind("", "/")
        self.debug = True
        self.methods = []
        if not template_path:
            frames = inspect.getouterframes(inspect.currentframe())
            frame,filename,line_number,function_name,lines,index = frames[0]
            for frame in frames:
                if filename != frame[1]:
                    filename = frame[1]
                    break
            self.template_path = os.path.realpath(os.path.join(os.path.dirname(filename), 'templates'))
        else:
            self.template_path = template_path

    def get_routes(self):
        """
        returns our compiled routes and classes as a list to be used in tornado
        """
        self.registery = {}
        for rule in self.methods:
            self.route_(**rule)
        return [(k, v) for k, v in self.registery.iteritems()]

    def is_werkzeug_route(self, route):
        """
        does it look like a werkzeug route or direct reg exp. of
        tornado.
        """
        return _rule_re.match(route)

    def route(self, rule, methods=None, werkzeug_route=None, tornado_route=None, handler_bases=None, nowrap=None):
        """
        our super handy dandy routing function, usually you create an application,
        and decorate your functions so they become RequestHandlers::

                    app = App()

                    @app.route("/hello")
                    def hello():
                        return "foo"

        :param rule: this can be either a werkzeug route or a reg.expression as in tornado.
                     we try to understand the type of it automatically - wheter werkzeug or reg.exp. -
                     this by checking with a regexp. If it is a werkzeug route, we simply get the compiled
                     reg. exp from werkzeug and pass it to tornado handlers.

        :param methods: methods can be a combination of ['GET', 'POST', 'HEAD', 'PUT'...]
                        any http verb that tornado accepts. Behind the scenes we create a class
                        and attach these methods.

                        for example something like::

                            class HelloHandler(tornado.web.RequestHandler):
                                def get(self):


        :param werkzeug_route: we explicitly tell that this is a werkzeug route, in case auto detection fails.
        :param tornado_route: we explicitly tell that this is a tornado reg. exp. route
        :param handler_bases: for debug we create DebuggableHandler, and for normal operations we create
                                tornado.web.RequestHandler but in case you want to use your own classes for request
                                handling, you can pass it with handler_bases parameter. So behind the scenes this::

                                    @route("/foo", handler_bases=(MyHandler,))
                                    def foo():
                                        pass

                                becomes this::

                                    class HelloHandler(MyHandler):
                                        def get(self):
                                            ...

        :param nowrap: if you add use self - or handler - as your first parameter::

                            @route('/foo')
                            def foo(self):
                                self.write("hello")

                        if becomes something like this::

                            class HelloHandler(tornado.web.RequestHandler):
                                def get(self):
                                    self.write("hello")

                        if you omit self as your first parameter::

                            @route('/foo')
                            def foo():
                                return "hello"

                        we implicitly wrap foo so it becomes something like this::

                            class HelloHandler(tornado.web.RequestHandler):
                                def get(self, *args, **kwargs):
                                    def wrapper(*args, **kwargs):
                                        return foo(*args, **kwargs)
                                    wrapper(*args, **kwargs)

                        in case you want to use some other name for your first parameter,
                        or for some other reason you can explicitly say don't wrap.

                        in case you are using tornado.coroutine or some other tornado decorator,
                        we don't wrap your function - because simply it won't work. so this::

                            @route('/foo')
                            @coroutine
                            def foo():
                                ...

                        will give you an error.

        """
        def inner(fn):
            self.methods.append(dict(
                rule=rule,
                 methods=methods,
                 werkzeug_route=werkzeug_route,
                 tornado_route=tornado_route,
                 handler_bases=handler_bases,
                 fn=fn,
                 nowrap=nowrap
            ))
            return fn
        return inner

    def route_(self, rule, methods=None, werkzeug_route=None,
                    tornado_route=None, handler_bases=None, fn=None, nowrap=None):
        if not methods:
            methods = ['GET']

        clsname = '%sHandler' % fn.__name__.capitalize()
        if not handler_bases:
            if self.debug:
                bases = (DebuggableHandler,)
            else:
                bases = (tornado.web.RequestHandler,)
        else:
            bases = handler_bases
        m = {}
        for method in methods:
            inspected = inspect.getargspec(fn)

            can_be_wrapped = True
            if nowrap == None:
                # are we using a tornado.coroutine or something similar,
                # we dont wrap
                if 'tornado' in inspect.getsourcefile(fn):
                    can_be_wrapped = False
                else:
                    can_be_wrapped = nowrap != True
            else:
                can_be_wrapped = nowrap

            self_in_args = inspected.args and inspected.args[0] in ['self', 'handler']

            if not self_in_args and can_be_wrapped==True:
                def wrapper(self, *args, **kwargs):
                    with StackContext(functools.partial(ctx_man, self)) as cm:
                        w = fn #wrap(fn)
                        result = w(*args, **kwargs)
                    if isinstance(result, TemplateProxy):
                        self.render(*result.args, **result.kwargs)
                    else:
                        self.finish(result)
                m[method.lower()] = wrapper
            else:
                m[method.lower()] = fn
        klass = type(clsname, bases, m)

        use_werkzeug_route = None

        if tornado_route:
            use_werkzeug_route = False

        if werkzeug_route:
            use_werkzeug_route = True

        if use_werkzeug_route == None:
            use_werkzeug_route = self.is_werkzeug_route(rule)

        if use_werkzeug_route:
            r = Rule(rule, methods=methods)
            self.url_map.add(r)
            r.compile()
            pattern = r._regex.pattern.replace('^\\|', "")
            self.registery[pattern] = klass
        else:
            self.registery[rule] = klass

    def run(self, port=8888, **settings):
        self.debug = settings.get('debug', False)
        template_path = settings.get('template_path')
        if not template_path:
            settings['template_path'] = self.template_path
        if self.debug:
            application = DebugApplication(self.get_routes(), **settings)
        else:
            application = tornado.web.Application(self.get_routes(), **settings)
        logger.info("starting server on port: %s", port)
        application.listen(port)
        tornado.ioloop.IOLoop.instance().start()
