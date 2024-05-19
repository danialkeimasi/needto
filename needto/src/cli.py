import os
import click
import sys
import typer
import rich.console
import rich.prompt
import subprocess

from .config import config_manager
from .ai_client import AIClient
from .utils import prompt_menu_and_print

app = typer.Typer(no_args_is_help=True)


@app.command(help="Find and run a command.")
def do(prompt_list: list[str]):
    prompt = " ".join(prompt_list)
    console = rich.console.Console()
    system_prompt = """
    You are a CLI code generator. User will search for a command, you respond with a list of CLI commands.
    Don't write markdown.
    Response should always be JSON stars with "{" and ends with "}" with these keys:
    "description" (str), "warning" (str only if necessary), "commands" (list of str).
    Don't explain at begin or end of JSON.
    """
    console = rich.console.Console()
    ai_client = AIClient(system_prompt=system_prompt)
    parsed_answer = ai_client.ask(prompt)

    while True:
        console.print(parsed_answer["description"], style="bold blue")

        if warning := parsed_answer.get("warning"):
            console.print(warning, style="bold yellow")

        if selected_command := prompt_menu_and_print(
            parsed_answer["commands"],
            ask_for_edit=True,
            confirm_prompt="Run",
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
            console.print("Leave blank to end conversation", style="blue bold")
            if user_prompt := input("> "):
                print()
                parsed_answer = ai_client.ask(user_prompt)
            else:
                break


@app.command(help="Ask question, Send output of commands to AI to get help.")
def ask(prompt_list: list[str]):
    prompt = " ".join(prompt_list)
    system_prompt = """
    You are a AI assistant. User will ask you something and you will help him find their answer.
    You can ask user to run commands and send the output of commands to you, to help you answer their questions.
    Don't recommend commands that can change the system state.
    Don't write markdown.
    Response should always be JSON stars with "{" and ends with "}" with these keys:
    "help" (text), "commands_to_explore" (list of str only if necessary)
    Don't explain at begin or end of JSON.
    """
    console = rich.console.Console()
    ai_client = AIClient(system_prompt=system_prompt)
    parsed_answer = ai_client.ask(prompt)
    while True:
        console.print(parsed_answer["help"])
        print()

        if commands := parsed_answer.get("commands_to_explore"):
            if command := prompt_menu_and_print(
                commands, confirm_prompt="Run and send output of", ask_for_edit=True
            ):
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
                console.print("Leave blank to end conversation", style="blue bold")
                if user_prompt := input("> "):
                    print()
                    parsed_answer = ai_client.ask(user_prompt)
                else:
                    break
        else:
            break


@app.command(help="Write code.")
def write(prompt_list: list[str]):
    prompt = " ".join(prompt_list)
    system_prompt = """
    You are a AI assistant. User will ask you to write a code.
    You can ask user to clarify what they need and then run the code.
    Don't write markdown.
    Response should always be JSON stars with "{" and ends with "}" with these keys:
    "help" (text), "files_to_save": (object with name to content)
    Don't explain at begin or end of JSON.
    """
    console = rich.console.Console()
    ai_client = AIClient(system_prompt=system_prompt)
    parsed_answer = ai_client.ask(prompt)
    while True:
        console.print(parsed_answer["help"])
        files_to_save = parsed_answer.get("files_to_save", {})
        print()
        if files_to_save:
            if selected_file_name := prompt_menu_and_print(
                list(files_to_save.keys()),
                preview_command=lambda file_name: files_to_save.get(file_name, ""),
            ):
                file_content = files_to_save[selected_file_name]
                while os.path.exists(selected_file_name):
                    selected_file_name = console.print(
                        f"[bold red]'{selected_file_name}' already exists[/bold red]. Please enter a new name",
                    )
                with open(selected_file_name, "w") as f:
                    f.write(file_content)
                console.print(f"'{selected_file_name}' saved.", style="bold green")
                break

        console.print("Leave blank to end conversation", style="blue bold")
        if user_prompt := input("> "):
            print()
            parsed_answer = ai_client.ask(user_prompt)
        else:
            break


@app.command(help=f"Open editor for '{config_manager.config_path}'.")
def config():
    click.edit(filename=config_manager.config_path)
