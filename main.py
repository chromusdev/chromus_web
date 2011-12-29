import random
import os
import md5
import urllib
import logging

import webapp2

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.api import memcache

from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template

import random
import json


class AppHandler(webapp.RequestHandler):
    def render_template(self, name, data):
        path = os.path.join(os.path.dirname(__file__), name)
        self.response.out.write(template.render(path, data))

    def render_json(self, data):
        response = json.dumps(data)

        callback = self.request.get('_callback') or self.request.get('callback')

        if callback:
            response = "%s(%s)" % (callback, response)

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(response)


class VkToken(db.Model):
    token   = db.StringProperty()
    rand_num = db.FloatProperty()
    

class TokenHandler(AppHandler):
    def get(self, action):
        if action == 'get':
            rand_num = random.random()
            entity = VkToken.all().order('rand_num').filter('rand_num >=', rand_num).get()

            if entity is None:
                entity = VkToken.all().order('rand_num').get()
            
            if entity is not None:
                self.render_json({ 'token': entity.token })
            else:
                self.render_json({ 'error': 'Tokens not found' })

        elif action == 'add':
            token = self.request.get('token')

            entity = VkToken(key_name = token)
            entity.rand_num = random.random()
            entity.token = token
            entity.put()

        elif action == 'delete':
            token = self.request.get('token')
            key = db.Key.from_path('VkToken', token)
            db.delete(key)


class PageHandler(AppHandler):
    def get(self, page = None):
        if page is None:
            page = "index"

        self.render_template(page+".html", {})


import cgi
import urllib
from google.appengine.ext import webapp
from google.appengine.api import urlfetch


class Proxy(AppHandler):
    def get(self):
        method = self.request.get('_method') or 'GET'
        url = self.request.get('_url')
        
        data = []

        for arg in self.request.arguments():
            if arg not in ['_method', '_url', '_callback']:
                data.append("%s=%s" % (arg, self.request.get(arg)))

        data = "&".join(data)

        if method is 'GET':
            url = url + '?' + data
            payload = None
        else:
            payload = data


        result = urlfetch.fetch(url=url, method=getattr(urlfetch, method), payload = payload, follow_redirects = False)

        self.render_json({ 'response': result.content, 'method': method, 'payload': payload, 'headers':dict(result.headers), 'status_code':result.status_code })


app = webapp2.WSGIApplication(
    [
        (r'/', PageHandler),
        (r'/api/token/([^/]+)', TokenHandler),
        (r'/page/([^/]+)', PageHandler),
        (r'/proxy', Proxy)
    ],
debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
