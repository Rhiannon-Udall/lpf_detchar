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



# Formatting and Pre-commit

# Writing Code and Client Scripts

# Documentation
TODO

# Testing
TODO