from flask import Flask, request, session, render_template
from prospector.run import Prospector, ProspectorConfig
from collections import defaultdict
import argparse
import os
import re
import inspect
import sys
import json

VERSION = '1.0.0'

app = Flask(__name__)
propector_messages = None
paths = []

__doc__ = """
View your static code analysis in realtime.
"""


def prospect_this_directory():
    config = ProspectorConfig()
    prospector = Prospector(config)
    prospector.execute()
    all_messages = [m.as_dict() for m in prospector.messages]

    global prospector_messages
    prospector_messages = all_messages

    return all_messages


def organize_messages(messages, page_no=0, per_page=10):
    def _organize_message(_messages):
        formatted = defaultdict(lambda: list())
        for msg in _messages:
            location = msg['location']
            line = location['line']
            location['starting_line_no'] = max(0, line - 3)
            location['ending_line_no'] = line + 3
            location['html'] = internal_open_file(location['path'], location['starting_line_no'],
                                                  location['ending_line_no'])
            location['id'] = hash(msg['message'] + location['path'] + str(location['line']))
            formatted[msg['message']].append(location)
        return dict(formatted)
    formatted_messages = _organize_message(messages)
    issue_count = len(formatted_messages.keys())
    first_entry = page_no * per_page
    last_entry = min((page_no + 1) * per_page, issue_count)
    page_keys = formatted_messages.keys()[first_entry:last_entry]
    page_messages = dict([(key, formatted_messages[key]) for key in page_keys])
    page_count = issue_count / per_page + 1
    return page_messages, page_count, issue_count


def internal_open_file(filepath, starting_line_no, ending_line_no):
    _starting_line_no = starting_line_no - 1
    _ending_line_no = ending_line_no - 1
    text = ""
    fp = open(filepath, 'rb')
    for i, line in enumerate(fp):
        if _starting_line_no <= i <= _ending_line_no:
            text += line
        if i > ending_line_no:
            break
    fp.close()
    return text


@app.route("/")
def view_messages():
    page_no = int(request.args.get('page', 1)) - 1
    messages, page_count, issues_count = organize_messages(prospector_messages, page_no)
    stats = {'page_count': page_count, 'page_no': page_no, 'issue_count': issues_count}
    return render_template('messages.html', messages=messages, stats=stats)


@app.route("/open_file")
def open_file():
    file_path = request.args.get('file_path')
    line = int(request.args.get('line')) - 1
    starting_line_no = line - 7
    ending_line_no = line + 7
    res = {'snippet': "", 'start': starting_line_no, 'end': ending_line_no}
    fp = open(file_path, 'rb')
    for i, line in enumerate(fp):
        if starting_line_no <= i <= ending_line_no:
            res['snippet'] += line
        if i > ending_line_no:
            break
    fp.close()

    return json.dumps(res)


def get_changed_file_paths():
    pass


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    prospect_this_directory()
    app.run(debug=True)


if __name__ == '__main__':
    main()
