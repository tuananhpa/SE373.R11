import importlib.util
import json
import sys
import tempfile
import types
from pathlib import Path

# Only replaces the decorator for dependency-free checks of the actual filesystem implementation.
core = types.ModuleType('langchain_core')
tools = types.ModuleType('langchain_core.tools')
tools.tool = lambda function: function
sys.modules['langchain_core'] = core
sys.modules['langchain_core.tools'] = tools
base = Path(__file__).resolve().parent
results = []
for stage in ['stage-01-files', 'stage-02-skills']:
    paths = types.ModuleType('paths')
    paths.OUTPUT_SUBDIR = 'output'
    paths.WORKSPACE_DIR = base / stage / 'workspace'
    sys.modules['paths'] = paths
    spec = importlib.util.spec_from_file_location('file_impl', base / stage / 'tools/files.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for path, expected in [('data/policies', None), ('data/policies/policy-before-oct.md', 'NOT_A_DIRECTORY'),
                           ('data/does-not-exist', 'DIRECTORY_NOT_FOUND'), ('../outside', 'PATH_OUTSIDE_WORKSPACE'),
                           (str(paths.WORKSPACE_DIR.resolve()), 'PATH_OUTSIDE_WORKSPACE')]:
        result = json.loads(module.list_files(path))
        assert (result.get('error') or {}).get('code') == expected
        if expected is None:
            assert [e['name'] for e in result['entries']] == sorted(e['name'] for e in result['entries'])
            assert len(result['entries']) == 2
        results.append({'stage': stage, 'path': path if not Path(path).is_absolute() else '<absolute workspace>', 'result': result})
    with tempfile.TemporaryDirectory(dir=base) as td:
        root = Path(td) / 'workspace'
        root.mkdir()
        (root / 'a-dir').mkdir()
        (root / 'a-dir/nested.md').write_text('fake')
        (root / 'z.md').write_text('fake')
        listing = module._list(root, '.')
        assert listing['entries'] == [{'name': 'a-dir', 'path': 'a-dir', 'type': 'directory'}, {'name': 'z.md', 'path': 'z.md', 'type': 'file'}]
        assert module._list(root, 'a-dir')['entries'][0]['path'] == 'a-dir/nested.md'
        outside = Path(td) / 'outside'
        outside.mkdir()
        try:
            (root / 'escape').symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            results.append({'stage': stage, 'symlink': 'SKIPPED', 'reason': str(exc)})
        else:
            assert module._list(root, 'escape')['error']['code'] == 'PATH_OUTSIDE_WORKSPACE'
            assert module._list(root, '.')['error']['code'] == 'PATH_OUTSIDE_WORKSPACE'
            results.append({'stage': stage, 'symlink': 'PASS'})
(base / 'tool-check-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
print('PASS: direct filesystem checks for both stages; see tool-check-results.json')
