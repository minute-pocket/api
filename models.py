# -*- coding:utf-8 -*-
from google.appengine.ext import ndb


class Settings(ndb.Model):
    name = ndb.StringProperty()
    value = ndb.StringProperty()

    @staticmethod
    def get(name, default=None):
        retval = Settings.query(Settings.name == name).get()
        if retval:
            return retval.value

        retval = Settings()
        retval.name = name
        retval.value = default or "UNSET"
        retval.put()

        return default


class Account(ndb.Model):
    username = ndb.StringProperty(indexed=True)
    email = ndb.StringProperty(indexed=True, default=None)
    access_token = ndb.StringProperty(indexed=False)
    created = ndb.DateTimeProperty(auto_now_add=True)

    @classmethod
    def find_by_username(cls, username):
        return cls.query().filter(cls.username == username).get()
