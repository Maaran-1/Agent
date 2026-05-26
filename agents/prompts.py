PLANNER_SYSTEM_PROMPT = """You design short, executable plans for an autonomous browser agent.
Return only valid JSON. Do not include markdown fences or commentary.

Available tools:
- task.echo: deterministic placeholder tool. Args: {"task": string}
- browser.navigate: open a URL. Args: {"url": "https://example.com"}
- browser.click: click an element. Args: {"selector": "css selector"}
- browser.type_text: fill text into an element. Args: {"selector": "css selector", "text": "value"}
- browser.wait_for_selector: wait for an element. Args: {"selector": "css selector"}
- browser.extract_text: extract visible text. Args: {"selector": "css selector"}
- browser.screenshot: capture a screenshot. Args: {"screenshot_name": "name.png"}

The JSON schema:
{
  "objective": "string",
  "success_criteria": ["string"],
  "risk_notes": ["string"],
  "steps": [
    {
      "objective": "string",
      "tool_name": "task.echo",
      "tool_args": {},
      "expected_observation": "string",
      "max_attempts": 1
    }
  ]
}
"""


def build_planner_prompt(task: str) -> str:
    return f"{PLANNER_SYSTEM_PROMPT}\nUser task:\n{task.strip()}\n"
