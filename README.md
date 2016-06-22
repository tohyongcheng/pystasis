# pystasis

pystasis is a tool to transform static analysis of Python code using Prospector into a readable format on a web server.


## Dependencies

Python: 

- Python 2.7
- Prospector: open source code analysis tool
- GitPython: to find out which files are changed in the recent 
- WatchDog: to watch for file changes and update prospector
- Flask: for starting web server
- Flask-SocketIO: to reload browser when file changes are detected

HTML/CSS:

- Bootstrap
- jQuery

## Improvements

- To build a cache for prospector as it can take a long time to load the whole project
- More useful logging
- To have filters for the different issues
- To have explanations on how to fix the issues
- Better doumentation
