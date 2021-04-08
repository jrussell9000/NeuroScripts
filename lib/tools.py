# UTILITY FUNCTIONS #
import os
import shutil

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


def scan2bidsmode(modstring):
    scan2bidsmode_dict = {
        "MPRAGE": "T1w",
        "BRAVO": "T1w",
        "AxT2FLAIR": "T2w",
        "NODDI": "dwi",
        "Ax_DTI": "dwi",
        "AxDTI": "dwi",
        "EPI_": "bold",
        "Fieldmap_EPI": "rawfmap",
        "Fieldmap_DTI": "rawfmap",
        "WATER_Fieldmap": "magnitude",
        "FieldMap_Fieldmap_3D": "fieldmap"
    }
    returnkey = "nomatch"
    for key in scan2bidsmode_dict.keys():
        if key in modstring:
            returnkey = scan2bidsmode_dict[key]
    return(returnkey)


def scan2bidsdir(typestring):
    scan2bidsdir_dict = {
        "MPRAGE": "anat",
        "BRAVO": "anat",
        "AxT2FLAIR": "anat",
        "NODDI": "dwi",
        "Ax_DTI": "dwi",
        "EPI": "func",
        "Fieldmap_EPI": "fmap",
        "Fieldmap_DTI": "fmap",
        "WATER_Fieldmap": "fmap",
        "FieldMap_Fieldmap_3D": "fmap"
    }
    returnkey = "nomatch"
    for key in scan2bidsdir_dict.keys():
        if key in typestring:
            returnkey = scan2bidsdir_dict[key]
    return(returnkey)




def progress_percentage(perc, width=None):
    # This will only work for python 3.3+ due to use of
    # os.get_terminal_size the print function etc.

    FULL_BLOCK = '█'
    # this is a gradient of incompleteness
    INCOMPLETE_BLOCK_GRAD = ['░', '▒', '▓']

    assert(isinstance(perc, float))
    assert(0. <= perc <= 100.)
    # if width unset use full terminal
    if width is None:
        width = os.get_terminal_size().columns
    # progress bar is block_widget separator perc_widget : ####### 30%
    max_perc_widget = '[100.00%]' # 100% is max
    separator = ' '
    blocks_widget_width = width - len(separator) - len(max_perc_widget)
    assert(blocks_widget_width >= 10) # not very meaningful if not
    perc_per_block = 100.0/blocks_widget_width
    # epsilon is the sensitivity of rendering a gradient block
    epsilon = 1e-6
    # number of blocks that should be represented as complete
    full_blocks = int((perc + epsilon)/perc_per_block)
    # the rest are "incomplete"
    empty_blocks = blocks_widget_width - full_blocks

    # build blocks widget
    blocks_widget = ([FULL_BLOCK] * full_blocks)
    blocks_widget.extend([INCOMPLETE_BLOCK_GRAD[0]] * empty_blocks)
    # marginal case - remainder due to how granular our blocks are
    remainder = perc - full_blocks*perc_per_block
    # epsilon needed for rounding errors (check would be != 0.)
    # based on reminder modify first empty block shading
    # depending on remainder
    if remainder > epsilon:
        grad_index = int((len(INCOMPLETE_BLOCK_GRAD) * remainder)/perc_per_block)
        blocks_widget[full_blocks] = INCOMPLETE_BLOCK_GRAD[grad_index]

    # build perc widget
    str_perc = '%.2f' % perc
    # -1 because the percentage sign is not included
    perc_widget = '[%s%%]' % str_perc.ljust(len(max_perc_widget) - 3)

    # form progressbar
    progress_bar = '%s%s%s' % (''.join(blocks_widget), separator, perc_widget)
    # return progressbar as string
    return ''.join(progress_bar)


def copy_progress(copied, total):
    print('\r' + progress_percentage(100*copied/total, width=30), end='')

def copyfileobj(fsrc, fdst, callback, total, length=16*1024):
    copied = 0
    while True:
        buf = fsrc.read(length)
        if not buf:
            break
        fdst.write(buf)
        copied += len(buf)
        callback(copied, total=total)

def copyfile(src, dst, *, follow_symlinks=True):
    """Copy data from src to dst.

    If follow_symlinks is not set and src is a symbolic link, a new
    symlink will be created instead of copying the file it points to.

    """
    if shutil._samefile(src, dst):
        raise shutil.SameFileError("{!r} and {!r} are the same file".format(src, dst))

    for fn in [src, dst]:
        try:
            st = os.stat(fn)
        except OSError:
            # File most likely does not exist
            pass
        else:
            # XXX What about other special files? (sockets, devices...)
            if shutil.stat.S_ISFIFO(st.st_mode):
                raise shutil.SpecialFileError("`%s` is a named pipe" % fn)

    if not follow_symlinks and os.path.islink(src):
        os.symlink(os.readlink(src), dst)
    else:
        size = os.stat(src).st_size
        with open(src, 'rb') as fsrc:
            with open(dst, 'wb') as fdst:
                copyfileobj(fsrc, fdst, callback=copy_progress, total=size)
    return dst


def copy_with_progress(src, dst, *, follow_symlinks=True):
    if os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))
    copyfile(src, dst, follow_symlinks=follow_symlinks)
    shutil.copymode(src, dst)
    return dst

def manuallyReviewDWI(subject_id, input_dwi, manual_corr_dir, output_file):
    if os.path.exists(manual_corr_dir):
        shutil.rmtree(manual_corr_dir)

    os.mkdir(manual_corr_dir)

    #First split the DWIs into individual volumes
    os.system('fslsplit ' + input_dwi + ' ' + manual_corr_dir + '/img_ -t')

    for nii in glob(manual_corr_dir + '*.nii*'):
        basename = nii.split('/')[len(nii.split('/'))-1]
        slice = basename.split('.')[0]
        outputPNG = manual_corr_dir + slice + '.png'
        os.system('slicer ' + nii + ' -L -a ' + outputPNG)

    #Run the manual correction
    png_viewer = PNGViewer(manual_corr_dir, subject_id)
    png_viewer.runPNGViewer()

    try:
        input('Please press enter after reviewing DWIs...')
    except SyntaxError:
        pass

    png_viewer.cleanupURL()
    os.system('mv ~/Downloads/Unknown* ' + output_file)
    shutil.rmtree(manual_corr_dir)