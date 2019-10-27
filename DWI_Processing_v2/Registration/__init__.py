#%%
import numpy as np
import nibabel as nib
from dipy.align.imwarp import SymmetricDiffeomorphicRegistration
from dipy.align.imwarp import DiffeomorphicMap
from dipy.align.metrics import CCMetric
import os.path
from dipy.viz import regtools

#%%
input_fa = "/scratch/jdrussell3/dipytest/dti_model/dti_FA.nii.gz"

# Per Genc, Smith, et al., 
# 1. Generate a intra-subject FOD template for each subject
# 2. Then create a population template
# 3. 