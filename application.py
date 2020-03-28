# -*- coding:utf-8 -*-

from flask import Flask, url_for, redirect, session, request
from models import Account, Settings
from email.utils import parseaddr
from mailer import Mailgun


try:
    from frequests import requests
except:
    import requests

from google.appengine.api import taskqueue

import urllib, logging

Flask.secret_key = 'Some random key'  # import os; os.urandom(24)
Flask.template_folder = 'templates'

app = Flask(__name__)
consumer_key = Settings.get('POCKET_API_KEY')


@app.route('/')
def home():
    return redirect('https://minute-pocket.com/')


@app.route('/connect')
def connect():
    connect_url = url_for('authorize', _external=True)
    oauth = requests.post('https://getpocket.com/v3/oauth/request', json={
        'consumer_key': consumer_key,
        'redirect_uri': connect_url
    }, headers={'X-Accept': 'application/json'})

    if oauth.status_code != 200:
        logging.error(oauth.content)
        return "oups"

    code = oauth.json().get('code')
    session.clear()
    session['code'] = code

    return redirect("https://getpocket.com/auth/authorize?request_token={0}&redirect_uri={1}".format(code, urllib.quote(connect_url, safe='')))


@app.route('/authorize')
def authorize():
    oauth = requests.post('https://getpocket.com/v3/oauth/authorize', json={
        'consumer_key': consumer_key,
        'code': session.get('code')
    }, headers={'X-Accept': 'application/json'})

    if oauth.status_code != 200:
        logging.error(oauth.content)
        return redirect('https://minute-pocket.com/?status=unauthorized')

    result = oauth.json()
    session.pop('code', None)

    account = Account.find_by_username(result.get('username'))
    if not account:
        account = Account(**result)
    else:
        account.access_token = result.get('access_token')

    key = account.put()

    session['key'] = key.id()
    session['username'] = result.get('username')

    if account.email is not None:
        return redirect('https://minute-pocket.com/?status=authorized&email={0}'.format(urllib.quote(account.email)))
    else:
        return redirect('https://minute-pocket.com/?status=authorized')


@app.route('/queue', methods=['POST'])
def queue():
    email = request.form.get('email')
    parsed = parseaddr(email)
    if not parsed[1]:
        return redirect('https://minute-pocket.com/?status=authorized&error=email')

    account = Account.get_by_id(session.get('key'))
    account.email = email
    account.put()

    taskqueue.add(queue_name='process', params={'key': session.get('key')})
    return redirect('https://minute-pocket.com/?status=processing')


@app.route('/count-users')
def count_users():
    total = 0
    for key in Account.query().iter(keys_only=True):
        account = key.get()
        if account.email is not None:
            total = total + 1

    return str(total)


@app.route('/_ah/start')
def warmup():
    return 'ok'


durations = (2, 5, 10, 15, 20, 30, 45, 60)
limit = 100


@app.route('/_ah/queue/process', methods=['POST'])
def process():
    account_id = long(request.form.get('key'))
    account = Account.get_by_id(account_id)

    offset = int(request.form.get('offset', 0))
    updated = int(request.form.get('updated', 0))

    while True:
        result = requests.post('https://getpocket.com/v3/get', data={
            'consumer_key': consumer_key,
            'access_token': account.access_token,
            'state': 'unread',
            'sort': 'newest',
            'detailType': 'complete',
            'contentType': 'article',
            'count': limit,
            'offset': offset
        })

        if result.get_header('x-limit-key-remaining') == 0:
            taskqueue.add(
                queue_name='process',
                params={
                    'key': session.get('key'),
                    'offset': offset,
                    'updated': updated
                },
                countdown=result.get_header('x-limit-key-reset')
            )

            return 'paused ...'

        result.raise_for_status()

        items = result.json()

        if len(items['list']) == 0:
            break

        actions = []
        found_tags = 0
        for key in items.get('list'):
            item = items['list'].get(key)

            found_tag = False
            if item.get('tags', None):
                for tag in item.get('tags'):
                    if tag.find('minutes') > -1:
                        found_tag = True
                        break

            if found_tag:
                found_tags = found_tags + 1
                continue

            duration = (int(item.get('word_count')) / 275) * 60
            if item.get('image', None) is not None:
                duration = duration + (len(item.get('images')) * 12)

            duration = int(duration / 60)
            tag_name = None
            for d in durations:
                if duration <= d:
                    tag_name = '{0} minutes'.format(d)
                    break

            if tag_name is None:
                tag_name = '60+ minutes'

            actions.append({
                'action': 'tags_add',
                'item_id': item.get('item_id'),
                'tags': tag_name
            })

        if len(actions) > 0:
            tag_request = requests.post('https://getpocket.com/v3/send', json={
                'consumer_key': consumer_key,
                'access_token': account.access_token,
                'actions': actions
            })

            if tag_request.get_header('x-limit-key-remaining') == 0:
                taskqueue.add(
                    queue_name='process',
                    params={
                        'key': session.get('key'),
                        'offset': offset,
                        'updated': updated
                    },
                    countdown=tag_request.get_header('x-limit-key-reset')
                )

                return 'paused ...'

            tag_request.raise_for_status()

            updated = updated + len(actions)

        if found_tags == limit:
            break

        offset = offset + limit

    # Send an email
    email = Mailgun("We've updated {0} items from your list!".format(updated), 'updated')
    email.send_to(account.username, account.email, {'username': account.username, 'updated': updated})
    return 'ok'


if __name__ == '__main__':
    app.run(debug=True)
