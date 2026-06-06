import re

with open("awesome_tts/awesometts/router.py", "r") as f:
    content = f.read()

new_funcs = r"""
    def _create_human_readable_path(self, path, svc_id, text, options, want_human, note):
        import os
        from shutil import copyfile

        if not want_human:
            return path

        if not os.path.isdir(self._temp_dir):
            os.mkdir(self._temp_dir)

        def substitute(match):
            from awesometts import logger
            key = match.group(1).strip()
            if key:
                lower = key.lower()
                if lower == 'service': return svc_id
                if lower == 'text': return text
                if lower == 'voice': return options['voice'].lower()

                try:
                    return note[key]  # exact field match
                except Exception as e:
                    logger.debug("Silently ignoring error on exact field match: %s", e)

                try:
                    for other_key in note.keys():
                        if other_key.strip().lower() == lower:
                            return note[other_key]  # fuzzy field match
                except Exception as e:
                    logger.debug("Silently ignoring error on fuzzy field match: %s", e)
            return ''

        filename = RE_MUSTACHE.sub(substitute, want_human)
        filename = RE_UNSAFE.sub('', filename)
        filename = RE_WHITESPACE.sub(' ', filename).strip()
        if not filename or filename.lower() in WINDOWS_RESERVED:
            filename = 'AwesomeTTS Audio'
        else:
            filename = filename[0:90]
        filename = 'ATTS ' + filename + '.mp3'

        new_path = os.path.join(self._temp_dir, filename)
        copyfile(path, new_path)

        return new_path

    def _prepare_call(self, svc_id, text, options):
        svc_id, service, options = self._validate_service(svc_id, options)
        if not text: raise ValueError("No speakable text is present")
        limit = 5000
        if len(text) > limit: raise ValueError("Text to speak is too long")
        text = service['instance'].modify(text)
        if not text: raise ValueError("Text not usable by " + service['class'].NAME)
        path = self._validate_path(svc_id, text, options)

        import os
        cache_hit = os.path.exists(path)

        if not cache_hit:
            for extra in self.get_extras(svc_id):
                key = extra['key']
                try:
                    options[key] = self._config['extras'][svc_id][key]
                    options[key] = options[key].strip()
                    if not options[key]:
                        raise KeyError
                except KeyError:
                    if extra['required']:
                        raise KeyError("%s required to access %s" % (extra['label'].rstrip(':'), svc_id))
                    else:
                        options[key] = None

        return svc_id, service, options, text, path, cache_hit

    def __call__(self, svc_id, text, options, callbacks, want_human=False, note=None, async_variable=True):
        self._call_assert_callbacks(callbacks)

        try:
            self._logger.debug("Call for '%s' w/ %s", svc_id, options)
            svc_id, service, options, text, path, cache_hit = self._prepare_call(svc_id, text, options)
            self._logger.debug(
                "Parsed call to '%s' w/ %s and \"%s\" at %s (cache %s)",
                svc_id, options, text, path, "hit" if cache_hit else "miss",
            )
        except Exception as exception:
            if 'done' in callbacks: callbacks['done']()
            callbacks['fail'](exception, text)
            if 'then' in callbacks: callbacks['then']()
            return

        if cache_hit:
            if 'done' in callbacks: callbacks['done']()
            callbacks['okay'](self._create_human_readable_path(path, svc_id, text, options, want_human, note))
            if 'then' in callbacks: callbacks['then']()

        elif path in self._failures and time() - self._failures[path][0] < FAILURE_CACHE_SECS:
            if 'done' in callbacks: callbacks['done']()
            callbacks['fail'](self._failures[path][1], text)
            if 'then' in callbacks: callbacks['then']()

        else:
            def on_error(exception):
                if BaseTrait.INTERNET in service['class'].TRAITS and \
                   not isinstance(exception, IncompleteRead) and \
                   not isinstance(exception, SocketError) and \
                   not isinstance(exception, URLError):
                    self._failures[path] = time(), exception
                callbacks['fail'](exception, text)

            service['instance'].net_reset()
            self._busy.append(path)

            def completion_callback(exception, text="Not available by Router.__call__.completion_callback"):
                self._busy.remove(path)
                import os
                if 'done' in callbacks: callbacks['done']()
                if 'miss' in callbacks: callbacks['miss'](svc_id, service['instance'].net_count())
                if exception:
                    on_error(exception)
                elif os.path.exists(path):
                    callbacks['okay'](self._create_human_readable_path(path, svc_id, text, options, want_human, note))
                else:
                    on_error(EnvironmentError("Expected %s to be created" % path))
                if 'then' in callbacks: callbacks['then']()

            def prerun():
                try:
                    if hasattr(service['instance'], 'prerun'):
                        service['instance'].prerun()
                    return True
                except Exception as e:
                    completion_callback(e)
                    return False

            def execution_task():
                if prerun():
                    service['instance'].run(text, options, path)

            if async_variable:
                self._pool.spawn(execution_task, completion_callback, callbacks['fail'])
            else:
                try:
                    execution_task()
                    completion_callback(None)
                except Exception as e:
                    completion_callback(e)

"""

start = content.find("    def _create_human_readable_path(self, path, svc_id, text, options, want_human, note):")
end = content.find("    def _call_assert_callbacks(self, callbacks):")

if start != -1 and end != -1:
    content = content[:start] + new_funcs + "\n" + content[end:]

with open("awesome_tts/awesometts/router.py", "w") as f:
    f.write(content)
