import os
import click
import json
import sys
import platform
from simple_term_menu import TerminalMenu
import typer
from groq import Groq
import rich.console
import rich.prompt
import subprocess
from rich.markdown import Markdown

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

app = typer.Typer()


class AIClient:
    def __init__(self, *, system_prompt: str, model_name: str = "llama3-70b-8192"):
        console = rich.console.Console()
        self.model_name = model_name
        final_prompt = f"""{system_prompt}
        System Info: OS: {platform.system()}, Arch: {platform.machine()}"""
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

    def ask(self, prompt: str, print_prompt=False, output_limit: int = 2000):
        prompt = prompt.strip()
        console = rich.console.Console()
        if print_prompt:
            print()
            console.print(prompt)
            print()
        self.messages.append({"role": "user", "content": prompt[:output_limit]})

        answer = ""
        for try_count in range(3):
            chat_completion = client.chat.completions.create(
                messages=self.messages, model=self.model_name
            )
            answer = chat_completion.choices[0].message.content
            self.messages.append({"role": "system", "content": answer})
            try:
                return json.loads(answer.replace(r"\'", "\\'"))
            except json.decoder.JSONDecodeError:
                with open(f"error_{try_count}.txt", "w") as fp:
                    fp.write(answer)


def prompt_commands(recommended_commands: list[str], *, ask_for_edit=False):
    console = rich.console.Console()
    NO_OP = "----"
    commands_to_prompt: list[str] = [NO_OP] + recommended_commands
    menu_entry_index = TerminalMenu(
        [command.replace("|", r"\|") for command in commands_to_prompt],
    ).show()
    selected_command: str = commands_to_prompt[menu_entry_index]

    print()
    for command in recommended_commands:
        if command == selected_command:
            console.print(f"$ {command}", style="black on white")
        else:
            console.print(f"$ {command}")
    print()

    if selected_command == NO_OP:
        return

    if ask_for_edit and sys.stdin.isatty():
        if edited_text := click.edit(text=selected_command):
            selected_command = edited_text.strip()

    if selected_command.startswith("#"):
        return

    if not sys.stdin.isatty():
        sys.stdin = open("/dev/tty")

    if not rich.prompt.Confirm.ask(f"Running '{selected_command}'", default=False):
        return

    return selected_command


def run_command(command: str):
    console = rich.console.Console()
    try:
        result = subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        console.print(e)
        sys.exit(e.returncode)
    else:
        console.print(f"Successfully ran '{command}'.")
        sys.exit(result.returncode)


@app.command()
def cli(prompt: str):
    console = rich.console.Console()
    system_prompt = """
    You are a CLI code generator. User will search for a command, you respond with a list of CLI commands.
    Always answer in json in all your responses starting with '{' and ending with '}' with these keys:
    "description" (str), "warning" (str only if necessary), "commands" (list of str), needs_manual_change (bool).
    """
    ai_client = AIClient(system_prompt=system_prompt)
    parsed_answer = ai_client.ask(prompt)

    console.print(parsed_answer["description"], style="bold blue")
    if warning := parsed_answer.get("warning"):
        console.print(warning, style="bold yellow")

    if selected_command := prompt_commands(
        parsed_answer["commands"],
        ask_for_edit=parsed_answer["needs_manual_change"],
    ):
        run_command(selected_command)


@app.command()
def ask(prompt: str):
    console = rich.console.Console()
    system_prompt = """
    You are a AI assistant.
    You can ask user to run commands and send the output of commands to you, to help you answer their questions.
    Always answer in json in all your responses starting with '{' and ending with '}' with these keys:
    "help" (str), "commands_to_explore" (list of str only if necessary), "files_to_save": (object with name to content)

    Example response:

    {"help": "here is python script", "commands_to_explore": [], "files_to_save": {"main.py": "import request\nrequest.get("https://google.com")"}}
    """
    console = rich.console.Console()
    ai_client = AIClient(system_prompt=system_prompt)
    parsed_answer = ai_client.ask(prompt)
    while True:
        console.print(Markdown(parsed_answer["help"]))
        print()
        for file_name, file_content in parsed_answer["files_to_save"].items():
            while os.path.exists(file_name):
                file_name = rich.prompt.Prompt.ask(
                    f"[bold red]'{file_name}' already exists[/bold red]. Please enter a new name",
                )
            with open(file_name, "w") as f:
                f.write(file_content)
            console.print(f"'{file_name}' saved.", style="bold green")

        if commands := parsed_answer.get("commands_to_explore"):
            if command := prompt_commands(commands):
                try:
                    command_output = subprocess.run(
                        command, shell=True, capture_output=True
                    )
                except subprocess.CalledProcessError as e:
                    parsed_answer = ai_client.ask(
                        f"Failed to run '{command}': {e}", print_prompt=True
                    )
                else:
                    parsed_answer = ai_client.ask(
                        f"Output of '{command}':\n"
                        + f"stdout:\n{command_output.stdout.decode()}\n"
                        + (
                            f"stderr:\n{command_output.stderr.decode()}"
                            if command_output.stderr
                            else ""
                        ),
                        print_prompt=True,
                    )
            else:
                if user_prompt := input("> "):
                    print()
                    parsed_answer = ai_client.ask(user_prompt)
                else:
                    break
        else:
            break


if __name__ == "__main__":
    app()
