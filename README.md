# Needto

[![PyPI - Version](https://img.shields.io/pypi/v/needto.svg)](https://pypi.org/project/needto)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/needto.svg)](https://pypi.org/project/needto)


Needto have an AI assistant in your command line?

`needto` is an AI-powered assistant for the command line, designed to help you with various tasks such as **finding and running commands**, **answering questions by analyzing command outputs**, and **writing code snippets**. It suggests solutions and makes it easy to apply them in your environment. With `needto`, you can select and run recommended commands safely.

## Installation

To install `needto`, use `pipx`:

```sh
pipx install needto
```

## Configuration

After installation, configure `needto` by running:

```sh
needto config
```

Needto leverages `Groq` to run Meta's Llama3 language models. To get started, you'll need a Groq API key ([Groq](console.groq.com)).

## Usage

### 1. Find and Run a Command

Use `needto do` to find and run commands effortlessly. Simply describe what you need to do, and `needto` will provide a list of CLI commands for you to choose from. You can then edit the command further if necessary before executing it.

**Example:**

```sh
needto do "kill process on port 8000"
```

### 2. Ask Questions

Ask `needto ask` questions about your system. It will help you find answers by suggesting commands to explore and analyzing the outputs of those commands. Note that, in this case, `needto` will prioritize safety and avoid recommending commands that could modify your system state. You always remain in full control of what gets executed on your computer.


**Example:**

```sh
needto ask "how many programs I have installed on my system?"
```

### 3. Write Code

Use `needto write` to generate code snippets. Describe the code you need, and `needto` will provide it along with necessary clarifications.

**Example:**

```sh
needto write "a python script that gets my public IP"
```

## License

`needto` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
