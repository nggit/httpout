/*
 * Copyright (c) 2024 nggit
 */
#define PY_SSIZE_T_CLEAN
#define Py_LIMITED_API
#include <Python.h>

/* function declarations */
static PyObject* cleanup_modules(PyObject *self, PyObject *args);

/* function implementations */
static PyObject*
cleanup_modules(PyObject *self, PyObject *args)
{
    PyObject *modules;
    PyObject *excludes = Py_None;

    if (!PyArg_ParseTuple(args, "O|O", &modules, &excludes)) {
        return NULL;
    }

    if (!PyDict_Check(modules)) {
        PyErr_SetString(PyExc_TypeError, "modules.c: first argument must be a dictionary");
        return NULL;
    }

    if (excludes != Py_None && !PySequence_Check(excludes)) {
        PyErr_SetString(PyExc_TypeError, "modules.c: second argument must be an iterable or None");
        return NULL;
    }

    PyObject *double_underscore = PyUnicode_FromString("__");
    PyObject *module_name, *module;
    Py_ssize_t pos = 0;

    while (PyDict_Next(modules, &pos, &module_name, &module)) {
        PyObject *module_dict = PyObject_GetAttrString(module, "__dict__");

        if (module_dict == NULL) {
            if (PyErr_Occurred()) {
                PyErr_Clear();
            }
        } else if (PyDict_Check(module_dict)) {
            PyObject *name, *value;
            Py_ssize_t dict_pos = 0;

            while (PyDict_Next(module_dict, &dict_pos, &name, &value)) {
                if ((excludes != Py_None && PySequence_Contains(excludes, value)) ||
                    (PyUnicode_Check(name) && PyUnicode_Find(name, double_underscore, 0, 2, 1) == 0)) {
                    continue;
                }

                if (value != module) {
                    /*
                     * attempt to get the __dict__ attribute of the value
                     * if the value has a __dict__ but is not a type or module, recurse
                     */
                    PyObject *value_dict = PyObject_GetAttrString(value, "__dict__");

                    if (value_dict == NULL) {
                        if (PyErr_Occurred()) {
                            PyErr_Clear();
                        }
                    } else if (PyDict_Check(value_dict) &&
                               !PyType_Check(value) &&
                               !PyModule_Check(value)) {
                        /* recursively call cleanup_modules for the value's __dict__ */
                        PyObject *args = Py_BuildValue("(OO)", value_dict, excludes);
                        PyObject *result = cleanup_modules(self, args);
                        Py_XDECREF(args);

                        if (result == NULL) {
                            Py_XDECREF(value_dict);
                            Py_XDECREF(module_dict);
                            Py_DECREF(double_underscore);
                            return NULL;
                        }

                        Py_XDECREF(result);
                    }

                    Py_XDECREF(value_dict);
                }

                /* set the module.__dict__[name] to None */
                PyDict_SetItem(module_dict, name, Py_None);
            }
        }

        Py_XDECREF(module_dict);

        /* set the module itself to None if it doesn't start with "__" */
        if (PyUnicode_Check(module_name) &&
            PyUnicode_Find(module_name, double_underscore, 0, 2, 1) == -1) {
            PyDict_SetItem(modules, module_name, Py_None);
        }
    }

    Py_DECREF(double_underscore);
    Py_RETURN_NONE;
}

static PyMethodDef modules_methods[] = {
    {"cleanup_modules", cleanup_modules, METH_VARARGS, ""},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef modules_module = {
    PyModuleDef_HEAD_INIT,
    "modules", /* __name__ */
    NULL,      /* __doc__ */
    -1,
    modules_methods
};

PyMODINIT_FUNC PyInit_modules(void) {
    return PyModule_Create(&modules_module);
}
