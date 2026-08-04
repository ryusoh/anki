import sys

def fix_file(filepath):
    with open(filepath, "r") as f:
        lines = f.readlines()

    new_lines = []
    for i, line in enumerate(lines):
        if line.lstrip().startswith("except:") and not line.lstrip().startswith("except: #"):
            indent = line[:len(line) - len(line.lstrip())]
            new_lines.append(indent + "except Exception as e:\n")
            if "raise" not in lines[i+1]:
                 new_lines.append(indent + "    import logging; logging.getLogger('anki_connect').warning('swallowed exception: %s', e)\n")
        else:
            new_lines.append(line)

    with open(filepath, "w") as f:
        f.writelines(new_lines)

fix_file("anki_connect/__init__.py")
fix_file("anki_connect/util.py")
fix_file("anki_connect/web.py")
