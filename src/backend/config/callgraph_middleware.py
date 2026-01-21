# -*- encoding: UTF-8 -*-
import time
from django.conf import settings
from django.urls import resolve

from pycallgraph import Config
from pycallgraph import PyCallGraph
from pycallgraph.output import GraphvizOutput
from pycallgraph import GlobbingFilter


# New in Django 1.10
class CallgraphMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    # __call__ method is called when the instance is called (treating an instance as a function)
    def __call__(self, request):

        # Code to be executed for each request before
        # the view (and later middleware) are called.
        if settings.DEBUG and self.to_debug(request):
            config = Config()
            config.trace_filter = GlobbingFilter(include=['contracts.*'], exclude=[])
            graphviz = GraphvizOutput(output_file='callgraph-' + str(time.time()) + '.svg', output_type='svg')  # or 'png'
            pycallgraph = PyCallGraph(output=graphviz, config=config)
            pycallgraph.start()
            # noinspection PyAttributeOutsideInit
            self.pycallgraph = pycallgraph

            response = self.get_response(request)
            # Code to be executed for each request/response after
            # the view is called.

            self.pycallgraph.done()
        else:
            response = self.get_response(request)

        return response


    @staticmethod
    def to_debug(request):
        method = request.method
        if method == 'GET' and 'graph' in request.GET:
            return True
        url_path = request.path
        url_name = getattr(resolve(url_path), 'url_name', None)
        urls = getattr(settings, 'CALL_GRAPH_URLS', None)
        for url in urls:
            if url.get('name', None) is url_name and method in url.get('methods', None):
                return True
        return False