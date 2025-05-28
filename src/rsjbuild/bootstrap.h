#include <string.h>

#include "Python.h"

{%for module in modules%}
extern PyObject* PyInit_{{module}}(void);
{%endfor%}

{%for package in packages%}
PyMODINIT_FUNC  PyInit_{{package}}(void);
{%endfor%}


