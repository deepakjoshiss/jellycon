from __future__ import (
    division, absolute_import, print_function, unicode_literals
)

import json

import requests
import xbmcaddon
from kodi_six.utils import py2_decode

from .utils import get_device_id, get_version, load_user_details
from .lazylogger import LazyLogger

log = LazyLogger(__name__)


class API:
    def __init__(self, server=None, user_id=None, token=None):
        self.server = server
        self.user_id = user_id
        self.token = token

        self.settings = xbmcaddon.Addon()

        self.headers = {}
        self.create_headers()
        self.verify_cert = settings.getSetting('verify_cert') == 'true'

    def get(self, path):
        if 'Authorization' not in self.headers or self.token not in self.headers:
            self.create_headers(True)

        # Fixes initial login where class is initialized before wizard completes
        if not self.server:
            self.settings = xbmcaddon.Addon()
            self.server = self.settings.getSetting('server_address')

        url = '{}{}'.format(self.server, path)

        try:
            r = requests.get(url, headers=self.headers, verify=self.verify_cert, timeout=(5,60))
            try:
                '''
                The requests library defaults to using simplejson to handle
                json decoding.  On low power devices and using Py3, this is
                significantly slower than the builtin json library.  Skip that
                and just parse the json ourselves.  Fall back to using
                requests/simplejson if there's a parsing error.
                '''
                r.raise_for_status()
                response_data = json.loads(r.text)
            except ValueError:
                response_data = r.json()
        except Exception:
            response_data = {}
        return response_data

    def post(self, url, payload={}):
        if 'Authorization' not in self.headers or self.token not in self.headers:
            self.create_headers(True)

        url = '{}{}'.format(self.server, url)

        try:
            r = requests.post(url, json=payload, headers=self.headers, verify=self.verify_cert, timeout=5)
            try:
                # Much faster on low power devices, see above comment
                response_data = json.loads(r.text)
            except ValueError:
                response_data = r.json()
        except Exception:
            response_data = {}
        return response_data

    def delete(self, url):
        if 'Authorization' not in self.headers or self.token not in self.headers:
            self.create_headers(True)

        url = '{}{}'.format(self.server, url)

        try:
            requests.delete(url, headers=self.headers, verify=self.verify_cert, timeout=5)
        except Exception:
            pass

    def authenticate(self, auth_data):
        # The authentication request must NOT carry a token. A stale/expired
        # token in the Authorization header is rejected by the server (401)
        # even on this anonymous endpoint, which would otherwise make it
        # impossible to log back in once a token expires. Drop any existing
        # token and build a token-free header for this request.
        self.token = None
        self.create_headers(force=True, include_token=False)

        if not self.server:
            self.settings = xbmcaddon.Addon()
            self.server = self.settings.getSetting('server_address')

        url = '{}/Users/AuthenticateByName'.format(self.server)
        try:
            r = requests.post(url, json=auth_data, headers=self.headers, verify=self.verify_cert, timeout=5)
            try:
                response = json.loads(r.text)
            except ValueError:
                response = r.json()
        except Exception:
            response = {}

        token = response.get('AccessToken')
        if token:
            self.token = token
            self.user_id = response.get('User').get('Id')
            # Append the freshly issued token to the current header so the rest
            # of this session uses it (auth.json is updated by the caller).
            self.headers['Authorization'] += ", Token={}".format(token)
            return response
        else:
            log.error('Unable to authenticate to Jellyfin server')
            return {}

    def is_authenticated(self):
        '''
        Check whether the currently held token is still valid on the server.

        Returns True only on an authenticated (200) response.  A token that
        has expired or been revoked server-side returns 401, in which case we
        report False so the caller can prompt for credentials and re-login.
        '''
        # Pick up the saved token for the current user and build fresh headers
        self.create_headers(True)

        if not self.token:
            return False

        if not self.server:
            self.settings = xbmcaddon.Addon()
            self.server = self.settings.getSetting('server_address')

        url = '{}/Users/Me'.format(self.server)
        try:
            r = requests.get(url, headers=self.headers, verify=self.verify_cert, timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def create_headers(self, force=False, include_token=True):

        # If the headers already exist with an auth token, return unless we're regenerating
        if self.headers and 'Authorization' in self.headers.get('Authorization', '') and force is False:
            return

        headers = {}
        device_name = self.settings.getSetting('deviceName')
        if len(device_name) == 0:
            device_name = "JellyCon"
        # Ensure ascii and remove invalid characters
        device_name = py2_decode(device_name).replace('"', '_').replace(',', '_')
        device_id = get_device_id()
        version = get_version()

        authorization = (
            'MediaBrowser Client="Kodi JellyCon", Device="{device}", '
            'DeviceId="{device_id}", Version="{version}"'
        ).format(
            device=device_name,
            device_id=device_id,
            version=version
        )

        headers['Authorization'] = authorization

        # Skip the token entirely when explicitly requested (e.g. the
        # authentication request, which must be sent without a token).
        if include_token:
            # If we have a valid token, ensure it's included in the headers unless we're regenerating
            if self.token and force is False:
                headers['Authorization'] += ', Token="{}"'.format(self.token)
            else:
                # Check for updated credentials since initialization
                user_details = load_user_details()
                token = user_details.get('token')
                if token:
                    self.token = token
                    headers['Authorization'] += ", Token={}".format(self.token)

        # Kodi doesn't support br or zstd compression, exclude them
        headers['Accept-Encoding'] = 'gzip, deflate'

        # Make headers available to api calls
        self.headers = headers

    def post_capabilities(self):
        url = '/Sessions/Capabilities/Full'

        data = {
            'SupportsMediaControl': True,
            'PlayableMediaTypes': ["Video", "Audio"],
            'SupportedCommands': ["MoveUp",
                                  "MoveDown",
                                  "MoveLeft",
                                  "MoveRight",
                                  "Select",
                                  "Back",
                                  "ToggleContextMenu",
                                  "ToggleFullscreen",
                                  "ToggleOsdMenu",
                                  "GoHome",
                                  "PageUp",
                                  "NextLetter",
                                  "GoToSearch",
                                  "GoToSettings",
                                  "PageDown",
                                  "PreviousLetter",
                                  "TakeScreenshot",
                                  "VolumeUp",
                                  "VolumeDown",
                                  "ToggleMute",
                                  "SendString",
                                  "DisplayMessage",
                                  "SetAudioStreamIndex",
                                  "SetSubtitleStreamIndex",
                                  "SetRepeatMode",
                                  "Mute",
                                  "Unmute",
                                  "SetVolume",
                                  "PlayNext",
                                  "Play",
                                  "Playstate",
                                  "PlayMediaSource"]
        }

        self.post(url, data)

    def speedtest(self, test_data_size):
        self.create_headers()

        url = '{}/playback/bitratetest?size={}'.format(self.server, test_data_size)
        # Because this needs the stream argument, this doesn't go through self.get()
        response = requests.get(url, stream=True, headers=self.headers, verify=self.verify_cert)

        return response


settings = xbmcaddon.Addon()
user_details = load_user_details()
api = API(
    settings.getSetting('server_address'),
    user_details.get('user_id'),
    user_details.get('token')
)
