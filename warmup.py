from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.api import memcache

from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template

def main():
    print "Content-type: text/plain"
    print "OK"
