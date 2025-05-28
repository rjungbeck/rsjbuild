import sys
import importlib.machinery
import logging

package = "{{package}}"
packages = {{packages}}
logger = logging.getLogger(f"bootstrap {package}")

cdef extern from "Python.h":
    ctypedef struct PyModuleDef:
        const char* m_name;

    void Py_INCREF(object)
    object PyModule_FromDefAndSpec(PyModuleDef *definition, object spec)
    int PyModule_ExecDef(object module, PyModuleDef* definition)

cdef extern from "{{package}}.h":
{% for module in modules %}
    object PyInit_{{module}}()
{% endfor %}

definitions = {
{% for module in modules %}
    "{{module}}": PyInit_{{module}},
{% endfor %}
    }

def debugMsg(*args):
    {% if debug %}
    print(*args)
    {% else %}
    pass
    {%  endif %}

cdef class CythonPackageLoader:
    cdef PyModuleDef* definition
    cdef object def_o
    cdef str name

    def __init__(self, name):
        debugMsg("Create CythonPackageLoader", name)
        self.def_o = definitions[name] ()
        self.definition = <PyModuleDef*>self.def_o
        self.name = name
        Py_INCREF(self.def_o)

    def load_module(self, fullname):
        debugMsg(package, "load_module", fullname)
        raise ImportError

    def create_module(self, spec):
        debugMsg(package, self.name, "create_module", spec)
        if package != "__main__":
            if spec.name.split(".")[-1] != self.name:
                raise ImportError()
        module = PyModule_FromDefAndSpec(self.definition, spec)

        return module

    def exec_module(self, module):
        try:
            PyModule_ExecDef(module, self.definition)
            module.__file__ = f"{sys.executable}/{self.name}"
        except Exception:
            logger.exception("Exception")

class CythonPackageMetaPathFinder:
    def __init__(self, modules_set):
        self.modules_set = modules_set

    def find_spec(self, fullname, path, target=None):
        debugMsg(package, "find_spec", fullname, path)
        nameParts = fullname.split(".")

        if package == "__main__":
            if len(nameParts) > 1:
                return None
        else:
            if len(nameParts) > 1:

                if nameParts[-2] != package:
                    return None

        namePart = nameParts[-1]

        if namePart not in self.modules_set:
            return None
        return importlib.machinery.ModuleSpec(fullname, CythonPackageLoader(namePart))

    def invalidate_caches(self):
        pass

def bootstrap_cython_submodules():
    debugMsg(package, "bootstrap_cython_submodules")
    modules_set = {{modules}}
    sys.meta_path.insert(0, CythonPackageMetaPathFinder(modules_set))
    #sys.meta_path.append(CythonPackageMetaPathFinder(modules_set))

bootstrap_cython_submodules()

{% if mainModule %}
sys.frozen = True
import {{mainModule}}
{{mainModule}}.main()
{%else %}
__path__ = f"{sys.executable}/{{package}}"
{% endif %}

