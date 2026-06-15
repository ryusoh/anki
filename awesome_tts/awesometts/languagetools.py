import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from typing import Optional

import requests

from . import machineid


@dataclass
class TrialRequestReponse:
    success: bool
    api_key: Optional[str] = None
    error: Optional[str] = None


class LanguageTools:
    def __init__(self, api_key, logger, client_version, client_uuid):
        self.logger = logger
        self.base_url = 'https://cloudlanguagetools-api.vocab.ai'
        if 'ANKI_LANGUAGE_TOOLS_BASE_URL' in os.environ:
            self.base_url = os.environ['ANKI_LANGUAGE_TOOLS_BASE_URL']
        self.vocab_api_base_url = 'https://app.vocab.ai/languagetools-api/v3'
        if 'ANKI_LANGUAGE_TOOLS_VOCABAI_BASE_URL' in os.environ:
            self.vocab_api_base_url = os.environ['ANKI_LANGUAGE_TOOLS_VOCABAI_BASE_URL']
        self.api_key = api_key
        self.client_version = client_version
        self.client_uuid = client_uuid
        self.trial_instant_signed_up = False
        self.api_key_verified = False
        self.use_vocabai_api = False

    def get_base_url(self):
        return self.base_url

    def set_api_key(self, api_key):
        self.api_key = api_key
        self.api_key_verified = False
        self.use_vocabai_api = False

    def get_api_key(self):
        return self.api_key

    def use_plus_mode(self):
        return len(self.api_key) > 0

    def verify_api_key(self, api_key):
        # first , try to verify API key with vocab API
        try:
            response = requests.get(
                self.vocab_api_base_url + '/account',
                headers={'Authorization': f'Api-Key {api_key}'},
                timeout=10,
            )
            if response.status_code == 200:
                # API key is valid on vocab API
                self.api_key = api_key
                self.api_key_verified = True
                self.use_vocabai_api = True
                return {
                    'key_valid': True,
                }

            # now check with cloudlanguagetools API
            response = requests.get(
                self.base_url + '/account', headers={'api_key': api_key}, timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if 'error' in data:
                    return {'key_valid': False, 'msg': data['error']}
                # key valid
                self.api_key = api_key
                self.api_key_verified = True
                self.use_vocabai_api = False
                return {'key_valid': True, 'msg': f'api key: {api_key}'}
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error verifying API key: {e}")
            return {'key_valid': False, 'msg': 'api key not valid'}

        # by default, key is invalid
        return {'key_valid': False, 'msg': 'api key not valid'}

    def ensure_key_verified(self):
        if self.api_key == None:
            raise ValueError('API Key not set')
        if self.api_key_verified == False:
            self.verify_api_key(self.api_key)

    def account_info(self):
        self.ensure_key_verified()

        try:
            if self.use_vocabai_api:
                response = requests.get(
                    self.vocab_api_base_url + '/account',
                    headers={'Authorization': f'Api-Key {self.api_key}'},
                    timeout=10,
                )
            else:
                response = requests.get(
                    self.base_url + '/account', headers={'api_key': self.api_key}, timeout=10
                )
            data = json.loads(response.content)
            return data
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error in account_info: {e}")
            raise ValueError(f"Network error: {e}")

    # def request_trial_key(self, email):
    #     self.logger.info(f'requesting trial key for email {email}')
    #     response = requests.post(self.base_url + '/request_trial_key', json={'email': email})
    #     data = json.loads(response.content)
    #     self.logger.info(f'retrieved {data}')
    #     if 'api_key' in data:
    #         self.trial_instant_signed_up = True
    #     return data

    def generate_audio_v2(
        self, source_text, service, request_mode, language_code, deck_name, voice_key, options, path
    ):
        self.ensure_key_verified()

        # query cloud language tools API
        data = {
            'text': source_text,
            'service': service,
            'request_mode': request_mode,
            'language_code': language_code,
            'deck_name': deck_name,
            'voice_key': voice_key,
            'options': options,
        }

        try:
            if self.use_vocabai_api:
                headers = {
                    'Authorization': f'Api-Key {self.api_key}',
                    'User-Agent': f'anki-awesometts/{self.client_version}',
                    'X-Vocab-Addon-ID': self.client_uuid,
                }
                full_url = self.vocab_api_base_url + '/audio'
                response = requests.post(full_url, json=data, headers=headers, timeout=10)
            else:
                url_path = '/audio_v2'
                full_url = self.base_url + url_path
                self.logger.info(f'request url: {full_url}, data: {data}')
                response = requests.post(
                    full_url,
                    json=data,
                    headers={
                        'api_key': self.get_api_key(),
                        'client': 'awesometts',
                        'client_version': self.client_version,
                    },
                    timeout=10,
                )

            if response.status_code == 200:
                self.logger.info('success, receiving audio')
                with open(path, 'wb') as f:
                    f.write(response.content)
            else:
                error_message = f"Status code: {response.status_code} ({response.content})"
                self.logger.error(error_message)
                raise ValueError(error_message)
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error in generate_audio_v2: {e}")
            raise ValueError(f"Network error: {e}")

    def compute_hmac_signature(self, email, client_uuid, machine_id):
        secret_key = os.environ.get('ANKI_LANGUAGE_TOOLS_TRIAL_SECRET_KEY', 'kXpZuHms9Rv0Y4wqlcze')

        message = f"{email}:{client_uuid}:{machine_id}".encode('utf-8')
        signature = hmac.new(secret_key.encode('utf-8'), message, hashlib.sha256).hexdigest()

        return signature

    def build_trial_key_request_data(self, email, password, client_uuid):
        machine_id = machineid.id()

        hmac_signature = self.compute_hmac_signature(email, client_uuid, machine_id)

        data = {'id_1': client_uuid, 'id_2': machine_id, 'id_3': hmac_signature}
        data['email'] = email
        data['password'] = password
        return data

    def request_trial_key(self, email, password) -> TrialRequestReponse:
        self.logger.info(f'requesting trial key for email {email}')

        data = self.build_trial_key_request_data(email, password, self.client_uuid)

        # Make sure we have the method to get headers
        if not hasattr(self, 'get_trial_request_headers'):
            # Default headers if method doesn't exist
            headers = {
                'User-Agent': f'anki-awesometts/{self.client_version}',
                'Content-Type': 'application/json',
            }
        else:
            headers = self.get_trial_request_headers()

        # Make sure we have the correct URL
        if not hasattr(self, 'vocab_api_base_url'):
            base_url = self.base_url
        else:
            base_url = self.vocab_api_base_url

        try:
            response = requests.post(
                base_url + '/register_trial', json=data, headers=headers, timeout=10
            )
            data = json.loads(response.content)
            self.logger.info(f'retrieved {data}, status_code: {response.status_code}')

            if response.status_code == 201:
                # trial key was successfully created
                return TrialRequestReponse(success=True, api_key=data['api_key'])
            else:
                error_message = '<b>error:</b> ' + ', '.join(
                    [f"{key}: {value}" for key, value in data.items()]
                )
                return TrialRequestReponse(success=False, error=error_message)
        except Exception as e:
            self.logger.error(f"Error processing trial key request: {str(e)}")
            return TrialRequestReponse(success=False, error=f"Error: {str(e)}")
