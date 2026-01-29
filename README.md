# Python Package Template
This project is meant to serve as a template and tutorial for setting up new python projects.
It is an *opinionated* tutorial, in so far as I have chosen specific implementations where other options may be available (and more common).
In this documentation I'll do my best to justify these choices and provide some alternate options, but it is important to remember that in python there usually isn't one correct way to do things. 
The following sections explain how to use this package, what choices were made, and how they work, so that you will better know how to modify these choices when you are writing your own package.

# Package Setup and Installation

To install this package from the source installation, it is recommended that you first be working in a `conda` environment or `virtualenv`, and I'll assume the former is in use.
This package can then be installed with `pip install .` or `pip install -e .` if you wish to install in developer mode, where changes you make propagate automatically rather than requiring re-installation. 

<details>
  <summary> <b> Opinionated choice #1</b> </summary>

  This is actually the first opinionated choice made, because this combination of `pip` and `conda` is by no means the only way to handle package setup and installation, and probably isn't the best.
  It is, however, very standard in the LVK, and it is the system I am most familiar with, so we'll proceed from there.
  If you're interested in branching out, see [here](https://dublog.net/blog/so-many-python-package-managers/) for some of the options circa 2024.
  Personally, I am interested in trying out `uv`, but I decided to stick with what I know for the purposes of this tutorial. 
</details>

