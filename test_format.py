# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

import os
import unittest
import subprocess
import shutil
from random import randint
import hashlib
from pathlib import Path
from time import sleep
from checksumdir import dirhash


PWD = os.path.dirname(os.path.realpath(__file__))
TEST_DIR = os.path.join(PWD, 'test')


def _create_file(file_name):
    file_path = os.path.join(TEST_DIR, file_name)
    Path(file_path).touch()
    _add_random_content_to_file(file_path)
    return _hashfile(file_path)


def _add_random_content_to_file(file_path):
    with open(file_path, 'w') as file:
        file.write(str(randint(0, 10000)))


def _hashfile(file):
    buf_size = 65536
    sha256 = hashlib.sha256()
    with open(file, 'rb') as my_file:
        while True:
            data = my_file.read(buf_size)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()


def _hashdir(directory):
    return dirhash(directory, 'sha256')


def _create_dir(dir_name):
    Path(os.path.join(TEST_DIR, dir_name)).mkdir()


def _remove_file(file_path):
    Path(file_path).unlink()


def _remove_dir(dir_path):
    shutil.rmtree(dir_path, ignore_errors=True)


def _init_test_dir():
    _remove_dir(TEST_DIR)
    Path(TEST_DIR).mkdir()


def _create_test_tree(tree):
    return _create_dirs_and_files_from_tree(TEST_DIR, tree)


def _is_dir(path):
    return os.path.isdir(path)


def _create_dirs_and_files_from_tree(root_pwd, tree_dict):
    hashes_dict = {}
    for key, val in tree_dict.items():
        full_path = os.path.join(root_pwd, key)
        if isinstance(val, dict):
            Path(full_path).mkdir()
            hashes_dict.update(
                _create_dirs_and_files_from_tree(full_path, val))
            hashes_dict[key] = _hashdir(full_path)
        else:
            Path(full_path).touch()
            _add_random_content_to_file(full_path)
            hashes_dict[key] = _hashfile(full_path)
        # add a delay to show different creating time stamps for each file,
        # otherwise all files show the exact same creating time
        sleep(10/1000)
    return hashes_dict


def _assert_tree_renaming(self,
                          expected_tree,
                          hashes_dict,
                          expected_renaming,
                          root_path,
                          is_files_only=False,
                          excluded_dir=""):
    for name, children in expected_tree.items():
        path = os.path.join(root_path, name)
        if is_files_only and _is_dir(path):
            new_name = name
        else:
            # if part of excluded directory do not replace
            if excluded_dir in path.split('/'):
                new_name = name
            else:
                new_name = name.replace(' ', '_')
        new_path = os.path.join(root_path, new_name)
        if isinstance(children, dict):
            _assert_tree_renaming(self,
                                  children,
                                  hashes_dict,
                                  expected_renaming,
                                  new_path,
                                  is_files_only=is_files_only)
        else:
            assert_file_exists(self, new_path)
            assert_hash_is_same(self, expected_renaming, hashes_dict, new_path)


def assert_hash_is_same(self, renaming_dict, hashes_dict, file_path):
    file_name = os.path.basename(file_path)
    old_name = renaming_dict[file_name]
    prev_hash = hashes_dict[old_name]
    self.assertEqual(prev_hash,
                     _hashfile(file_path),
                     msg=f'{old_name} {prev_hash} != '
                     f'{file_name} {_hashfile(file_path)}')


def assert_file_exists(self, path):
    self.assertEqual(True, os.path.exists(
        path), msg=f'[{path}], doesn\'t exist')


