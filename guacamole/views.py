from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import StreamingHttpResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from guacamole import client

import logging
import uuid
import threading


logger = logging.getLogger(__name__)
sockets = {}
sockets_lock = threading.RLock()
read_lock = threading.RLock()
write_lock = threading.RLock()
pending_read_request = threading.Event()


def index(request):
    return render_to_response('index.html',
                              {},
                              context_instance=RequestContext(request))


@csrf_exempt
def tunnel(request):
    qs = request.META['QUERY_STRING']
    logger.info('tunnel %s', qs)
    if qs == 'connect':
        return _do_connect(request)
    else:
        tokens = qs.split(':')
        if len(tokens) >= 2:
            if tokens[0] == 'read':
                return _do_read(request, tokens[1])
            elif tokens[0] == 'write':
                return _do_write(request, tokens[1])

    return HttpResponse(status=400)


def _do_connect(request):
    # Connect to guacd daemon
    guac = client.GuacamoleClient()
    guac.connect(protocol='vnc',
                 hostname='blargh.host.com',
                 port=5901,
                 password='password')
#     guac.connect(protocol='ssh',
#                  hostname='blargh.host.com',
#                  port=22,
#                  username='user',
#                  password='password')

    cache_key = str(uuid.uuid4())
    with sockets_lock:
        logger.info('Saving socket with key %s', cache_key)
        sockets[cache_key] = guac

    response = HttpResponse(content=cache_key)
    response['Cache-Control'] = 'no-cache'

    return response


def _do_read(request, cache_key):
    pending_read_request.set()

    def content():
        with sockets_lock:
            guac = sockets[cache_key]

        with read_lock:
            pending_read_request.clear()

            while True:
                content = guac.read()
                if content:
                    yield content
                else:
                    break

                if pending_read_request.is_set():
                    logger.info('Letting another request take over.')
                    break

            # End-of-instruction marker
            yield '0.;'

    response = StreamingHttpResponse(content(),
                                     content_type='application/octet-stream')
    response['Cache-Control'] = 'no-cache'
    return response


def _do_write(request, cache_key):
    with sockets_lock:
        guac = sockets[cache_key]

    with write_lock:
        while True:
            chunk = request.read(8192)
            if chunk:
                guac.write(chunk)
            else:
                break

    response = HttpResponse(content_type='application/octet-stream')
    response['Cache-Control'] = 'no-cache'
    return response
