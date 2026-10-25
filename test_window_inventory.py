"""Read-only status smoke test. Does not restore game windows."""
from pathlib import Path
from arena_window_control import inspect_session, read_session, _process_info
root=Path(__file__).resolve().parent
session=read_session(root)
print("SESSION",session)
result=inspect_session(root)
print("WINDOWS",result)
assert len(result)==3
assert result[0]["slot"]==1
assert result[1]["slot"]==2
assert result[2]["slot"]==3
assert result[2]["label"]=="미설정" if session.get("ObserverPid") is None else True
print("PASS: read-only status/foreground logic")
