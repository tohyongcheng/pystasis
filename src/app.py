from flask import Flask, request, render_template, copy_current_request_context
from flask_socketio import SocketIO, emit
from prospector.run import Prospector, ProspectorConfig
from git import Repo
from collections import defaultdict
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import time
import os
import sys
import json
import logging
import threading
import copy

VERSION = '1.0.0'
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

app = Flask(__name__)
socketio = SocketIO(app)
prospector_messages = None

__doc__ = """View your static code analysis in realtime."""


def prospect(paths):
    config = ProspectorConfig()
    config.paths = paths
    prospector = Prospector(config)
    prospector.execute()
    all_messages = [m.as_dict() for m in prospector.messages]
    global prospector_messages
    prospector_messages = all_messages

    return prospector_messages


def refresh_prospect_with_recently_changed_files(paths):
    config = ProspectorConfig()
    config.paths = paths
    config.explicit_file_mode = all(map(os.path.isfile, config.paths))
    prospector = Prospector(config)
    prospector.execute()
    global prospector_messages
    new_messages = [m.as_dict() for m in prospector.messages]
    messages_kept = [msg for msg in prospector_messages if not any([msg['location']['path'] in path for path in paths])]
    prospector_messages = new_messages + messages_kept
    
    # TODO: Need to fix RuntimeError
    emit('refresh', {}, '/test')

    return prospector_messages
    

def organize_messages(messages, page_no=0, per_page=10):
    def _organize_message(_messages):
        formatted = defaultdict(lambda: list())
        for msg in _messages:
            location = copy.deepcopy(msg['location'])
            line = location['line']
            location['starting_line_no'] = max(0, line - 7)
            location['ending_line_no'] = line + 7
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


def internal_open_file(file_path, starting_line_no, ending_line_no):
    _starting_line_no = starting_line_no - 1
    _ending_line_no = ending_line_no - 1
    text = ""
    fp = open(file_path, 'rb')
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
    line_no = int(request.args.get('line')) - 1
    starting_line_no = line_no - 7
    ending_line_no = line_no + 7
    res = {'snippet': "", 'start': starting_line_no + 1, 'end': ending_line_no + 1}
    fp = open(file_path, 'rb')
    for i, line in enumerate(fp):
        if starting_line_no <= i <= ending_line_no:
            res['snippet'] += line
        if i > ending_line_no:
            break
    fp.close()

    return json.dumps(res)


@socketio.on('connect', namespace='/test')
def test_connect():
    print("Client connected")


def get_changed_file_paths(working_dir):
    repo = Repo(working_dir)
    if repo.bare:
        return None
    file_paths = set()
    for diff in (repo.index.diff(None) + repo.index.diff("HEAD")):
        file_paths.add(diff.a_path)
        file_paths.add(diff.b_path)
    list_of_file_paths = list(file_paths)
    print list_of_file_paths
    return list_of_file_paths


class WatchDogFileSystemsHandler(PatternMatchingEventHandler):
    def __init__(self):
        PatternMatchingEventHandler.__init__(self, patterns=["*.py"])

    def on_modified(self, event):
        print event
        if event.src_path.endswith('.py'):
            print "Refreshing %s" % event.src_path
            refresh_prospect_with_recently_changed_files([event.src_path])


def start_watchdog(path):
    event_handler = WatchDogFileSystemsHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


class WatchDogThread(threading.Thread):
    def __init__(self, path):
        threading.Thread.__init__(self)
        self.path = path

    def run(self):
        start_watchdog(self.path)


class FlaskThread(threading.Thread):
    def __init__(self, paths):
        threading.Thread.__init__(self)
        self.paths = paths

    def run(self):
        run_flask(self.paths)

def run_flask(paths):
    prospect(paths)
    socketio.run(app)


def main():
    paths = sys.argv[1] if len(sys.argv) > 1 else '.'
    
    # flask_thread = FlaskThread(paths)
    # flask_thread.daemon = True
    # flask_thread.start()

    print "Starting WatchDogThread"
    watchdog_thread = WatchDogThread(paths)
    watchdog_thread.daemon = True
    watchdog_thread.start()

    run_flask(paths)


if __name__ == '__main__':
    main()
