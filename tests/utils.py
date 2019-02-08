import os


def get_files_tests(name):
    return os.path.join(os.path.dirname(__file__), 'files', name)