## The `pyproject.toml`
This file is the core configuration file we'll be working with for package setup. 
In the past, there were a bunch of different files that interacted in strange ways in order to achieve the same purpose, but this was bad, so as of [2020](https://peps.python.org/pep-0621/) the `pyproject.toml` is the correct standard.
We'll go through this section by section to explain what's going on.


### `build-system`
The first section of the `pyproject.toml` is this:
```toml
[build-system]
requires = [
    "setuptools>=42",
    "setuptools_scm[toml]>=3.4.3",
    "wheel",
]
build-backend = "setuptools.build_meta"
```
Now, we're off to an inauspicious start because, frankly, this is not something I actually think about at all and don't have a good explanation of what's happening here other than:
- `setuptools` will be used to build the package
- `setuptools_scm` will handle version control, more on that later
- `wheel` builds `wheels` which are a kind of bundled version of a package that helps with installation

The `build-backend` sets the build backend, I guess.
To be altogether honest, I have been copying this around for years and it Just Works&trade;, so there you have it. 

### `tool.setuptools.packages.find`

Next we have:
```toml
[tool.setuptools.packages.find]
where = ["src"] 
namespaces = true
```
This section is important because it is what tells setuptools where your source code actually lives.
The construction here is that there is a source directory (`src`), and the source code lives within it under the package namespace `my_python_package`. 

An alternate way to set this up looks like this:
```toml
[tool.setuptools.packages.find]
where = ["src"] 
namespaces = false
include = ["my_python_package"]
```
Which will only install `my_python_package`, instead of searching on its own.
This is useful if you have multiple directories in `src` and do not want them all built, but note that if you take this option then you will need to change the `include` bit to your package name as appropriate. 

### `tool.setuptools_scm`

Next is a one liner:
```toml
[tool.setuptools_scm]
write_to = "src/my_python_package/_version.py"
```
`setuptools_scm` handles the version control automatically base on `git` tags, so we just need to point it to where the packages version file will get written.
Substitute `my_python_package` for your own package name, but otherwise not much to do here. 

### `tool.setuptools.dynamic`

This is another rote section to copy around.
Just remember to swap in the correct package name!
This section is basically just pointing setuptools to the place where the version file will live, and telling it that this will be resolved dynamically. 

```toml
[tool.setuptools.dynamic]
version = {attr = "my_python_package._version.__version__"}
```

### `project`

This block is the meat of the description, and has the most elements that you need to fill out with your own details.

```toml
name = "my-python-package"
authors = [
  { name="Rhiannon Udall", email="rhiannon.udall@ligo.org" },
]
description = "A template for how to build your own python package, with opinionated choices for configuration"
readme = "README.md"
requires-python = ">=3.10"
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Intended Audience :: Gravitational Wave Scientists",
    "Development Status :: 1 - Initial Setup"
]
dynamic = ["version"]
dependencies = [
    "loguru",
    "typer"
]
```

Most of this stuff is pretty straightforward: package name and authors, python version, license, etc.
Keep the `dynamic` bit because that is used by `setuptools_scm` when setting the version.

One thing worth noting here are the `dependencies`.
These are the packages which need to be downloaded for your project, and by putting them here they will automatically be downloaded with your package.
This is, and I cannot emphasize this enough, infinitely better than defining your package's dependencies by the specific combination of things that makes your `conda` environment work.
**PLEASE PLEASE PLEASE I BEG OF YOU KEEP THIS LIST OF DEPENDENCIES UPDATED PROPERLY.**
The dependencies listed here are some of my opinionated suggestions, and will be explained in detail in later sections. 

### `project.scripts`

Now we get to an interesting section you will become familiar with.

```toml
[project.scripts]
template_python_project_hello = "my_python_package:cli_hello"
```

We'll go into this in more detail in [Writing Code and Client Scripts](#Writing_Code_and_Client_Scripts), 
but this section is where you add new client scripts once they have been written.
Notice the formatting: `template_python_project_hello` is the name of the script (i.e. if you install this package and type that, it will run), then on the right side of the equals is the path to the function, `"module:function"`. 
We'll see later how to set things up so this is properly exposed to access the script. 

### `project.urls`

This one is pretty much what you'd expect: important URLs  to add.
`homepage` and `issues` are default suggestions, see [here](https://packaging.python.org/en/latest/specifications/well-known-project-urls/#well-known-labels) for a list of labels that will automatically be recognized. 

```toml
[project.urls]
homepage = "https://github.com/Rhiannon-Udall/python-package-template"
issues = "https://github.com/Rhiannon-Udall/python-package-template/issues"
```

## Deployment

If you wish to deploy your package, such that others can easily access it (rather than having to clone your repository), you will want to put it on `pypi`.
The first step for this is to build a release version.
That requires, in turn, creating a release version of your git repository. 

As previously mentioned, `setuptools_scm` uses `git` tags to automaticallly generate the version of the package.
The basic system is that it will look at the most recent `git tag` and use this as the base version.
If the code has been modified since that tag, it will then add a `dev...` hash to the version name, to note that this is a development version under some git hash.
When you're ready to make a release version, you make a new [git tag](https://git-scm.com/book/en/v2/Git-Basics-Tagging).
The simple command will look something like this: `git tag -a v0.2.0 -m "Release version 0.2.0"` where `-a` is the version name you are making (make sure to follow [pep 440](https://peps.python.org/pep-0440/) if you want to upload to pypi) and `-m` is a message to apply to the git tag.

Once you have a tagged version, you need to follow [the pypi instructions for building and deploying your project](https://packaging.python.org/en/latest/tutorials/packaging-projects/).
To be completely honest, I reference these instructions every time I am doing `pypi` upload, so I would generally suggest you do the same.
For completeness, however, here are the basic steps.

1) Install/upgrade `twine` and `build`
2) Build your project by running `python3 -m build` in the project directory
3) Upload your project by running `python3 -m twine upload dist/*-{version}*`, where `{version}` is the version you build (e.g. `v0.2.0`). 

This will prompt you for your API token, for which you will need to create an account, see information [here](https://pypi.org/help/#apitoken).

# Formatting and Pre-commit

Readable code provides a number of important benefits:

- It makes it much easier for others to work with your code (which you want! Other people using your stuff makes your work intrinsically more important and valuable!)
- It makes it easier for *you* to work on your code
- It will save you from literal headaches (I am only half-joking, I find very messy code physically unpleasant to read)

Some aspects of keeping code readable require you to be diligent about how you write your code, and as such have a non-trivial time investment (which you should still make).
These will be covered in a different tutorial.

One important step in keeping code clean, however, requires 0 time investment on your part, and that step is setting up a code formatter.
These are packages which will run through your code and standardize the way it looks according to various rules, fixing stuff like indentation as they go. 
For this package, the one I am using is `ruff`.

<details>
  <summary> <b>Opinionated choice #2</b> </summary>

  `ruff` is another case of a choice that is actively being made.
  There are many possible formatters, and the most popular one is probably `black`, which I used for a while.
  However, `ruff` is easier to setup and *way* faster, so I have recently come to prefer it.
  If you want to switch to `black` you can change it in `.pre-commit-config.yaml`, which we'll get to in a bit. 
  There are also plenty of other options that you can look into [here](https://github.com/life4/awesome-python-code-formatters). 

</details>

Running `ruff` is very simple, with `ruff check` being enough to tell you if your code passes, and `ruff check --fix` doing that while also actively fixing any issues it can. 
However, to make this even easier, we can use `pre-commit`.
This is already configured to use `ruff` in this template: 

```yaml
repos:
- repo: https://github.com/astral-sh/ruff-pre-commit
  # Ruff version.
  rev: v0.11.11
  hooks:
    # Run the linter.
    - id: ruff-check
      types_or: [ python, pyi ]
      args: [ --fix ]
    # Run the formatter.
    - id: ruff-format
      types_or: [ python, pyi ]
```

This runs both `ruff check` and `ruff format` on the appropriate files. 
To use `pre-commit` directly on all files, you can do `pre-commit run --all`, and this will run the commands on all files as requested.
Even better, though is what is implied by the name *pre*-commit: you can configure it to run whenever you make a git commit, so you don't forget.
To do so, all you need to do is run `pre-commit install` once in the repository, and from then on your code will be formatted with each commit.
If corrections are needed, the commit will fail, and you just `git add .` again to catch the changes and then commit as normal.

# Writing Code and Client Scripts

You presumably already know how to write python code, so we will not go into great detail with that here.
However, there are a couple neat tricks worth knowing about that this package implements/demonstrates.

## Logging

It is often the case that you want logging messages to tell you what your program is doing.
This can be achieved in multiple ways, from `print` statements to the built in python `logging`, but here I will suggest the use of `loguru`.

<details> 
  <summary><b>Opinionated Choice #3</b></summary>

  As mentioned, there are lots of different ways to get messages into `stdout`. 
  `print` is the simplest -- and make no mistake, I make plenty of use of it -- but for writing a package it's also probably the worst.
  The main reasons for this are that a) it you can't control where output goes (it's straight to `stdout`) and  b) you can't set different levels (i.e. differentiate error messages from normal information). 
  There are lots of ways to make this better, and python has the built-in [`logging`](https://docs.python.org/3/library/logging.html). 
  However, configuration of the built-in `logging` is kind of a pain.
  `loguru`, by contrast, is very easy to use and configure, and looks very clean in the process, so that's what I prefer. 

</details>

The actual logging infrastructure gets implemented in `logging.py`:

```python
"""Implements logging for this package. Code copied (with slight modification) from `nrsur_catalog`"""

import logging
import sys
import warnings

from loguru import logger

logger.remove(0)

logger_format = "|<blue>MY-PYTHON-PACKAGE</blue>|{time:DD/MM HH:mm:ss}|{level}| <green>{message}</green> "

logger.add(
    sys.stderr,
    format=logger_format,
    colorize=True,
    level="WARNING",
)
logger.add(sys.stdout, format=logger_format, colorize=True, level="INFO")

warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning)
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
```

There's a bit here which I won't try to explain, but the important thing is to note the `logger` object.
If you feed your messages into that by calling e.g. `logger.info`, `logger.warning`, and `logger.error`, you're able to control your outputs and get them prettily printed. 
We'll see an application of this in the code below. 

## Typer

Another thing you'll commonly want to do is write command line scripts.
These are scripts that you call from terminal in order to do something.
Usually, you'll want to put in some inputs at the time you call it, in order to customize the behavior, and for this you'll need a parser.
These are wrappers around a script which take command line inputs, then make them variables in your python code which can be operated upon.
The simplest way to do this is to call `sys.argv` and hope that the user a) knew what arguments to put in and b) knew what the correct order to put them in was.
**Please do not take this approach, as it makes code extremely difficult to read and use**.
Instead, various modules allow you to build more advanced parsers, which provide the user with more information and make your code more readable. 

