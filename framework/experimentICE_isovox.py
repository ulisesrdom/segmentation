import numpy as np
import scipy as sp
import nibabel as nib
import os
import argparse
import time
import matplotlib.pyplot as plt
from PIL import Image
from pylab import *
from skimage.morphology import ball,opening,closing,dilation,erosion,watershed
from scipy.ndimage.measurements import watershed_ift
from skimage.filters import threshold_otsu
from skimage.restoration import denoise_bilateral
from scipy.stats.stats import pearsonr
from dipy.align.reslice import reslice

# Normalize intensity values to the range [0,scaleVal]
# Input:  data numpy array with the intensity values to normalize and
#         scaleVal value for the normalization.
# Output: data numpy array with the normalized intensity values.
def NormalizeIntensity(data,scaleVal):
   maxVal = data.max()
   minVal = data.min()
   data = (scaleVal/(maxVal-minVal))*(data-minVal)
   return data



base_dir    = '/home/dalmau/opt/imagenes/data_NeoBrainS12/'
neo_subject = '30wCoronal/example2/'
results_dir = '/home/dalmau/opt/segmentation/framework/experimentICE_isovox_output/example2_30wCoronal/true/'
atlas_label = '28w'
iso_voxels = True  # <-- Isotropic voxels or not

# Read subject files
t2CurrentSubjectName  = base_dir + 'trainingDataNeoBrainS12/'+neo_subject+'T2_1-1.nii.gz'
t1CurrentSubjectName  = base_dir + 'trainingDataNeoBrainS12/'+neo_subject+'T1_1-2.nii.gz'
GTName                = base_dir + 'trainingDataNeoBrainS12/'+neo_subject+'manualSegm.nii.gz'
t2CurrentSubject_data = nib.load(t2CurrentSubjectName).get_data()
t1CurrentSubject_data = nib.load(t1CurrentSubjectName).get_data()
GT_data               = nib.load(GTName).get_data()
affineT2CS            = nib.load(t2CurrentSubjectName).get_affine()
zoomsT2CS             = nib.load(t2CurrentSubjectName).get_header().get_zooms()[:3]


# Read priors files
AT1Name    = base_dir + 'trainingDataNeoBrainS12/'+neo_subject+'A'+atlas_label+'_T1.nii.gz'
AT2Name    = base_dir + 'trainingDataNeoBrainS12/'+neo_subject+'A'+atlas_label+'_T2.nii.gz'
AMaskName  = base_dir + 'trainingDataNeoBrainS12/'+neo_subject+'A'+atlas_label+'_Mask.nii.gz'
ABSName    = base_dir + 'trainingDataNeoBrainS12/'+neo_subject+'A'+atlas_label+'_BS.nii.gz'
ACeName    = base_dir + 'trainingDataNeoBrainS12/'+neo_subject+'A'+atlas_label+'_Ce.nii.gz'
ACoName    = base_dir + 'trainingDataNeoBrainS12/'+neo_subject+'A'+atlas_label+'_Co.nii.gz'
ACSFName   = base_dir + 'trainingDataNeoBrainS12/'+neo_subject+'A'+atlas_label+'_CSF.nii.gz'
ADGMName   = base_dir + 'trainingDataNeoBrainS12/'+neo_subject+'A'+atlas_label+'_DGM.nii.gz'
AWMName    = base_dir + 'trainingDataNeoBrainS12/'+neo_subject+'A'+atlas_label+'_WM.nii.gz'
AT1_data   = nib.load(AT1Name).get_data()
AT2_data   = nib.load(AT2Name).get_data()
AMask_data = nib.load(AMaskName).get_data()
ABS_data   = nib.load(ABSName).get_data()
ACe_data   = nib.load(ACeName).get_data()
ACo_data   = nib.load(ACoName).get_data()
ACSF_data  = nib.load(ACSFName).get_data()
ADGM_data  = nib.load(ADGMName).get_data()
AWM_data   = nib.load(AWMName).get_data()


start_time = time.time()

