from pathlib import Path, PurePath


def get_files_tests(name):
    return PurePath(Path(__file__).parent, 'files', name)
