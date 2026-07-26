#!/usr/bin/env python3
"""Reduce a `claude -p --output-format stream-json` log to a gradable summary.

Emits the final assistant message plus the sequence of tool calls, so the
"verified before writing" and "verification tools used" columns in RESULTS.md
are read off the transcript instead of recalled.

    python3 summarize_run.py run.jsonl > run_final.md
"""
import json
import sys


def main():
    path = sys.argv[1]
    tools, final, cost, turns, model = [], "", None, None, None

    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            if event.get("type") == "assistant":
                message = event.get("message", {})
                model = model or message.get("model")
                for block in message.get("content", []):
                    if block.get("type") == "tool_use":
                        target = block.get("input", {})
                        detail = (target.get("file_path") or target.get("url")
                                  or target.get("command") or target.get("pattern")
                                  or target.get("skill") or "")
                        tools.append((block.get("name"), str(detail)[:160]))
            elif event.get("type") == "result":
                final = event.get("result", "") or final
                cost = event.get("total_cost_usd", cost)
                turns = event.get("num_turns", turns)

    print(f"# Run summary — `{path.rsplit('/', 1)[-1]}`\n")
    print(f"- model: `{model}`")
    print(f"- turns: {turns}")
    print(f"- total_cost_usd: {cost}")
    print(f"- tool calls: **{len(tools)}**\n")

    print("## Tool calls, in order\n")
    if tools:
        for i, (name, detail) in enumerate(tools, 1):
            print(f"{i}. `{name}` — {detail}" if detail else f"{i}. `{name}`")
    else:
        print("_none — the agent answered without consulting anything._")

    print("\n## Final message\n")
    print(final)


if __name__ == "__main__":
    main()