# Step 1.4 - Resampling for isotropic voxels

n_zooms = (zoomsT2CS[0],zoomsT2CS[0],zoomsT2CS[0])
v = n_zooms[0]
if iso_voxels == True :
  t2CurrentSubject_data,affineT2CS = reslice(t2CurrentSubject_data,affineT2CS,zoomsT2CS,n_zooms)
  t1CurrentSubject_data,_          = reslice(t1CurrentSubject_data,affineT2CS,zoomsT2CS,n_zooms)
  AT1_data,_                       = reslice(AT1_data,affineT2CS,zoomsT2CS,n_zooms)
  AT2_data,_                       = reslice(AT2_data,affineT2CS,zoomsT2CS,n_zooms)
  AMask_data,_                     = reslice(AMask_data,affineT2CS,zoomsT2CS,n_zooms)
  ABS_data,_                       = reslice(ABS_data,affineT2CS,zoomsT2CS,n_zooms)
  ACe_data,_                       = reslice(ACe_data,affineT2CS,zoomsT2CS,n_zooms)
  ACo_data,_                       = reslice(ACo_data,affineT2CS,zoomsT2CS,n_zooms)
  ACSF_data,_                      = reslice(ACSF_data,affineT2CS,zoomsT2CS,n_zooms)
  ADGM_data,_                      = reslice(ADGM_data,affineT2CS,zoomsT2CS,n_zooms)
  AWM_data,_                       = reslice(AWM_data,affineT2CS,zoomsT2CS,n_zooms)


# Step 1.5 - Anisotropic diffusion filter

scaleValue = 1.0
t2CurrentSubject_data = denoise_bilateral(NormalizeIntensity(t2CurrentSubject_data,scaleValue))
t1CurrentSubject_data = denoise_bilateral(NormalizeIntensity(t1CurrentSubject_data,scaleValue))


# Normalize the rest of the volume intensity values to [0,255]
scaleValue            = 255.0
t2CurrentSubject_data = NormalizeIntensity(t2CurrentSubject_data,scaleValue)
t1CurrentSubject_data = NormalizeIntensity(t1CurrentSubject_data,scaleValue)
AT1_data              = NormalizeIntensity(AT1_data,scaleValue)
AT2_data              = NormalizeIntensity(AT2_data,scaleValue)
AMask_data            = NormalizeIntensity(AMask_data,scaleValue)
ABS_data              = NormalizeIntensity(ABS_data,scaleValue)
ACe_data              = NormalizeIntensity(ACe_data,scaleValue)
ACo_data              = NormalizeIntensity(ACo_data,scaleValue)
ACSF_data             = NormalizeIntensity(ACSF_data,scaleValue)
ADGM_data             = NormalizeIntensity(ADGM_data,scaleValue)
AWM_data              = NormalizeIntensity(AWM_data,scaleValue)

dim1 = t2CurrentSubject_data.shape[0]
dim2 = t2CurrentSubject_data.shape[1]
dim3 = t2CurrentSubject_data.shape[2]


# 2 - Intracranial Cavity Extraction

#   apply atlas head mask
for i in xrange(0,dim1):
  for j in xrange(0,dim2):
   for k in xrange(0,dim3):
      if AMask_data[i,j,k] == 0 :
        t2CurrentSubject_data[i,j,k] = 0

nSlice = int(dim3 / 2)
difSlice = 12

Im = Image.fromarray(np.uint8(t2CurrentSubject_data[:,:,nSlice]))
Im.save(results_dir+'T2_IC.png')
Im = Image.fromarray(np.uint8(t2CurrentSubject_data[:,:,nSlice+difSlice]))
Im.save(results_dir+'T2_IC_p'+str(difSlice)+'.png')
Im = Image.fromarray(np.uint8(t2CurrentSubject_data[:,:,nSlice-difSlice]))
Im.save(results_dir+'T2_IC_m'+str(difSlice)+'.png')

