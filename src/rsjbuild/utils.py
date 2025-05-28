import stat
import os
import os.path
import sys
import shutil
import logging

logger = logging.getLogger(__file__)

def chmodRW(path):
    path.chmod(path.stat().st_mode | stat.S_IWRITE | stat.S_IREAD | stat.S_IWUSR | stat.S_IRUSR | stat.S_IWGRP | stat.S_IRGRP)

def system(cmd):
    print(cmd)
    ret = os.system(cmd)
    if ret:
        raise ValueError

def pythonCall(cmd):
    system(f"{sys.executable} {cmd}")

def copytree(src, dst, symlinks=False, ignore=None):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            if not os.path.isdir(d):
                shutil.copytree(s, d, symlinks, ignore)
            else:
                copytree(s, d, symlinks, ignore)
        else:

            shutil.copy2(s, d)

def template(templatePath, targetPath, **kwargs):
    import jinja2
    template = jinja2.Template(templatePath.read_text())

    content = template.render(**kwargs)

    targetPath.write_text(content)
