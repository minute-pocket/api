# Minute-Pocket - API backend

This is the api part of Minute-Pocket. It was previously running on Google Appengine.

All the settings were set on the Google Datastore.

Here are the keys that must be set:

 * POCKET_API_KEY : The KEY from [Pocket](https://getpocket.com)
 * CONTACT_NAME : The name displayed when sending an email ("Minute-Pocket")
 * CONTACT_EMAIL : The email used (like contact@minute-pocket.com)
 * MAILGUN_API_URL : The URL for Mailgun to send emails (generally contains the domain)
 * MAILGUN_API_KEY : The API Key for Mailgun.


## Installation

You'll need to install the packages to the lib folder, by doing the following:

    pip install -r requirements.txt -t lib


## Run locally

You can run this project locally by doing the following:

```
virtualenv env
./env/bin/pip install -r requirements.txt
./env/bin/python application.py
```

## Missing something?

Don't hesitate to open a ticket if some explanation are missing.

And feel free to open any Pull Requests if you want to improve the service.