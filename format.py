# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

import argparse
import subprocess
import os
from datetime import datetime
from PIL import Image, UnidentifiedImageError
from natsort import natsorted

CWD = os.getcwd()
IS_DRY_RUN = False
IS_TO_LOWER = False
IS_TO_CAPITALIZE = False
IS_RECURSIVE = False
IS_FILE_ONLY = False
EXCLUDE_DIRS = []
SUBSTITUTE = None
NAME = ''
IMAGE_EXTENSIONS = ['jpg']


def get_date_taken(path):
    try:
        return datetime.strptime(str(Image.open(path)._getexif()[36867]),
                                 '%Y:%m:%d %H:%M:%S')
    except (UnidentifiedImageError, TypeError, KeyError):
        stat = os.stat(path)
        try:
            return datetime.fromtimestamp(stat.st_birthtime)
        except AttributeError:
            return datetime.fromtimestamp(stat.st_mtime)


def is_file(path):
    return os.path.isfile(path)


def is_dir(path):
    return os.path.isdir(path)


def exists(path):
    return os.path.exists(path)


def dirname(path):
    return os.path.dirname(path)


def basename(path):
    return os.path.basename(path)


def join(root, relative_path):
    return os.path.join(root, relative_path)


class Rename:

    def __init__(self):
        self._counter = 1
        self._last_dir = ''

    def run(self, path, is_file_, is_dry_run=False):
        full_path = join(CWD, path[:-4]) if is_file_ else join(CWD, path)
        dir_name = dirname(full_path)
        name = basename(full_path)
        is_file_ = is_file(f'{full_path}.tmp') if not is_dry_run else True

        if NAME and IS_RECURSIVE:
            raise RuntimeError(
                'Do not use the recursive option when renaming  batch files')

        if NAME and is_file_:
            if self._last_dir != dirname(full_path):
                self._counter = 1
            if '.' in name:
                extension = get_extension(name)
                tmp = f'{NAME}_{self._counter}.{extension}'
            else:
                tmp = f'{NAME}_{self._counter}'
            self._counter += 1
            self._last_dir = dirname(full_path)
            return join(dir_name, tmp)

        tmp = name
        if IS_TO_LOWER:
            tmp = name.lower()
        elif IS_TO_CAPITALIZE:
            tmp = tmp.replace('_', ' ')
            for word in tmp.split():
                tmp = tmp.replace(word, word.capitalize())

        tmp2 = tmp.replace(' ', '_')
        tmp2 = tmp2.replace('Of', 'of')

        if SUBSTITUTE:
            old, new = SUBSTITUTE[0].split('/', maxsplit=1)
            return join(dir_name, tmp2.replace(old, new))
        return join(dir_name, tmp2)

    def reset(self):
        self._counter = 1


def main():
    global IS_DRY_RUN
    global IS_TO_LOWER
    global IS_TO_CAPITALIZE
    global IS_RECURSIVE
    global IS_FILE_ONLY
    global EXCLUDE_DIRS
    global SUBSTITUTE
    global NAME

    parser = argparse.ArgumentParser(description='Reformat file names')
    parser.add_argument('targets', nargs='+', help='Targets to rename')
    parser.add_argument('-d', '--dry-run', action='store_true',
                        help='Only show what it would do.')
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='Apply reformatting recursively')
    parser.add_argument('-l', '--lower', action='store_true',
                        help='Change to all lower case')
    parser.add_argument('-c', '--capitalize', action='store_true',
                        help='Capitalize first letter of each word')
    parser.add_argument('-f', '--files', action='store_true',
                        help='Change files only, ignore dirs')
    parser.add_argument('-e', '--exclude_dirs', nargs=1, default=[],
                        help='Exclude the directories that match')
    parser.add_argument('-s', '--substitute', nargs=1,
                        help='Substitute with matching sequence')
    parser.add_argument('-n', '--name', nargs=1,
                        help='Rename appending a numeric sequence')

    args = parser.parse_args()

    IS_DRY_RUN = args.dry_run
    IS_TO_LOWER = args.lower
    IS_TO_CAPITALIZE = args.capitalize
    IS_RECURSIVE = args.recursive
    IS_FILE_ONLY = args.files
    EXCLUDE_DIRS = args.exclude_dirs
    SUBSTITUTE = args.substitute
    NAME = args.name[0] if args.name else ''

    process(args.targets)


def rename_dirs(targets):
    rename = Rename()
    rename_cnt = 0
    renamed_targets = targets
    dirs, renamed_targets = find_dirs_to_rename(targets)
    for old_path in dirs:
        new_path = rename.run(old_path, is_file_=False)
        rename_cnt += move_file(old_path, new_path, is_file_=False)
        if old_path in renamed_targets:
            renamed_targets.remove(old_path)
            renamed_targets.append(new_path)
    return renamed_targets, rename_cnt


