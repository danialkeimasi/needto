import typing
import click
import sys
from simple_term_menu import TerminalMenu
import rich.console
import rich.prompt

EDITOR_TEMPLATE = """{command}

# save this file to confirm the command or quit to skip it.
# after save, you will {confirm_prompt} this command.
"""


def prompt_menu(
    items: list[str],
    *,
    ask_for_edit=False,
    no_op_value="-- non of this options, want to explain more --",
    confirm_prompt="",
    preview_command: None | str | typing.Callable[[str], str] = None,
):
    items_to_prompt: list[str] = [no_op_value] + items
    menu_entry_index = TerminalMenu(
        [command.replace("|", r"\|") for command in items_to_prompt],
        preview_command=preview_command,
    ).show()
    selected_item: str = items_to_prompt[menu_entry_index]

    if selected_item == no_op_value:
        return

    if ask_for_edit and sys.stdin.isatty():
        if edited_text := click.edit(
            text=EDITOR_TEMPLATE.format(
                command=selected_item, confirm_prompt=confirm_prompt.lower()
            )
        ):
            lines = [
                line
                for line in edited_text.split("\n")
                if line.strip() and not line.strip().startswith("#")
            ]
            if len(lines) == 1:
                selected_item = lines[0].strip()
        else:
            return

    if not sys.stdin.isatty():
        sys.stdin = open("/dev/tty")

        if confirm_prompt and not rich.prompt.Confirm.ask(
            f"{confirm_prompt} '{selected_item}'", default=False
        ):
            return

    return selected_item


def prompt_menu_and_print(
    items: list[str],
    *,
    ask_for_edit=False,
    no_op_value="-- non of this options, want to explain more --",
    confirm_prompt="",
    preview_command: None | str | typing.Callable[[str], str] = None,
):
    selected_item = prompt_menu(
        items,
        ask_for_edit=ask_for_edit,
        no_op_value=no_op_value,
        confirm_prompt=confirm_prompt,
        preview_command=preview_command,
    )

    console = rich.console.Console()
    print()
    for command in items:
        if command == selected_item:
            console.print(f"$ {command}", style="black on white")
        else:
            console.print(f"$ {command}")
    print()

    return selected_item
