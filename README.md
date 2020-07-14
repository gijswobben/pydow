# PyDow
Python shadow DOM, based on Pyodide. This is a sample project that explores the possibilities of Pyodide. It is not intended for production purposes and performance is poor. However, it demonstrates the power of Python as a front end language.

PyDow works by keeping a shadow representation of the DOM in memory. Interactions are calculated in this shadow first, and then the differences between the old and the new state are rendered to the browser. This principle is similar to what front-end frameworks like React, Angular, or Vue use. The difference is that this implementation is written in pure Python using the Pyodide project.

## Getting started
Run the following command to get this example app started:

```console
$ python -m http.server
```

This will start a server on port 8000, so navigate to http://localhost:8000/index.html to see the app.

The `index.html` page will load Pyodide from the CDN, then load the `pydow.py` file to load the PyDow framework, and finally the `test_app.py` file that contains the definition of the test app.
