# -*- coding:utf-8 -*-

from flask import current_app, render_template_string
import mimetypes, os, logging
from frequests import requests
from models import Settings

mimetypes.init()


def guess_mimetype(name):
    type_found = mimetypes.guess_type(name)
    if type_found:
        return type_found[0]  # Best guess

    return 'text/plain'


class Mailgun(object):
    def __init__(self, subject, template=None, text=None, html=None):
        self.files = {}
        self.data = {
            'from': None,
            'to': [],
            'cc': [],
            'bcc': [],
            'subject': subject,
            'text': None,
            'html': None,
            'o:tag': None,
            'o:campaign': None,
            'o:deliverytime': None,
            'o:tracking': 'yes',
            'o:tracking-clicks': 'htmlonly',
            'o:tracking-opens': 'yes',
            'h:X-Version': 'Minute-Pocket v1'
        }

        self.set_from(Settings.get('CONTACT_NAME'), Settings.get('CONTACT_EMAIL'))

        if template:
            # set html and text
            path = os.path.join(current_app.root_path, current_app.template_folder)

            try:
                txt_file = open(os.path.join(path, '{0}.txt'.format(template)))
                self.data['text'] = txt_file.read()
                txt_file.close()
            except IOError:
                self.data['text'] = None

            try:
                html_file = open(os.path.join(path, '{0}.html'.format(template)))
                self.data['html'] = html_file.read()
                html_file.close()
            except IOError:
                self.data['html'] = None

        if text:
            self.data['text'] = text

        if html:
            self.data['html'] = html

        if not self.data['text'] and not self.data['html']:
            raise ValueError('Unable to find the specified template.')

    def _set_email(self, name, email):
        if name is None:
            return email

        name = name.replace('<', '').replace('>', '').replace('@', '').replace('"', '').replace("'", '')
        return u'{0} <{1}>'.format(name, email)

    def set_from(self, from_name, from_email):
        self.data['from'] = self._set_email(from_name, from_email)

    def set_reply_to(self, from_name, from_email):
        self.data['h:Reply-To'] = self._set_email(from_name, from_email)

    def add_attachment(self, name, content, type=None):
        """
        Add attachment with content as binary content of the opened file
        """
        if not type:
            type = guess_mimetype(name)

        #           attachment[0]
        self.files['attachment[' + str(len(self.files)) + ']'] = (name, content, type)

    def send_to(self, name, email, substitution={}, send_at=None):
        self.data['to'] = []
        self.data['cc'] = []
        self.data['bcc'] = []

        self.data['to'].append(self._set_email(name, email))

        if substitution:
            self.data['subject'] = render_template_string(self.data['subject'], **substitution)
            if self.data['text'] is not None:
                self.data['text'] = render_template_string(self.data['text'], **substitution)

            if self.data['html'] is not None:
                self.data['html'] = render_template_string(self.data['html'], **substitution)

        return self.send(send_at)

    def send(self, send_at=None):
        # We do some changes to data so we make a copy of it
        if send_at:
            # @see http://stackoverflow.com/questions/3453177/convert-python-datetime-to-rfc-2822
            # Thu, 13 Oct 2011 18:02:00 GMT
            self.data['o:deliverytime'] = send_at.strftime('%a, %d %b %Y %H:%M:%S') + ' GMT'

        r = None
        try:
            print self.data
            r = requests.post(
                u"{0}/messages".format(Settings.get('MAILGUN_API_URL')),
                auth=('api', Settings.get('MAILGUN_API_KEY')),
                data=self.data,
                files=self.files,
                verify=False,
                timeout=20
            )

            if r.status_code == 200:
                logging.info(r.content)
                return r.json()
            else:
                logging.error(r.content)
        except requests.exceptions.RequestException:
            logging.exception("[MailGun]")

        return None
