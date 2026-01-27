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