#   define structuring element
struct_elem = ball(4) # <-- should have 9 voxel units of diameter
#   Perform morphologic opening on T2 image
openedT2 = opening(t2CurrentSubject_data,struct_elem)
Im = Image.fromarray(np.uint8(openedT2[:,:,nSlice]))
Im.save(results_dir+'openedT2.png')

#   Obtain morphological gradient of opened T2 image
cross_se = np.array(np.zeros(( 3,3,3 )),dtype=np.uint8) # <-- should have 3 voxel units of diameter
i_mid = int(3/2.0)
for i in xrange(0,3):
   cross_se[i,i_mid,i_mid] = 1
   cross_se[i_mid,i,i_mid] = 1
   cross_se[i_mid,i_mid,i] = 1


dilationOT2 = dilation(openedT2,cross_se)
erosionOT2  = erosion(openedT2,cross_se)
del openedT2
gradientOT2 = dilationOT2 - erosionOT2
Im = Image.fromarray(np.uint8(gradientOT2[:,:,nSlice]))
Im.save(results_dir+'GradientMorp_NoNorm.png')
del dilationOT2
del erosionOT2
gradientOT2 = NormalizeIntensity(gradientOT2,255.0)
Im = Image.fromarray(np.uint8(gradientOT2[:,:,nSlice]))
Im.save(results_dir+'GradientMorp_Norm.png')

#   Obtain segmentation function (sum of increasing scale dilations)
dilGradOT2   = dilation(gradientOT2,ball(0))
for i in xrange(1,5):
   dilGradOT2   = dilation(gradientOT2,ball(i)) + dilGradOT2

segFuncGOT2  = NormalizeIntensity(dilGradOT2,255.0)
Im = Image.fromarray(np.uint8(segFuncGOT2[:,:,nSlice]))
Im.save(results_dir+'seg_func_ICE.png')
del dilGradOT2
del gradientOT2

#   Obtain T2 mask by threshold
#t = threshold_otsu(t2CurrentSubject_data)
#maskT2 = t2CurrentSubject_data >= (t*1.75) # 2.1)
#maskT2 = np.array(maskT2,dtype=float)

#   Obtain gravity center of mask of T2
C = np.zeros(3)
maskT2Count = 0
for x in xrange(0,dim1):
  for y in xrange(0,dim2):
    for z in xrange(0,dim3):
       if t2CurrentSubject_data[x,y,z] > 0 :
          maskT2Count = maskT2Count + 1
          C[0] = C[0] + x
          C[1] = C[1] + y
          C[2] = C[2] + z

C = C / float(maskT2Count)
print "Centroid = {}".format(C)

#   set two class of markers (for marker based watershed segmentation)
markersICE = np.array(np.zeros((dim1,dim2,dim3)),dtype=int)
markersICE[int(C[0]),int(C[1]),int(C[2])] = 2
for i in xrange(1,4):
  markersICE[int(C[0])+i,int(C[1]),int(C[2])] = 2
  markersICE[int(C[0])-i,int(C[1]),int(C[2])] = 2
  markersICE[int(C[0]),int(C[1])+i,int(C[2])] = 2
  markersICE[int(C[0]),int(C[1])-i,int(C[2])] = 2
  markersICE[int(C[0]),int(C[1]),int(C[2])+i] = 2
  markersICE[int(C[0]),int(C[1]),int(C[2])-i] = 2

for y in xrange(0,dim2):
  for z in xrange(0,dim3):
     markersICE[0,y,z] = 1
     markersICE[dim1-1,y,z] = 1

for x in xrange(0,dim1):
  for z in xrange(0,dim3):
     markersICE[x,0,z] = 1
     markersICE[x,dim2-1,z] = 1

for y in xrange(0,dim2):
  for x in xrange(0,dim1):
     markersICE[x,y,0] = 1
     markersICE[x,y,dim3-1] = 1

