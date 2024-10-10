/*
 * Copyright (c) 2024 nggit
 */
#include <string.h>

#define PY_SSIZE_T_CLEAN
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
        PyErr_SetString(PyExc_TypeError,
                        "modules.c: first argument must be a dictionary");
        return NULL;
    }

    if (excludes != Py_None && !PySequence_Check(excludes)) {
        PyErr_SetString(PyExc_TypeError,
                        "modules.c: second argument must be an iterable or None");
        return NULL;
    }

    PyObject *module_name, *module;
    Py_ssize_t pos = 0;

    while (PyDict_Next(modules, &pos, &module_name, &module)) {
        PyObject *module_dict = PyObject_GetAttrString(module, "__dict__");

        if (module_dict == NULL) {
            PyErr_Clear();
        } else if (PyDict_Check(module_dict)) {
            PyObject *name, *value;
            Py_ssize_t dict_pos = 0;

            while (PyDict_Next(module_dict, &dict_pos, &name, &value)) {
                if (excludes != Py_None && PySequence_Contains(excludes, value)) {
                    continue;
                }

                /* skip if the name starts with "__" */
                const char *name_str;
                Py_ssize_t name_size;
                name_str = PyUnicode_AsUTF8AndSize(name, &name_size);

                if (name_str == NULL ||
                    (name_size >= 2 && strncmp(name_str, "__", 2) == 0)) {
                    continue;
                }

                if (value != module) {
                    /*
                     * attempt to get the __dict__ attribute of the value
                     * if the value has a __dict__ but is not a type or module, recurse
                     */
                    PyObject *value_dict = PyObject_GetAttrString(value, "__dict__");

                    if (value_dict == NULL) {
                        PyErr_Clear();
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
        const char *module_name_str;
        Py_ssize_t module_name_size;
        module_name_str = PyUnicode_AsUTF8AndSize(module_name, &module_name_size);

        if (module_name_str != NULL && module_name_size >= 2 &&
            strncmp(module_name_str, "__", 2) != 0) {
            PyDict_SetItem(modules, module_name, Py_None);
        }
    }

    if (PyErr_Occurred()) {
        return NULL;
    }

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