The most common parser to use for this purpose is the built-in [`argparse`](https://docs.python.org/3/library/argparse.html).
I'm going to suggest a different route, however, and instead introduce `typer`, which helps you avoid having to write a parser at all. 

<details>
  <summary><b>Opinionated Suggestion #4</b></summary>

  As noted, the most common way to do argument parsing (certainly used in >90% of cases in the LVK collaboration) is `argparse`. 
  I've used `argparse` quite extensively, and indeed have written [some very involved code manipulating it](https://git.ligo.org/cbc/projects/cbcflow/-/blob/main/src/cbcflow/core/parser.py?ref_type=heads), and that experience is what makes me suggest that you should use something else.
  `argparse` does what you expect it to, but it has a number of problems: it doesn't play well with linters, reading and understanding the parser code is very laborious, and it can have weird edge cases that are hard to predict.
  Also, it does nothing to improve the quality of the outputs, which in turn makes it harder to use scripts written with it (god forbid you try to figure out the appropriate flag to pass to `bilby_pipe`).

  By contrast, `typer` (and `click`, which `typer` is really just a wrapper for), have much more readable code, play well with linters, and produce much cleaner outputs.
  The reason I prefer `typer` over using `click` directly is that `typer` is easier to use, as we shall see, and does a good job bridging the writing of good functions with the writing of the script itself. 

</details>

The example code for setting up a `typer` script is `hello.py`:
```python
"""An example source file for a python project. This includes a function, and the way to call it as a script via Typer"""

import typer

from typing import Annotated

from .logging import logger


def hello(
    name: Annotated[str, typer.Argument(help="The name of the person to say hello to")],
) -> str:
    """Says hello to {name}

    Parameters
    ==========
        name : str
            The name of the person to say hello to

    Returns
    =======
        str
            The message to send (also sent to stdout via the logger)
    """
    message = f"Hello {name}, this is an example python script!"
    logger.info(message)
    return message


def cli_hello():
    typer.run(hello)
```

Here `hello` is a very simple function, but thoroughly documented:

- The input and output types are specified
- Docstrings also explain inputs and outputs, as well as the purpose of the code.
- `typer.Argument` is used to add a help message explaining `name`

You are likely already familiar with most of these points (TODO link to previous tutorials about this), except the bit about `typer`, which I will now explain.

The command `typer.run()` takes in a function, constructs a command line parser from the function signature (that is, the combination of its inputs, outputs, typing, and docstrings), then feeds the user inputs to that parser into the function.
The function name `cli_hello` conveys that this function is a command line (client, hence `cli`) wrapper of `hello`, but this is just a convention and need not be adapted. 
To see what this looks like we can do:
```bash
(better-bilby-pipe-development) [rhiannon.udall@citlogin1 RandomSourceLibraries]$ template_python_project_hello --help
                                                                                                                        
 Usage: template_python_project_hello [OPTIONS] NAME                                                                    
                                                                                                                        
 Says hello to {name}                                                                                                   
                                                                                                                        
 Parameters                                                                                                             
 ==========                                                                                                             
     name : str                                                                                                         
         The name of the person to say hello to                                                                         
                                                                                                                        
 Returns                                                                                                                
 =======                                                                                                                
     str                                                                                                                
         The message to send (also sent to stdout via the logger)                                                       
                                                                                                                        
╭─ Arguments ──────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    name      TEXT  The name of the person to say hello to [required]                                               │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                          │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
```

As you can see, the function has been converted into a command line script.
Note that the information on `name`in the `Arguments` is derived from the annotation we added.
`typer` can also do other cool stuff, for which you should visit [the package documentation](https://typer.tiangolo.com/) if you are interested.

If the script is provided an input it will do what you'd expect:
```bash

(better-bilby-pipe-development) [rhiannon.udall@citlogin1 RandomSourceLibraries]$ template_python_project_hello rhiannon.udall
|MY-PYTHON-PACKAGE|29/01 13:09:38|INFO| Hello rhiannon.udall, this is an example python script! 
```

Now you probably noticed that the script name was not `cli_hello`, but instead `template_python_project_hello`.
Recall that this was what we set in the `pyproject.toml`: `template_python_project_hello = "my_python_package:cli_hello"`.
Now, this assumes that we could do `from my_python_package import cli_hello`, which is not presently true.
To make this accessible, we can import it at the module level by adding it to the `__init__.py`:

```python
from . import hello, logging

from .hello import cli_hello

__all__ = ["hello", "logging", "cli_hello"]
```

Here the `__all__` bit is not necessary for the code to run, but `ruff` will yell at you if you don't add it. 


# Documentation
TODO

# Testing
TODO

