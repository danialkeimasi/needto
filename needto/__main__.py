import typing
import os
import click
import json
import sys
import platform
from simple_term_menu import TerminalMenu
import typer
import groq
import rich.console
import rich.prompt
import subprocess
from rich.markdown import Markdown

try:
    client = groq.Groq(
        api_key=os.environ.get("GROQ_API_KEY"),
    )
except groq.GroqError:
    print("Please set GROQ_API_KEY environment variable.")
    sys.exit(1)

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
        prompt = prompt.strip()[:output_limit]
        console = rich.console.Console()
        if print_prompt:
            print()
            console.print(prompt)
            print()

        self.messages.append({"role": "user", "content": prompt})
        chat_completion = client.chat.completions.create(
            messages=self.messages,
            model=self.model_name,
            response_format={"type": "json_object"},
        )
        answer = chat_completion.choices[0].message.content
        self.messages.append({"role": "system", "content": answer})
        try:
            return json.loads(answer)
        except json.decoder.JSONDecodeError:
            with open("error.txt", "w") as fp:
                fp.write(answer)


def prompt_menu(
    recommended_commands: list[str],
    *,
    ask_for_edit=False,
    confirm_prompt="",
    preview_command: None | str | typing.Callable[[str], str] = None,
):
    console = rich.console.Console()
    NO_OP = "-- explain more --"
    commands_to_prompt: list[str] = [NO_OP] + recommended_commands
    menu_entry_index = TerminalMenu(
        [command.replace("|", r"\|") for command in commands_to_prompt],
        preview_command=preview_command,
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

    if confirm_prompt and not rich.prompt.Confirm.ask(
        f"{confirm_prompt} '{selected_command}'", default=False
    ):
        return

    return selected_command


@app.command()
def find(prompt: str):
    console = rich.console.Console()
    system_prompt = """
    You are a CLI code generator. User will search for a command, you respond with a list of CLI commands.
    Always answer in json in all your responses with these keys:
    "description" (str), "warning" (str only if necessary), "commands" (list of str), needs_manual_change (bool).
    """
    console = rich.console.Console()
    ai_client = AIClient(system_prompt=system_prompt)
    parsed_answer = ai_client.ask(prompt)

    while True:
        console.print(parsed_answer["description"], style="bold blue")
        if warning := parsed_answer.get("warning"):
            console.print(warning, style="bold yellow")

        if selected_command := prompt_menu(
            parsed_answer["commands"],
            ask_for_edit=parsed_answer["needs_manual_change"],
            confirm_prompt="Running",
        ):
            try:
                result = subprocess.run(selected_command, shell=True, check=True)
            except subprocess.CalledProcessError as e:
                console.print(e)
                sys.exit(e.returncode)
            else:
                console.print(f"Successfully ran '{selected_command}'.")
                sys.exit(result.returncode)
        else:
            if user_prompt := input("> "):
                print()
                parsed_answer = ai_client.ask(user_prompt)
            else:
                break


@app.command()
def ask(prompt: str):
    system_prompt = """
    You are a AI assistant. User will ask you something and you will help him find their answer.
    You can ask user to run commands and send the output of commands to you, to help you answer their questions.
    Always answer in json in all your responses with these keys:
    "help" (markdown str), "commands_to_explore" (list of str only if necessary)
    """
    console = rich.console.Console()
    ai_client = AIClient(system_prompt=system_prompt)
    parsed_answer = ai_client.ask(prompt)
    while True:
        console.print(Markdown(parsed_answer["help"]))
        print()

        if commands := parsed_answer.get("commands_to_explore"):
            if command := prompt_menu(commands):
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


@app.command()
def write(prompt: str):
    system_prompt = """
    You are a AI assistant. User will ask you to write a code.
    You can ask user to clarify what they need and then run the code.
    Always answer in json in all your responses with these keys:
    "help" (markdown str), "files_to_save": (object with name to content)
    """
    console = rich.console.Console()
    ai_client = AIClient(system_prompt=system_prompt)
    parsed_answer = ai_client.ask(prompt)
    while True:
        console.print(Markdown(parsed_answer["help"]))
        files_to_save = parsed_answer.get("files_to_save", {})
        print()
        if files_to_save:
            if selected_file_name := prompt_menu(
                list(files_to_save.keys()),
                preview_command=lambda file_name: files_to_save.get(file_name, ""),
            ):
                file_content = files_to_save[selected_file_name]
                while os.path.exists(selected_file_name):
                    selected_file_name = rich.prompt.Prompt.ask(
                        f"[bold red]'{selected_file_name}' already exists[/bold red]. Please enter a new name",
                    )
                with open(selected_file_name, "w") as f:
                    f.write(file_content)
                console.print(f"'{selected_file_name}' saved.", style="bold green")
                break

        if user_prompt := input("> "):
            print()
            parsed_answer = ai_client.ask(user_prompt)
        else:
            break


if __name__ == "__main__":
    app()