#   Apply watershed segmentation with markers
segFuncGOT2 = np.array(segFuncGOT2,dtype=int)
ICEMask = watershed(segFuncGOT2,markersICE)
del segFuncGOT2
del markersICE
ICEMask = dilation(ICEMask,ball(1))
#   Apply Inctracranial Cavity Extraction with segmented watershed mask
for x in xrange(0,dim1):
  for y in xrange(0,dim2):
    for z in xrange(0,dim3):
       if ICEMask[x,y,z] == 1 :
          t2CurrentSubject_data[x,y,z] = 0
          t1CurrentSubject_data[x,y,z] = 0

#   show a sample resulting slice

Im = Image.fromarray(np.uint8(ICEMask[:,:,nSlice]*127))
Im.save(results_dir+'ICEMask.png')
Im = Image.fromarray(np.uint8(ICEMask[:,:,nSlice+difSlice]*127))
Im.save(results_dir+'ICEMask_p'+str(difSlice)+'.png')
Im = Image.fromarray(np.uint8(ICEMask[:,:,nSlice-difSlice]*127))
Im.save(results_dir+'ICEMask_m'+str(difSlice)+'.png')
Im = Image.fromarray(np.uint8(t1CurrentSubject_data[:,:,nSlice]))
Im.save(results_dir+'t1CS.png')
Im = Image.fromarray(np.uint8(t1CurrentSubject_data[:,:,nSlice+difSlice]))
Im.save(results_dir+'t1CS_p'+str(difSlice)+'.png')
Im = Image.fromarray(np.uint8(t1CurrentSubject_data[:,:,nSlice-difSlice]))
Im.save(results_dir+'t1CS_m'+str(difSlice)+'.png')
Im = Image.fromarray(np.uint8(t2CurrentSubject_data[:,:,nSlice]))
Im.save(results_dir+'t2CS.png')
Im = Image.fromarray(np.uint8(t2CurrentSubject_data[:,:,nSlice+difSlice]))
Im.save(results_dir+'t2CS_p'+str(difSlice)+'.png')
Im = Image.fromarray(np.uint8(t2CurrentSubject_data[:,:,nSlice-difSlice]))
Im.save(results_dir+'t2CS_m'+str(difSlice)+'.png')


print "Until ICE: {} seconds.".format(time.time() - start_time)


del ICEMask


#   Obtain DICE coefficient for Brain Tissue (Intracranial Cavity Extraction).
#   Ground Truth clases (3D array GT_data):
#      1 - Cortical GM
#      2 - Basal ganglia and Thalami (Subcortical GM)
#      3 - Unmyelinated WM
#      4 - Myelinated WM
#      5 - Brainstem (without myelinated penduncies)
#      6 - Cerebellum
#      7 - Ventricles (lateral, third and fourth, this is ventricular CSF)
#      8 - External CSF (CSF that is not ventricular)

numeBrain   = 0
denSMBrain  = 0
denGTBrain  = 0
#wVoxel   = int(round(float(dim3)/float(GT_data.shape[2])))

for i in xrange(20,dim1-20):
 for j in xrange(20,dim2-20):
  for k in xrange(0,GT_data.shape[2]):
     k1 = int(round(float(dim3*k)/float(GT_data.shape[2])))
     # decide voxel value on third dimension based on voting scheme
     #BrainVotes  = 0
     #segValue = 0
     #for k2 in xrange(0,wVoxel):
     #   ind = k1 + k2
     #   if ind < dim3 :
     #      if SegMap[i,j,ind] > 0 :
     #         BrainVotes = BrainVotes + 1
     #maxVoted = max(BrainVotes,0)
     #if maxVoted == 0 :
     #   segValue = 0
     #else :
     #   segValue = 1
     if t2CurrentSubject_data[i,j,k1] > 0 :
        segValue = 1
     else :
        segValue = 0
     
     if segValue == 1 :
        denSMBrain  = denSMBrain + 1
     if GT_data[i,j,k] > 0 :
        denGTBrain  = denGTBrain + 1
        if segValue == 1 :
           numeBrain   = numeBrain + 1


DICE_Brain  = 2.0*numeBrain  / (denSMBrain  + denGTBrain)

print "DICE BRAIN = {}".format(DICE_Brain)