class TestRenameFile(unittest.TestCase):

    _test_file_name = 'TEST FILE'

    def setUp(self):
        _init_test_dir()
        os.chdir(TEST_DIR)
        self._expected_hash = _create_file(self._test_file_name)

    def tearDown(self):
        _remove_dir(TEST_DIR)

    def test_rename_file_remove_spaces(self):
        expected_name = self._test_file_name.replace(' ', '_')
        expected_path = os.path.join(TEST_DIR, expected_name)
        hash_tree_before = _hashdir(TEST_DIR)
        subprocess.run(f'frmt "{self._test_file_name}"',
                       shell=True,
                       check=True,
                       stdout=subprocess.DEVNULL)
        self.assertEqual(hash_tree_before, _hashdir(TEST_DIR))
        self.assertEqual(True, os.path.exists(expected_path))
        self.assertEqual(self._expected_hash, _hashfile(expected_path))
        _remove_file(expected_path)

    def test_rename_file_convert_to_lowercase(self):
        expected_name = self._test_file_name.replace(' ', '_').lower()
        expected_path = os.path.join(TEST_DIR, expected_name)
        hash_tree_before = _hashdir(TEST_DIR)
        subprocess.run(f'frmt -l "{self._test_file_name}"',
                       shell=True,
                       check=True,
                       stdout=subprocess.DEVNULL)
        self.assertEqual(hash_tree_before, _hashdir(TEST_DIR))
        self.assertEqual(True, os.path.exists(expected_path))
        self.assertEqual(self._expected_hash, _hashfile(expected_path))
        _remove_file(expected_path)

    def test_dry_run_does_not_modify_the_file(self):
        expected_name = self._test_file_name.replace(' ', '_')
        original_path = os.path.join(TEST_DIR, self._test_file_name)
        expected_path = os.path.join(TEST_DIR, expected_name)
        hash_tree_before = _hashdir(TEST_DIR)
        subprocess.run(f'frmt -d "{self._test_file_name}"',
                       shell=True,
                       check=True,
                       stdout=subprocess.DEVNULL)
        self.assertEqual(hash_tree_before, _hashdir(TEST_DIR))
        self.assertEqual(True, os.path.exists(original_path))
        self.assertEqual(False, os.path.exists(expected_path))
        self.assertEqual(self._expected_hash, _hashfile(original_path))
        _remove_file(original_path)


class TestRenameDirectory(unittest.TestCase):

    _test_dir_name = 'TEST DIR'

    def setUp(self):
        _init_test_dir()
        os.chdir(TEST_DIR)
        _create_dir(self._test_dir_name)

    def tearDown(self):
        _remove_dir(TEST_DIR)

    def test_rename_directory_remove_spaces(self):
        expected_name = self._test_dir_name.replace(' ', '_')
        expected_path = os.path.join(TEST_DIR, expected_name)
        hash_tree_before = _hashdir(TEST_DIR)
        subprocess.run(f'frmt "{self._test_dir_name}"',
                       shell=True,
                       check=True,
                       stdout=subprocess.DEVNULL)
        self.assertEqual(hash_tree_before, _hashdir(TEST_DIR))
        self.assertEqual(True, os.path.exists(expected_path))
        _remove_dir(expected_path)

    def test_rename_directory_covert_to_lowercase(self):
        expected_name = self._test_dir_name.replace(' ', '_').lower()
        expected_path = os.path.join(TEST_DIR, expected_name)
        hash_tree_before = _hashdir(TEST_DIR)
        subprocess.run(f'frmt -l "{self._test_dir_name}"',
                       shell=True,
                       check=True,
                       stdout=subprocess.DEVNULL)
        self.assertEqual(hash_tree_before, _hashdir(TEST_DIR))
        self.assertEqual(True, os.path.exists(expected_path))
        _remove_dir(expected_path)

    def test_dry_run_does_not_modify_the_dir(self):
        expected_name = self._test_dir_name.replace(' ', '_')
        original_path = os.path.join(TEST_DIR, self._test_dir_name)
        expected_path = os.path.join(TEST_DIR, expected_name)
        hash_tree_before = _hashdir(TEST_DIR)
        subprocess.run(f'frmt -d "{self._test_dir_name}"',
                       shell=True,
                       check=True,
                       stdout=subprocess.DEVNULL)
        self.assertEqual(hash_tree_before, _hashdir(TEST_DIR))
        self.assertEqual(True, os.path.exists(original_path))
        self.assertEqual(False, os.path.exists(expected_path))
        _remove_dir(original_path)


