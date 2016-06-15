from flask import Flask, request, session, render_template
from prospector.run import Prospector, ProspectorConfig
from collections import defaultdict
import argparse
import os
import re
import inspect


VERSION = '1.0.0'

app = Flask(__name__)

__doc__ = """
View your static code analysis in realtime.
"""

def prospect_this_directory():
    config = ProspectorConfig()
    prospector = Prospector(config)
    prospector.execute()
    all_messages = [m.as_dict() for m in prospector.messages]

    return all_messages

def organize_messages(messages):
    formatted_messages = defaultdict(lambda: list())
    for msg in messages:
        location = msg['location']
        formatted_messages[msg['message']].append(location)

    return dict(formatted_messages)

@app.route("/")
def view_messages():
    messages = organize_messages(prospect_this_directory())
    return render_template('messages.html', messages=messages)

@app.route("/open_file")
def open_file():
    filepath = request.args.get('filepath')
    starting_line_no = int(request.args.get('starting_line_no')) - 1
    ending_line_no = int(request.args.get('ending_line_no')) - 1
    text = ""
    fp = open(filepath, 'rb')
    for i, line in enumerate(fp):
        if i >= starting_line_no and i <= ending_line_no:
            text += line
        if i > ending_line_no:
            break
    fp.close()
    return text




def main():
    app.run(debug=True)

if __name__ == '__main__':
    main()
