import os


def get_all_files(directory="~"):
    directory = os.path.expanduser(directory)
    files = []
    for root, _, filenames in os.walk(directory):
        for f in filenames:
            path = os.path.join(root, f)
            files.append(path)
    return files
