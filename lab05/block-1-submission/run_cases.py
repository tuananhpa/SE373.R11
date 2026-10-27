"""Run real configured model; every case starts with fresh history. No mock traces."""
import argparse
import json
import sys
import uuid
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('stage', choices=['stage-00-chat', 'stage-01-files', 'stage-02-skills'])
parser.add_argument('--env', type=Path, help='Existing model configuration; never copied into submission')
args = parser.parse_args()
root = Path(__file__).resolve().parent
stage = root / args.stage
sys.path.insert(0, str(stage))
from dotenv import load_dotenv
if args.env:
    load_dotenv(args.env, override=False)
from agent import build_agent, build_model, capabilities
from config import load_settings, RECURSION_LIMIT
from observer import Observer, serialize_message
from trace import TraceWriter
from langchain_core.messages import HumanMessage
settings, missing = load_settings()
if missing:
    raise SystemExit('Missing model configuration: ' + ', '.join(missing))
cases = {
    'A': 'Tôi mua ngày 28/09/2026, yêu cầu hoàn ngày 06/10/2026, chưa kích hoạt. Tôi có được hoàn không?',
    'B': 'Tôi mua ngày 02/10/2026, yêu cầu hoàn ngày 12/10/2026, chưa kích hoạt. Tôi có được hoàn không?',
    'missing': 'Tôi mua ngày 02/10/2026, muốn hoàn ngày 12/10/2026.'}

def execute(label, question):
    observer = Observer(conversation_id=uuid.uuid4().hex)
    observer.start_turn(uuid.uuid4().hex)
    writer = TraceWriter(stage / 'traces', args.stage, observer.conversation_id, observer.run_id, 1)
    writer.write(observer.record('user_submitted', {'text': question, **capabilities()}))
    history = [HumanMessage(content=question)]
    graph = build_agent(build_model(settings))
    try:
        for mode, chunk in graph.stream({'messages': history}, config={'recursion_limit': RECURSION_LIMIT}, stream_mode=['custom', 'updates']):
            if mode == 'custom' and chunk.get('observer'):
                writer.write(observer.record(chunk['event'], chunk['data']))
            elif mode == 'updates':
                for update in chunk.values():
                    if isinstance(update, dict) and update.get('messages'):
                        history.extend(update['messages'])
        writer.write(observer.record('run_completed', {'messages': [serialize_message(m) for m in history], 'answer': history[-1].content}))
        (stage / 'traces' / (label + '-index.json')).write_text(json.dumps({'trace': writer.path.name, 'question': question}, ensure_ascii=False, indent=2), encoding='utf-8')
        print(label, writer.path.name)
    except Exception as exc:
        writer.write(observer.record('run_failed', {'error': str(exc)}))
        raise

execute('A', cases['A'])
if args.stage != 'stage-00-chat':
    execute('B', cases['B'])
    policy_dir = stage / 'workspace/data/policies'
    mappings = [('policy-before-oct.md', 'terms-legacy.md'), ('policy-from-oct.md', 'terms-current.md')]
    try:
        for old, new in mappings:
            (policy_dir / old).rename(policy_dir / new)
        execute('A-renamed', cases['A'])
        execute('B-renamed', cases['B'])
    finally:
        for old, new in mappings:
            if (policy_dir / new).exists():
                (policy_dir / new).rename(policy_dir / old)
    execute('missing', cases['missing'])
