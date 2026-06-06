import re

with open("awesome_tts/awesometts/router.py", "r") as f:
    content = f.read()

new_funcs = r"""
    def _validate_option(self, option, svc_id):
        assert 'key' in option, "missing option key for %s" % svc_id
        assert self._services.normalize(option['key']) == option['key'], "bad %s key %s" % (svc_id, option['key'])
        assert option['key'] not in ['group', 'preset', 'service', 'style'], option['key'] + " is reserved for use in TTS tags"
        assert 'label' in option, "missing %s label for %s" % (option['key'], svc_id)
        assert 'values' in option, "missing %s values for %s" % (option['key'], svc_id)
        assert isinstance(option['values'], list) or isinstance(option['values'], tuple) and len(option['values']) in range(2, 4), "%s values for %s should be list or 2-3-tuple" % (option['key'], svc_id)
        assert 'transform' in option, "missing %s transform for %s" % (option['key'], svc_id)
        if not option['label'].endswith(":"):
            option['label'] += ":"
        if 'default' in option and isinstance(option['values'], list) and len(option['values']) > 1:
            option['values'] = [
                item if item[0] != option['default'] or item[1] == 'Default' else (item[0], item[1] + " [default]")
                for item in option['values']
            ]
        return option

    def _validate_extra(self, extra, svc_id):
        assert 'key' in extra, "missing extra key for %s" % svc_id
        assert self._services.normalize(extra['key']) == extra['key'], "bad %s key %s" % (svc_id, extra['key'])
        assert 'label' in extra, "missing %s label for %s" % (extra['key'], svc_id)
        if 'required' not in extra:
            extra['required'] = False
        if not extra['label'].endswith(":"):
            extra['label'] += ":"
        return extra

    def _fetch_options_and_extras(self, svc_id, force_options_reload=False):
        svc_id, service = self._fetch_service(svc_id)

        if 'options' not in service or force_options_reload == True:
            self._logger.debug("Building the options list for %s", service['name'])
            service['options'] = [
                self._validate_option(option, svc_id)
                for option in service['instance'].options()
            ]

        if 'extras' not in service or force_options_reload == True:
            service['extras'] = []
            if hasattr(service['instance'], 'extras'):
                self._logger.debug("Building the extras list for %s", service['name'])
                service['extras'] = [
                    self._validate_extra(extra, svc_id)
                    for extra in service['instance'].extras()
                ]

        return svc_id, service
"""

start = content.find("    def _fetch_options_and_extras(self, svc_id, force_options_reload=False):")
end = content.find("    def _fetch_service(self, svc_id):")

if start != -1 and end != -1:
    content = content[:start] + new_funcs + "\n" + content[end:]

with open("awesome_tts/awesometts/router.py", "w") as f:
    f.write(content)
