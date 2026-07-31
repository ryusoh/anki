# -*- coding: utf-8 -*-

# AwesomeTTS text-to-speech add-on for Anki
# Copyright (C) 2010-Present  Anki AwesomeTTS Development Team
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Service classes for AwesomeTTS
"""

from .amazon import Amazon
from .azure import Azure
from .baidu import Baidu
from .cambridge import Cambridge
from .cereproc import CereProc
from .collins import Collins
from .common import Trait
from .duden import Duden
from .edgetts import EdgeTTS
from .ekho import Ekho
from .elevenlabs import ElevenLabs
from .espeak import ESpeak
from .festival import Festival
from .forvo import Forvo
from .fptai import FptAi
from .freedictionary import FreeDictionary
from .google import Google
from .googletts import GoogleTTS
from .ispeech import ISpeech
from .kokoro import Kokoro
from .naver import Naver
from .naverclova import NaverClova
from .naverclovapremium import NaverClovaPremium
from .oddcast import Oddcast
from .oxford import Oxford
from .pico2wave import Pico2Wave
from .rhvoice import RHVoice
from .sapi5com import SAPI5COM
from .sapi5js import SAPI5JS
from .say import Say
from .spanishdict import SpanishDict
from .vocalware import VocalWare
from .voicevox import Voicevox
from .watson import Watson
from .yandex import Yandex
from .youdao import Youdao

__all__ = [
    # common
    'Trait',
    # services
    'Amazon',
    'Azure',
    'Baidu',
    'CereProc',
    'Collins',
    'Duden',
    'EdgeTTS',
    'Ekho',
    'ElevenLabs',
    'ESpeak',
    'Festival',
    'FPT.AI',
    'FreeDictionary',
    'Google',
    'GoogleTTS',
    'ISpeech',
    'Kokoro',
    'Naver',
    'NaverClova',
    'Oddcast',
    'Oxford',
    'Pico2Wave',
    'RHVoice',
    'SAPI5COM',
    'SAPI5JS',
    'Say',
    'SpanishDict',
    'Yandex',
    'Youdao',
    'Forvo',
    'VocalWare',
    'Voicevox',
    'Watson',
]
