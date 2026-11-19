"""
base.py — the generic LLM tool-use loop shared by Red and Blue.
observe -> reason -> tool call -> observe, until step budget or a stop condition.

Uses the OpenAI-compatible client, so it works against Ollama or vLLM unchanged
(base_url + model from experiment.yaml). Tool calling is native (tools=SCHEMAS).
"""
import json
from openai import OpenAI


class Agent:
    def __init__(self, name, client: OpenAI, model, system_prompt, schemas, toolset, max_steps=8):
        self.name = name
        self.client = client
        self.model = model
        self.schemas = schemas
        self.toolset = toolset           # object with .call(name, **kwargs)
        self.messages = [{"role": "system", "content": system_prompt}]
        self.max_steps = max_steps

    def add_context(self, text):
        """Inject playbook / memory / debrief into the conversation before the round."""
        self.messages.append({"role": "user", "content": text})

    def run(self, opening_user_msg, on_step=None):
        self.messages.append({"role": "user", "content": opening_user_msg})
        transcript = []
        for step in range(self.max_steps):
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self.schemas,
                tool_choice="auto",
                temperature=0.3,
            )
            msg = resp.choices[0].message
            self.messages.append(msg.model_dump(exclude_none=True))

            if not msg.tool_calls:
                # model answered in prose: record and stop (it decided it's done)
                transcript.append({"step": step, "thought": msg.content})
                if on_step:
                    on_step(self.name, step, None, msg.content)
                break

            for tc in msg.tool_calls:
                fn = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = self.toolset.call(fn, **args)
                transcript.append({"step": step, "tool": fn, "args": args, "result": result["summary"][:300]})
                if on_step:
                    on_step(self.name, step, fn, result["summary"][:200])
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps({"ok": result["ok"], "summary": result["summary"]})[:4000],
                })
        return transcript
