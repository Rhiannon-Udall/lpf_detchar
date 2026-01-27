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
```
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
```
[tool.setuptools.packages.find]
where = ["src"] 
namespaces = true
```
This section is important because it is what tells setuptools where your source code actually lives.
The construction here is that there is a source directory (`src`), and the source code lives within it under the package namespace `my_python_package`. 
This should work for simple cases, but note that if you want to start adding more directories in `src` without having them built as a package, you need to set `namespaces` to `false`, then add `include = ["my_python_package"]`. 

### `tool.setuptools_scm`

Next is a one liner:
```
[tool.setuptools_scm]
write_to = "src/my_python_package/_version.py"
```
`setuptools_scm` handles the version control automatically, so we just need to point it to where the packages version file will get written.
Substitute `my_python_package` for your own package name, but otherwise not much to do here. 

However, this is a good moment for a digression about how version control works with this setup, so read the collapsed section below when you are ready to make a tagged release version.

<details>
    <summary><b>How to make tagged versions</b></summary>
    `setuptools_scm` uses `git` tags to automaticallly generate the version of the package.
    The basic system is that it will look at the most recent `git tag` and use this as the base version.
    If the code has been modified since that tag, it will then add a `dev...` hash to the version name, to note that this is a development version under some git hash.
    When you're ready to make a release version, you make a new [git tag](https://git-scm.com/book/en/v2/Git-Basics-Tagging).
    The simple command will look something like this: `git tag -a v0.2.0 -m "Release version 0.2.0"` where `-a` is the version name you are making (make sure to follow [pep 440](https://peps.python.org/pep-0440/) if you want to upload to pypi) and `-m` is a message to apply to the git tag. 

</details>



# Formatting and Pre-commit

# Writing Code and Client Scripts

# Documentation
TODO

# Testing
TODO