class TestRenameRecursiveFiles(unittest.TestCase):

    _tree = {
        'TEST DIR 1': {
            'TEST FILE 1': None,
            'TEST DIR 2': {
                'TEST FILE 2': None,
                'TEST DIR 3': {
                    'TEST FILE 3': None,
                }
            }
        }
    }

    def setUp(self):
        _init_test_dir()
        os.chdir(TEST_DIR)
        self._hashes_dict = _create_test_tree(self._tree)

    def tearDown(self):
        _remove_dir(TEST_DIR)

    def test_recursive(self):
        expected_tree = {
            'TEST_DIR_1': {
                'TEST_FILE_1': None,
                'TEST_DIR_2': {
                    'TEST_FILE_2': None,
                    'TEST_DIR_3': {
                        'TEST_FILE_3': None,
                    }
                }
            }
        }
        expected_renaming = {
            'TEST_DIR_1': 'TEST DIR 1',
            'TEST_FILE_1': 'TEST FILE 1',
            'TEST_DIR_2': 'TEST DIR 2',
            'TEST_FILE_2': 'TEST FILE 2',
            'TEST_DIR_3': 'TEST DIR 3',
            'TEST_FILE_3': 'TEST FILE 3',
        }
        hash_tree_before = _hashdir(TEST_DIR)
        subprocess.run('frmt -r "TEST DIR 1"',
                       shell=True,
                       check=True,
                       stdout=subprocess.DEVNULL)
        self.assertEqual(hash_tree_before, _hashdir(TEST_DIR))
        _assert_tree_renaming(self, expected_tree,
                              self._hashes_dict, expected_renaming, TEST_DIR)

    def test_recursive_files_only(self):
        expected_tree = {
            'TEST DIR 1': {
                'TEST_FILE_1': None,
                'TEST DIR 2': {
                    'TEST_FILE_2': None,
                    'TEST DIR 3': {
                        'TEST_FILE_3': None,
                    }
                }
            }
        }
        expected_renaming = {
            'TEST DIR_1': 'TEST DIR 1',
            'TEST_FILE_1': 'TEST FILE 1',
            'TEST DIR 2': 'TEST DIR 2',
            'TEST_FILE_2': 'TEST FILE 2',
            'TEST DIR 3': 'TEST DIR 3',
            'TEST_FILE_3': 'TEST FILE 3',
        }
        hash_tree_before = _hashdir(TEST_DIR)
        subprocess.run(
            'frmt -r -f "TEST DIR 1"',
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL)
        self.assertEqual(hash_tree_before, _hashdir(TEST_DIR))
        _assert_tree_renaming(self,
                              expected_tree,
                              self._hashes_dict,
                              expected_renaming,
                              TEST_DIR,
                              is_files_only=True)


