import random
import os
import md5
import urllib
import logging

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.api import memcache

from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template

import simplejson as json

class AppHandler(webapp.RequestHandler):
    def render_template(self, name, data):
        path = os.path.join(os.path.dirname(__file__), name)
        self.response.out.write(template.render(path, data))

    def render_json(self, data):
        response = json.dumps(data)

        if self.request.get('callback'):
            response = "%s(%s)" % (self.request.get('callback'), response)

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(response)

class VkKey(db.Model):
    user_id = db.IntegerProperty()
    api_key = db.IntegerProperty()
    secret = db.StringProperty(indexed = False)
    comment = db.StringProperty(indexed = False)

    @classmethod
    def keys(self):
        vk_keys = memcache.get('vk_keys')

        if vk_keys is None:
            vk_keys = self.all().fetch(100)
            memcache.set('vk_keys', vk_keys)

        return vk_keys


    @classmethod
    def get_key(self):
        keys = VkKey.keys()

        try:
            vk_key = random.choice(keys)
        except IndexError:
            vk_key = None

        memcache.incr(str(vk_key.key()), 1, None, 0)

        return vk_key


class VkKeyStat(db.Model):
    count  = db.IntegerProperty()
    created_at = db.DateTimeProperty(auto_now_add = True)


class UpdateKeyStats(AppHandler):
    def get(self):
        keys = VkKey.all().fetch(100)

        for vk_key in keys:
            count = memcache.get(str(vk_key.key()))

            if count is None:
                count = 0

            VkKeyStat(parent = vk_key, count = int(count)).put()

            memcache.delete(str(vk_key.key()))


class KeysList(AppHandler):
    def get(self):
        keys = VkKey.all().fetch(100)

        for vk_key in keys:
            stat = VkKeyStat.all().order('-created_at').ancestor(vk_key).get()

            if stat:
                vk_key.qps = stat.count/600.0 # 600 = 10 minutes
                vk_key.count = stat.count

        self.render_template("keys.html", {'keys':keys})


class KeyGraph(AppHandler):
    def get(self, vk_key):
        stat = VkKeyStat.all().order('-created_at').ancestor(db.Key(vk_key)).fetch(10)
        stat.reverse()

        chart_str = ",".join([str(s.count) for s in stat])

        self.redirect("http://chart.apis.google.com/chart?cht=lc&chs=300x50&chd=t:%s" % chart_str)


class AddKey(AppHandler):
    def post(self):
        key = VkKey()

        key.api_key = int(self.request.get('api_key'))
        key.user_id = int(self.request.get('user_id'))
        key.secret = self.request.get('secret')
        key.comment = self.request.get('comment')

        key.put()

        self.redirect('/keys')


class DeleteKey(AppHandler):
    def get(self, key):
        db.delete(key)

        self.redirect('/keys')


class SignData(AppHandler):
    def post(self):
        vk_key = VkKey.get_key()

        track = self.request.get('track')
        track = urllib.unquote_plus(urllib.unquote(track))

        logging.info("Track: %s" % track)

        substs = (vk_key.user_id, vk_key.api_key, self.request.get('callback'), track, vk_key.secret)

        md5_string = "%sapi_id=%scallback=%scount=10format=jsonmethod=audio.searchq=%ssort=2test_mode=1%s" % substs

        signed_data = md5.new(md5_string.encode('utf-8')).hexdigest()

        self.render_json({'api_key':vk_key.api_key, 'signed_data':signed_data, 'sign_string': md5_string})

    def get(self):
        self.post()


class MainPage(AppHandler):
    def get(self):
        self.render_template("index.html", {});

class PageHandler(AppHandler):
    def get(self, page):
        self.render_template(page+".html", {});


class VkInvite(AppHandler):
    def get(self, page):
        self.render_template("vk_invites.html")


application = webapp.WSGIApplication(
                                     [
                                      ('/', MainPage),
                                      ('/page/([^/]+)', PageHandler),
                                      ('/sign_data', SignData),
                                      ('/keys', KeysList),
                                      ('/keys/add', AddKey),
                                      ('/keys/update_stats', UpdateKeyStats),
                                      ('/key/([^/]+)?/delete', DeleteKey),
                                      ('/key/([^/]+)?/stat.png', KeyGraph)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
