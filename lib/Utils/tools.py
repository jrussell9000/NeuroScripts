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


def scan2bidsmode(modstring):
    scan2bidsmode_dict = {
        "MPRAGE": "T1w",
        "BRAVO": "T1w",
        "AxT2FLAIR": "T2w",
        "NODDI": "dwi",
        "Ax_DTI": "dwi",
        "EPI_": "bold",
        "Fieldmap_EPI": "epirawfmap",
        "Fieldmap_DTI": "dwirawfmap",
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