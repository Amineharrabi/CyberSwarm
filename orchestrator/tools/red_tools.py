"""
Red tools — typed wrappers executed inside red-box via `docker exec`. Each returns the
contract {ok, summary, data}. Every call goes through the Guard first (target allowlist,
budget) and is appended to the round action log, which is the ground truth for scoring
and ML labels.

Scope: recon + web testing against the lab's own intentionally weak app. No DoS tools.
"""
import json
import subprocess
from guard import Guard, GuardError

REDBOX = "cs_redbox"


def _exec(args, timeout=60):
    """Run a command inside red-box. args is a list (never a shell string)."""
    full = ["docker", "exec", REDBOX] + args
    p = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
    return p.stdout + p.stderr


def _log(action_log, agent, tool, args, status, summary):
    action_log.append(dict(agent=agent, tool=tool, args=args, status=status, summary=summary))


# --- Tool schemas exposed to the LLM (OpenAI function-calling format) ---
SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "scan_ports",
            "description": "TCP port scan of a single lab host to discover services.",
            "parameters": {
                "type": "object",
                "properties": {"target": {"type": "string", "description": "lab IP, e.g. 10.10.2.10"}},
                "required": ["target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "http_get",
            "description": "HTTP GET a URL on a lab host. Use to enumerate endpoints.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "http_login",
            "description": "POST username/password to the webapp /login endpoint. The username field is where an auth-bypass string can be tried.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "host:port, e.g. 10.10.2.10:5000"},
                    "username": {"type": "string"},
                    "password": {"type": "string"},
                },
                "required": ["target", "username", "password"],
            },
        },
    },
]


class RedTools:
    def __init__(self, guard: Guard, action_log: list):
        self.g = guard
        self.log = action_log

    def scan_ports(self, target):
        self.g.budget()
        self.g.check_target(target)
        host = target.split(":")[0]
        out = _exec(["nmap", "-Pn", "-T4", "--top-ports", "50", host], timeout=120)
        summary = self.g.cap(out)
        _log(self.log, "red", "scan_ports", {"target": target}, "ok", summary[:200])
        return {"ok": True, "summary": summary, "data": {"target": target}}

    def http_get(self, url):
        self.g.budget()
        # pull host out of the URL for the allowlist check
        hostpart = url.split("//", 1)[-1].split("/", 1)[0]
        self.g.check_target(hostpart)
        out = _exec(["curl", "-s", "-m", "10", "-i", url], timeout=20)
        summary = self.g.cap(out)
        _log(self.log, "red", "http_get", {"url": url}, "ok", summary[:200])
        return {"ok": True, "summary": summary, "data": {"url": url}}

    def http_login(self, target, username, password):
        self.g.budget()
        self.g.check_target(target)
        # username/password are form values sent with --data-urlencode, never shell-interpolated
        url = f"http://{target}/login"
        out = _exec([
            "curl", "-s", "-m", "10", "-i", url,
            "--data-urlencode", f"username={username}",
            "--data-urlencode", f"password={password}",
        ], timeout=20)
        summary = self.g.cap(out)
        _log(self.log, "red", "http_login", {"target": target, "username": username}, "ok", summary[:200])
        return {"ok": True, "summary": summary, "data": {"target": target}}

    # dispatch table used by the agent loop
    def call(self, name, **kwargs):
        try:
            fn = getattr(self, name)
        except AttributeError:
            return {"ok": False, "summary": f"unknown tool {name}", "data": {}}
        try:
            return fn(**kwargs)
        except GuardError as e:
            _log(self.log, "red", name, kwargs, "blocked", str(e))
            return {"ok": False, "summary": f"blocked by guard: {e}", "data": {}}
        except Exception as e:
            _log(self.log, "red", name, kwargs, "error", str(e))
            return {"ok": False, "summary": f"error: {e}", "data": {}}
