from pathlib import Path

import pytest

from laptop.storage import prepare_log_directory


def test_directory_is_created_and_probe_is_removed(tmp_path):
    directory = prepare_log_directory(tmp_path/'new logs'/'2026')
    assert directory.is_absolute() and directory.is_dir()
    assert list(directory.iterdir()) == []


@pytest.mark.parametrize('value', ['', '   '])
def test_empty_directory_rejected(value):
    with pytest.raises(ValueError):
        prepare_log_directory(value)


def test_file_cannot_be_selected_as_directory(tmp_path):
    file = tmp_path/'existing.txt'
    file.write_text('keep')
    with pytest.raises(OSError):
        prepare_log_directory(file)
    assert file.read_text() == 'keep'
