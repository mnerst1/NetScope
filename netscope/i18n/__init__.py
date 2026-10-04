import json
from pathlib import Path
from PySide6.QtCore import QObject, Signal

LOCALES = {
 'en':'English','ru':'Русский','kk':'Қазақша','es':'Español','fr':'Français','de':'Deutsch',
 'pt_BR':'Português (Brasil)','it':'Italiano','tr':'Türkçe','uk':'Українська','pl':'Polski',
 'nl':'Nederlands','ar':'العربية','fa':'فارسی','hi':'हिन्दी','bn':'বাংলা',
 'zh_CN':'简体中文','zh_TW':'繁體中文','ja':'日本語','ko':'한국어','id':'Bahasa Indonesia','vi':'Tiếng Việt','th':'ไทย'
}


def catalogs():
    return {code:json.loads((Path(__file__).parent/'locales'/f'{code}.json').read_text(encoding='utf-8')) for code in LOCALES}


def validate():
    data = catalogs()
    keys = set(data['en'])
    for code, entries in data.items():
        if set(entries) != keys or any(not isinstance(v,str) or not v.strip() for v in entries.values()):
            raise ValueError(f'Incomplete locale: {code}')
    return data


class I18n(QObject):
    changed = Signal()
    def __init__(self, language='en'):
        super().__init__()
        self.data = validate()
        self.language = language if language in LOCALES else 'en'

    def t(self, key):
        return self.data[self.language][key]

    def set_language(self, code):
        if code not in LOCALES:
            raise ValueError('Unsupported language')
        self.language = code
        self.changed.emit()
