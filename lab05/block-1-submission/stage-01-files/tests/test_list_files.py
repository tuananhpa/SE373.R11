import json
from pathlib import Path
import pytest
import paths
from tools.files import _list, list_files
from agent import TOOLS
from observer import tool_schema


def test_listing_sorted_direct_and_schema(tmp_path, monkeypatch):
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    (workspace / 'z.md').write_text('z')
    (workspace / 'a').mkdir()
    (workspace / 'a' / 'nested.md').write_text('nested')
    monkeypatch.setattr(paths, 'WORKSPACE_DIR', workspace)
    result = json.loads(list_files.invoke({'path': '.'}))
    assert result == {'ok': True, 'path': '.', 'entries': [
        {'name': 'a', 'path': 'a', 'type': 'directory'},
        {'name': 'z.md', 'path': 'z.md', 'type': 'file'}]}
    schema = next(tool_schema(t) for t in TOOLS if t.name == 'list_files')
    assert schema['parameters']['required'] == ['path']


@pytest.mark.parametrize('path,code', [('missing', 'DIRECTORY_NOT_FOUND'),
    ('file.md', 'NOT_A_DIRECTORY'), ('../outside', 'PATH_OUTSIDE_WORKSPACE'),
    ('', 'INVALID_PATH')])
def test_invalid_paths(tmp_path, path, code):
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    (workspace / 'file.md').write_text('fake')
    assert _list(workspace, path)['error']['code'] == code
    assert _list(workspace, str(workspace.resolve()))['error']['code'] == 'PATH_OUTSIDE_WORKSPACE'


def test_empty_and_contained_parent(tmp_path):
    (tmp_path / 'inner').mkdir()
    assert _list(tmp_path, 'inner')['entries'] == []
    assert _list(tmp_path, 'inner/..')['ok'] is True


def test_symlink_escape(tmp_path):
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'fake.md').write_text('dummy data')
    try:
        (workspace / 'escape').symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip('OS does not permit symlink creation')
    assert _list(workspace, 'escape')['error']['code'] == 'PATH_OUTSIDE_WORKSPACE'
    assert _list(workspace, '.')['error']['code'] == 'PATH_OUTSIDE_WORKSPACE'
