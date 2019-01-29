import os
import pathlib
import shutil
import tarfile
import tempfile

import pydicom

# UTILITY FUNCTIONS #


# Underline strings
def stru(string):
    start = '\033[4m'
    end = '\033[0m'
    ustr = start + string + end
    return(ustr)


# Underline all strings in a print command
def printu(string):
    start = '\033[4m'
    end = '\033[0m'
    ustr = start + string + end
    print(ustr)