class TestRenameNumberedFiles(unittest.TestCase):

    _tree = {
        'TEST DIR 1': {
            'TEST FILE D': None,
            'TEST FILE A': None,
            'TEST FILE 3': None,
            'TEST FILE': None,
            'TEST FILE ABC': None,
        }
    }

    def setUp(self):
        _init_test_dir()
        os.chdir(TEST_DIR)

    def tearDown(self):
        _remove_dir(TEST_DIR)

    def test_rename_numbered_files(self):
        hashes_dict = _create_test_tree(self._tree)
        expected_tree = {
            'TEST DIR 1': {
                'sample_1': None,
                'sample_2': None,
                'sample_3': None,
                'sample_4': None,
                'sample_5': None,
            }
        }
        expected_renaming = {
            'TEST DIR 1': 'TEST DIR 1',
            'sample_1': 'TEST FILE D',
            'sample_2': 'TEST FILE A',
            'sample_3': 'TEST FILE 3',
            'sample_4': 'TEST FILE',
            'sample_5': 'TEST FILE ABC',
        }
        hash_tree_before = _hashdir(TEST_DIR)
        subprocess.run('frmt -f -n sample "TEST DIR 1"/*',
                       shell=True,
                       check=True,
                       stdout=subprocess.DEVNULL)
        self.assertEqual(hash_tree_before, _hashdir(TEST_DIR))
        _assert_tree_renaming(self, expected_tree, hashes_dict,
                              expected_renaming, TEST_DIR, is_files_only=True)

    def test_rename_numbered_files_already_with_same_name_and_sequence(self):
        tree = {
            'TEST DIR 1': {
                'other file': None,
                'sample_1': None,
                'sample_2': None,
                'sample_3': None,
                'sample_4': None,
            }
        }
        hashes_dict = _create_test_tree(tree)
        expected_tree = {
            'TEST DIR 1': {
                'sample_1': None,
                'sample_2': None,
                'sample_3': None,
                'sample_4': None,
                'sample_5': None,
            }
        }
        expected_renaming = {
            'TEST DIR 1': 'TEST DIR 1',
            'sample_1': 'other file',
            'sample_2': 'sample_1',
            'sample_3': 'sample_2',
            'sample_4': 'sample_3',
            'sample_5': 'sample_4',
        }
        hash_tree_before = _hashdir(TEST_DIR)
        subprocess.run('frmt -f -n sample "TEST DIR 1"/*',
                       shell=True,
                       check=True,
                       stdout=subprocess.DEVNULL)
        self.assertEqual(hash_tree_before, _hashdir(TEST_DIR))
        _assert_tree_renaming(self, expected_tree, hashes_dict,
                              expected_renaming, TEST_DIR, is_files_only=True)


class TestExcludeDirectory(unittest.TestCase):

    _tree = {
        'TEST DIR 1': {
            'TEST FILE 1': None,
            'TEST DIR 2': {
                'TEST FILE 2': None,
                'TEST DIR 3': {
                    'TEST FILE 3': None,
                }
            }
        }
    }

    def setUp(self):
        _init_test_dir()
        os.chdir(TEST_DIR)
        self._hashes_dict = _create_test_tree(self._tree)

    def tearDown(self):
        _remove_dir(TEST_DIR)

    def test_recursive(self):
        expected_tree = {
            'TEST_DIR_1': {
                'TEST_FILE_1': None,
                'TEST DIR 2': {
                    'TEST FILE 2': None,
                    'TEST DIR 3': {
                        'TEST FILE 3': None,
                    }
                }
            }
        }
        expected_renaming = {
            'TEST_DIR_1': 'TEST DIR 1',
            'TEST_FILE_1': 'TEST FILE 1',
            'TEST DIR 2': 'TEST DIR 2',
            'TEST FILE 2': 'TEST FILE 2',
            'TEST DIR 3': 'TEST DIR 3',
            'TEST FILE 3': 'TEST FILE 3',
        }
        hash_tree_before = _hashdir(TEST_DIR)
        subprocess.run('frmt -r -e "TEST DIR 2" "TEST DIR 1"',
                       shell=True,
                       check=True,
                       stdout=subprocess.DEVNULL)
        self.assertEqual(hash_tree_before, _hashdir(TEST_DIR))
        _assert_tree_renaming(self, expected_tree,
                              self._hashes_dict, expected_renaming, TEST_DIR)


class TestToLower(unittest.TestCase):

    _tree = {
        'TEST DIR 1': {
            'TEST FILE 1': None,
            'TEST DIR 2': {
                'TEST FILE 2': None,
                'TEST DIR 3': {
                    'TEST FILE 3': None,
                }
            }
        }
    }

    def setUp(self):
        _init_test_dir()
        os.chdir(TEST_DIR)
        self._hashes_dict = _create_test_tree(self._tree)

    def tearDown(self):
        _remove_dir(TEST_DIR)

    def test_recursive(self):
        expected_tree = {
            'test_dir_1': {
                'test_file_1': None,
                'test_dir_2': {
                    'test_file_2': None,
                    'test_dir_3': {
                        'test_file_3': None,
                    }
                }
            }
        }
        expected_renaming = {
            'test_dir_1': 'TEST DIR 1',
            'test_file_1': 'TEST FILE 1',
            'test_dir_2': 'TEST DIR 2',
            'test_file_2': 'TEST FILE 2',
            'test_dir_3': 'TEST DIR 3',
            'test_file_3': 'TEST FILE 3',
        }
        hash_tree_before = _hashdir(TEST_DIR)
        subprocess.run('frmt -r -l "TEST DIR 1"',
                       shell=True,
                       check=True,
                       stdout=subprocess.DEVNULL)
        self.assertEqual(hash_tree_before, _hashdir(TEST_DIR))
        _assert_tree_renaming(self, expected_tree,
                              self._hashes_dict, expected_renaming, TEST_DIR)


