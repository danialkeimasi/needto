import time
import sys
import rich.console
import rich.prompt
from .config import config_manager

import rich.console
import json
import platform
import groq


def get_system_info():
    if platform.system() == "Linux":
        import distro

        distro_info = (
            f"Distro: {distro.id()} ({distro.like()}) {distro.version(best=True)}"
        )
    else:
        distro_info = ""

    return f"""
    {str(platform.uname())}
    {distro_info}
    """.strip()


class AIClient:
    def __init__(self, *, system_prompt: str):
        final_prompt = f"""{system_prompt}

        System Info:
        {get_system_info()}"""

        console = rich.console.Console()
        messages = [
            {"role": "system", "content": final_prompt.strip().replace("    ", "")},
        ]
        if stdin := "" if sys.stdin.isatty() else sys.stdin.read():
            console.print("Got this from stdin:")
            console.print(stdin)
            messages.append(
                {"role": "user", "content": f"Additional information:\n{stdin}"}
            )
        self.messages = messages

        self.client = groq.Groq(
            api_key=config_manager.values.groq_api_key,
        )

    def ask(self, prompt: str, print_prompt=False, output_limit: int = 2000):
        prompt = prompt.strip()[:output_limit]
        console = rich.console.Console()
        if print_prompt:
            print()
            console.print(prompt)
            print()

        self.messages.append({"role": "user", "content": prompt})

        retry_count = 3
        for _ in range(retry_count):
            chat_completion = self.client.chat.completions.create(
                messages=self.messages,
                model=config_manager.values.model_name,
                # response_format={"type": "json_object"},
            )
            answer = chat_completion.choices[0].message.content

            try:
                parsed_answer = json.loads(answer)
            except json.JSONDecodeError:
                self.messages.append(
                    {
                        "role": "user",
                        "content": "Last response was not JSON. Always write JSON.",
                    }
                )
            else:
                self.messages.append({"role": "system", "content": answer})
                return parsed_answer
