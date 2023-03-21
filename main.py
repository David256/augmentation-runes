"""
Do stuffs
"""

import os
import re
import argparse
import pathlib
import json

import openai
from openai.error import Timeout as TimeoutError
import inquirer
import pyperclip
from rich import print

from schemas import Processment, Prompt, Response, RuneDefinition

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print('Missing OPENAI_API_KEY environment')
    exit(-1)

PROMPT_TO_GENERATE = '''Escribe 10 párrafos que sean variación del siguiente párrafo:

la runa {rune_name}{invert}: {text}

Pero no te salgas de la runa {rune_name}{invert}
'''

PROMPT_TO_SUMMARY = '''Resume bien resumido este párrafo sin agregar nada más: {text}'''

REGEX_ITEM = re.compile(r'\d+\.')


def get_args():
    """
    Create and return an argparse object.Namespace that contains the passed
    arguments from the command line.

    Returns:
        argparse.Namespace: The object that contains the passed arguments from
                            the command line.
    """
    parser = argparse.ArgumentParser(
        description='The augmentation runes tool',
    )
    # Add the cli args
    parser.add_argument(
        'target_path',
        help='The JSON file path to read the possible rune values',
    )
    # Parse the args
    args = parser.parse_args()
    return args


def load_json_file(target_path: str) -> list[RuneDefinition]:
    """
    Load the JSON file content and convert it in a list of RuneDefinition
    objects.

    Args:
        target_path (str): The JSON file path that will be loaded.

    Returns:
        List[RuneDefinition]: A RuneDefinition object list created from the JSON
                              file content.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    path = pathlib.Path(target_path)
    if not path.exists():
        raise FileNotFoundError(f'file is not found: {target_path}')
    content = path.read_text(encoding='utf-8')
    rune_json = json.loads(content)
    return [RuneDefinition(**item) for item in rune_json]


def ask_openai(prompt: str) -> Response:
    """Ask to OpenAI."""
    prompt_messages = [
        Prompt(role='system', content='You are a helpful assistant.'),
        Prompt(role='user', content=prompt),
    ]

    while True:
        try:
            raw_response: dict = openai.ChatCompletion.create(
                model='gpt-3.5-turbo',
                messages=[p.dict() for p in prompt_messages],
            )
        except TimeoutError as err:
            print(err)
            continue
        break
    response = Response(**raw_response)
    return response


def parse_response(response: str) -> list[str]:
    """
    Split the response and return a list of responses.
    """
    options = response.split('\n')
    options = list(
        map(lambda x: REGEX_ITEM.sub('', x).strip(),
            filter(lambda x: bool(x.strip()), options)))
    return options


def get_only_the_rune_name(rune_name: str) -> str:
    """Get only the rune name."""
    if rune_name.startswith('RUNA'):
        rune_name = rune_name[len('RUNA'):].strip()
    return rune_name


def create_string_from_list(items: list[str]) -> str:
    """
    Create a return an splited strings by comma that contains all the elements
    of the given list, each one is wrapped in double quotes.

    Args:
        items (list[str]): The list of element to convert in a string.

    Returns:
        str: The created string that contains all the elements of the
             given list, each one is wrapped in double quotes and splited
            by comma.
    """
    copied: str = ''
    for i,item in enumerate(items):
        copied += f'"{item}"'
        if i < len(items) - 1:
            copied += ','
        copied += '\n'
    return copied


def process_summaries(processment: Processment) -> Processment:
    """
    Process and generate the summaries.
    """
    summaries: list[str] = []
    for i,alternative in enumerate(processment.rune_definition.alternatives):
        prompt = PROMPT_TO_SUMMARY.format(text=alternative)
        print(f'{i+1}: [cyan]{prompt}[/]\n\n')
        confirmed: bool = inquirer.confirm('Ask to OpenAI for this prompt?')
        if not confirmed:
            print('[red]Ignored[/]')
            continue

        response = ask_openai(prompt)
        print(f'Usage tokens: [bold blue]{response.usage.total_tokens}[/]')
        processment.total_tokens += response.usage.total_tokens

        choice, = response.choices
        content: str = choice.message.content

        print(f'{content}\n')
        will_add = inquirer.confirm('Add?', default=True)
        if will_add:
            summaries.append(content)
            print('[green]Added![/]\n')
        summaries.append(content)

    # Print all the summaries
    print('Summaries:')
    for i,summary in enumerate(summaries):
        print(f'{i + 1} - {summary}\n')

    will_copy = inquirer.confirm('Copy?', default=True)
    if will_copy:
        copied = create_string_from_list(summaries)
        assert len(copied) > 0
        pyperclip.copy(copied)
        print('[green]Copied![/]\n')
    return processment


def process_alternatives(processment: Processment) -> Processment:
    """
    Process and generate the alternatives.
    """
    rune_name = get_only_the_rune_name(processment.rune_definition.rune_name)
    # Generate a prompt
    prompt = PROMPT_TO_GENERATE.format(
        rune_name=rune_name,
        invert=(
            ' invertida'
            if processment.rune_definition.type == 'invert'
            else ''
            ),
        text=processment.rune_definition.description,
    )

    print(f'[cyan]{prompt}[/]\n\n')
    confirmed: bool = inquirer.confirm('Ask to OpenAI for this prompt?')
    if not confirmed:
        print('[red]Ignored[/]')
        return processment

    # Do the request for this prompt and add the total token amount
    response = ask_openai(prompt)
    print(f'Usage tokens: [bold blue]{response.usage.total_tokens}[/]')
    processment.total_tokens += response.usage.total_tokens

    choice, = response.choices
    content: str = choice.message.content
    items = parse_response(content)

    print('Items:')
    for i,item in enumerate(items):
        print(i + 1, '-', item)
        print()

    will_copy = inquirer.confirm('Copy?', default=True)
    if will_copy:
        copied = create_string_from_list(items)
        pyperclip.copy(copied)
        print('[green]Copied![/]\n')

    return processment


def main():
    """The main function"""
    # Get the args to get the target path
    args = get_args()
    total_tokens: int = 0

    # Set the OpenAI key
    openai.api_key = OPENAI_API_KEY

    # Get the rune definitions & filter whih does not have alternatives
    rune_definitions = load_json_file(args.target_path)
    print(f'{len(rune_definitions)} loaded')

    # Iterate for each rune definition and generate the prompt
    for i,rune_definition in enumerate(rune_definitions):
        processment = Processment(rune_definition=rune_definition)
        if rune_definition.alternatives and rune_definition.summaries:
            continue

        print(f'[bold green]{i}[/] -:\n')

        # Check if missing the alternatives
        if not processment.rune_definition.alternatives:
            processment = process_alternatives(processment)
        # Check if missing the summaries
        if processment.rune_definition.alternatives and \
            not processment.rune_definition.summaries:
            processment = process_summaries(processment)

        # Add the total of tokens
        total_tokens += processment.total_tokens
        print(f'tokens: [bold blue]{total_tokens}[/]')

    print(f'tokens: [bold blue]{total_tokens}[/]')


if __name__ == '__main__':
    main()