def sort_files(files):
    if NAME:
        files.sort(key=lambda x: get_date_taken(x))
    else:
        natsorted(files)


def is_image(path):
    extension = get_extension(path)
    if extension is not None and extension in IMAGE_EXTENSIONS:
        return True
    return False


def move_pp3_file(path):
    pp3_file_path = f'{path}.pp3'
    if exists(pp3_file_path):
        tmp_path = f'{pp3_file_path}.tmp'
        move_file(pp3_file_path, tmp_path, print_msg=False, is_file_=True)
        return tmp_path
    return None


def add_tmp_extension_to_files(files):
    tmp_files = []
    for path in files:
        if is_image(path):
            path_added = move_pp3_file(path)
            if path_added is not None:
                tmp_files.append(path_added)
        tmp_path = f'{path}.tmp'
        move_file(path, tmp_path, print_msg=False, is_file_=True)
        tmp_files.append(tmp_path)
    return tmp_files


def filter_pp3_files(files):
    non_pp3_files = []
    pp3_files = []
    for file in files:
        if get_extension(file[:-4]) == 'pp3':
            pp3_files.append(file)
        else:
            non_pp3_files.append(file)
    return non_pp3_files, pp3_files


def rename_files(files):
    rename = Rename()
    rename_cnt = 0

    non_pp3_files, pp3_files = filter_pp3_files(files)

    for relative_path in non_pp3_files:
        new_relative_path = rename.run(relative_path,
                                       is_file_=True,
                                       is_dry_run=IS_DRY_RUN)
        rename_cnt += move_file(relative_path,
                                new_relative_path, is_file_=True)

        corresponding_pp3_file = f'{relative_path[:-4]}.pp3.tmp'
        if corresponding_pp3_file in pp3_files:
            new_pp3_path = f'{new_relative_path}.pp3'
            rename_cnt += move_file(corresponding_pp3_file,
                                    new_pp3_path, is_file_=True)

    return rename_cnt


def process(targets):

    if IS_DRY_RUN:
        print('DRY-RUN', end='\n\n')

    rename_cnt = 0
    if not IS_FILE_ONLY:
        renamed_targets, rename_cnt = rename_dirs(targets)
    else:
        renamed_targets = targets

    files = find_files_to_rename(renamed_targets)
    sort_files(files)
    tmp_files = add_tmp_extension_to_files(files)

    rename_cnt += rename_files(tmp_files)

    if rename_cnt == 0:
        print('Not items found that need formatting.')


def get_extension(path):
    if '.' in path:
        return path.rsplit('.', 1)[-1].lower()
    return None


def is_under_excluded_dirs(path):
    for directory in EXCLUDE_DIRS:
        if directory in path.split('/'):
            return True
    return False


def find_dirs_to_rename(targets):
    dirs_ = []
    targets_ = []

    for target in targets:
        if is_under_excluded_dirs(target):
            continue
        if IS_RECURSIVE:
            start_path = join(CWD, target)
            for root, dirs, _ in os.walk(start_path, topdown=False):
                dirs[:] = [dir for dir in dirs
                           if not is_under_excluded_dirs(join(root, dir))]
                for directory in dirs:
                    full_path = join(root, directory)
                    dirs_.append(full_path)
        target_path = join(CWD, target)
        if is_dir(target_path) and not is_under_excluded_dirs(target_path):
            dirs_.append(target_path)
        targets_.append(target_path)

    return dirs_, targets_


def find_files_to_rename(targets):
    files_ = []

    for target in targets:
        if is_under_excluded_dirs(target):
            continue
        if IS_RECURSIVE:
            if is_file(target):
                files_.append(target)
            for root, dirs, files in os.walk(join(CWD, target)):
                dirs[:] = [dir for dir in dirs
                           if not is_under_excluded_dirs(join(root, dir))]
                for file in files:
                    full_path = join(root, file)
                    files_.append(full_path)
        elif is_file(target):
            files_.append(target)

    return files_


def move_file(src, dest, is_file_, print_msg=True):
    escaped_chars = str.maketrans(
        {"(": r"\(", ")": r"\)", " ": r"\ ", "'": r"\'", "&": r"\&"})
    escaped_src = src.translate(escaped_chars)
    escaped_dest = dest.translate(escaped_chars)
    if src == dest:
        return 0
    if not IS_DRY_RUN:
        move(escaped_src, escaped_dest)
    if print_msg:
        src_name = basename(
            src)[:-4] if is_file_ else basename(src)
        print_message(src_name, basename(dest))
    return 1


def move(src, dest):
    cmd = f'mv {src} {dest}'
    subprocess.call(cmd, shell=True)


def print_message(old_path, new_path):
    word = '-->'
    if IS_DRY_RUN:
        word = '~~>'
    old_name = basename(old_path)
    new_name = basename(new_path)
    print(f'{old_name:<50} {word:} {new_name}')


if __name__ == '__main__':
    main()