class TestSubstitute(unittest.TestCase):

    _tree = {
        'TEST DIR 1': {
            'TEST FILE 1': None,
            'TEST DIR 2': {
                'TEST FILE 2': None,
                'TEST DIR 3': {
                    'TEST FILE 3': None,
                }
            }
        }
    }

    def setUp(self):
        _init_test_dir()
        os.chdir(TEST_DIR)
        self._hashes_dict = _create_test_tree(self._tree)

    def tearDown(self):
        _remove_dir(TEST_DIR)

    def test_recursive(self):
        expected_tree = {
            'SAMPLE_DIR_1': {
                'SAMPLE_FILE_1': None,
                'SAMPLE_DIR_2': {
                    'SAMPLE_FILE_2': None,
                    'SAMPLE_DIR_3': {
                        'SAMPLE_FILE_3': None,
                    }
                }
            }
        }
        expected_renaming = {
            'SAMPLE_DIR_1': 'TEST DIR 1',
            'SAMPLE_FILE_1': 'TEST FILE 1',
            'SAMPLE_DIR_2': 'TEST DIR 2',
            'SAMPLE_FILE_2': 'TEST FILE 2',
            'SAMPLE_DIR_3': 'TEST DIR 3',
            'SAMPLE_FILE_3': 'TEST FILE 3',
        }
        hash_tree_before = _hashdir(TEST_DIR)
        subprocess.run('frmt -r -s TEST/SAMPLE "TEST DIR 1"',
                       shell=True,
                       check=True,
                       stdout=subprocess.DEVNULL)
        self.assertEqual(hash_tree_before, _hashdir(TEST_DIR))
        _assert_tree_renaming(self, expected_tree,
                              self._hashes_dict, expected_renaming, TEST_DIR)


class TestRenamePP3FileInImages(unittest.TestCase):

    _tree = {
        'TEST DIR 1': {
            'TEST FILE 1.jpg': None,
            'TEST FILE 2.jpg': None,
            'TEST FILE 2.jpg.pp3': None,
            'TEST FILE 3': None,
        }
    }

    def setUp(self):
        _init_test_dir()
        os.chdir(TEST_DIR)
        self._hashes_dict = _create_test_tree(self._tree)

    def tearDown(self):
        _remove_dir(TEST_DIR)

    def test_recursive(self):
        expected_tree = {
            'TEST DIR 1': {
                'sample_1.jpg': None,
                'sample_2.jpg': None,
                'sample_2.jpg.pp3': None,
                'TEST FILE 3': None,
            }
        }
        expected_renaming = {
            'TEST DIR 1': 'TEST DIR 1',
            'sample_1.jpg': 'TEST FILE 1.jpg',
            'sample_2.jpg': 'TEST FILE 2.jpg',
            'sample_2.jpg.pp3': 'TEST FILE 2.jpg.pp3',
            'TEST FILE 3': 'TEST FILE 3',
        }
        hash_tree_before = _hashdir(TEST_DIR)
        os.chdir('TEST DIR 1')
        subprocess.run('frmt -n sample *.jpg',
                       shell=True,
                       check=True,
                       stdout=subprocess.DEVNULL)
        self.assertEqual(hash_tree_before, _hashdir(TEST_DIR))
        _assert_tree_renaming(self, expected_tree,
                              self._hashes_dict, expected_renaming, TEST_DIR)


if __name__ == '__main__':
    unittest.main()
