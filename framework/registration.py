import numpy as np
import scipy as sp
import nibabel as nib
import pickle
import os
import argparse
import time
import dipy.viz.regtools as rt
from pylab import *
#from nipype.interfaces.ants import N4BiasFieldCorrection
from dipy.align import VerbosityLevels
from dipy.align.transforms import regtransforms
from dipy.align.imaffine import (AffineMap,
                                 transform_centers_of_mass,
                                 MutualInformationMetric,
                                 AffineRegistration)
from dipy.align.metrics import CCMetric
from dipy.align.imwarp import SymmetricDiffeomorphicRegistration
from dipy.align.reslice import reslice


def dipy_align(static, static_grid2world, moving, moving_grid2world,
               transforms=None, level_iters=None, prealign=None):
    r''' Full rigid registration with Dipy's imaffine module
    Here we implement an extra optimization heuristic: move the geometric
    centers of the images to the origin. Imaffine does not do this by default
    because we want to give the user as much control of the optimization
    process as possible.
    '''
    # Bring the center of the moving image to the origin
    c_moving = tuple(0.5 * np.array(moving.shape, dtype=np.float64))
    c_moving = moving_grid2world.dot(c_moving+(1,))
    correction_moving = np.eye(4, dtype=np.float64)
    correction_moving[:3,3] = -1 * c_moving[:3]
    centered_moving_aff = correction_moving.dot(moving_grid2world)
    # Bring the center of the static image to the origin
    c_static = tuple(0.5 * np.array(static.shape, dtype=np.float64))
    c_static = static_grid2world.dot(c_static+(1,))
    correction_static = np.eye(4, dtype=np.float64)
    correction_static[:3,3] = -1 * c_static[:3]
    centered_static_aff = correction_static.dot(static_grid2world)
    dim = len(static.shape)
    metric = MutualInformationMetric(nbins=32, sampling_proportion=0.3)
    #metric = LocalCCMetric(radius=4)
    #metric.verbosity = VerbosityLevels.DEBUG
    # Registration schedule: center-of-mass then translation, then rigid and then affine
    if prealign is None:
        prealign = 'mass'
    if transforms is None:
        transforms = ['TRANSLATION', 'RIGID', 'AFFINE']
    nlevels = len(transforms)
    if level_iters is None:
        level_iters = [[10000, 1000, 100]] * nlevel
    sol = np.eye(dim + 1)
    for i in range(nlevels):
        transform_name = transforms[i]
        affr = AffineRegistration(metric=metric, level_iters=level_iters[i])
        affr.verbosity = VerbosityLevels.DEBUG
        transform = regtransforms[(transform_name, dim)]
        print('Optimizing: %s'%(transform_name,))
        x0 = None
        sol = affr.optimize(static, moving, transform, x0,
                              centered_static_aff, centered_moving_aff, starting_affine = prealign)
        prealign = sol.affine.copy()
    # Now bring the geometric centers back to their original location
    fixed = np.linalg.inv(correction_moving).dot(sol.affine.dot(correction_static))
    sol.set_affine(fixed)
    sol.domain_grid2world = static_grid2world
    sol.codomain_grid2world = moving_grid2world
    return sol


##----------------------------------------------------------------------------------
##----------------------------------------------------------------------------------

base_dir    = '/home/dalmau/opt/imagenes/data_NeoBrainS12/'
neo_subject = '30wCoronal/example1/'
results_dir = '/home/dalmau/opt/segmentation/framework/registration_output/example1_30wCoronal/'
atlas_index = 0
atlas_label = '28w'

# Step 1.1 - Intensity inhomogeneity correction (currently done with 3D Slicer Version 3.6.3)

#t1FileName = base_dir + 'trainingDataNeoBrainS12/'+neo_subject+'T1.nii.gz'
#t2FileName = base_dir + 'trainingDataNeoBrainS12/'+neo_subject+'T2.nii.gz"
#n4 = N4BiasFieldCorrection()
#n4.inputs.dimension = 3
#n4.inputs.input_image = t1FileName
#t1FileName = t1FileName[0:(t1FileName.index(".nii"))] + "_1-1.nii.gz"
#n4.inputs.output_image = t1FileName
#n4.cmdline
#n4.run()
#n4_2 = N4BiasFieldCorrection()
#n4_2.inputs.dimension = 3
#n4_2.inputs.input_image = t2FileName
#t2FileName = t2FileName[0:(t2FileName.index(".nii"))] + "_1-1.nii.gz"
#n4_2.inputs.output_image = t2FileName
#n4_2.cmdline
#n4_2.run()

#    1.2.1 - Rigid Registration of T1 subject image to T2 subject image
#    ---------------------------------------------------------------------------------------------

t2CurrentSubjectName = base_dir + 'trainingDataNeoBrainS12/'+neo_subject+'T2_1-1.nii.gz'
t1CurrentSubjectName = base_dir + 'trainingDataNeoBrainS12/'+neo_subject+'T1_1-1.nii.gz'

t2CurrentSubject = nib.load(t2CurrentSubjectName)
t1CurrentSubject = nib.load(t1CurrentSubjectName)

t2CurrentSubject_data = t2CurrentSubject.get_data()
t1CurrentSubject_data = t1CurrentSubject.get_data()

t2CSAffine = t2CurrentSubject.get_affine()
t1CSAffine = t1CurrentSubject.get_affine()


start_time = time.time()

scale = np.eye(4)
rigidTransformName = t2CurrentSubjectName[0:(t2CurrentSubjectName.index("/T2"))] +"/T1_towards_T2_rigid.p"

if os.path.isfile(rigidTransformName) :
   rigidTransform = pickle.load(open(rigidTransformName,'r'))
else :
   transforms = ["RIGID","AFFINE"]
   level_iters = [[10000, 1000, 100], [100]]
   rigidTransform = dipy_align(t2CurrentSubject_data,t2CSAffine,
      t1CurrentSubject_data,t1CSAffine,
      transforms = transforms, level_iters = level_iters, prealign=scale)
   pickle.dump(rigidTransform,open(rigidTransformName,'w'))


print "Rigid register: {} seconds.".format(time.time() - start_time)

t1CurrentSubject_data1 = rigidTransform.transform(t1CurrentSubject_data)
rt.overlay_slices(t2CurrentSubject_data, t1CurrentSubject_data1, slice_type=2, slice_index=25, ltitle='T2 Subject', rtitle='T1 Subject', fname= results_dir + 'T1_to_T2_rigid_coronal_slice25.png')
T1CS = nib.Nifti1Image(t1CurrentSubject_data1,t2CSAffine)
nib.save(T1CS,t2CurrentSubjectName[0:(t2CurrentSubjectName.index("/T2"))]+"/T1_1-2.nii.gz")

del t1CurrentSubject_data1
del T1CS

#    ---------------------------------------------------------------------------------------------


#    1.2.2 - Diffeomorphic Registration of atlases to T2
#    ---------------------------------------------------------------------------------------------

t2CurrentSubjectName    = base_dir + 'trainingDataNeoBrainS12/'+neo_subject+'T2_1-1.nii.gz'
t1CurrentSubjectName    = base_dir + 'trainingDataNeoBrainS12/'+neo_subject+'T1_1-2.nii.gz'
t1TemplateSubjectName   = base_dir + 'NeonatalAtlas2/template_T1.nii.gz'
t2TemplateSubjectName   = base_dir + 'NeonatalAtlas2/template_T2.nii.gz'
MaskTemplateSubjectName = base_dir + 'NeonatalAtlas2/brainmask.nii.gz'
BSTemplateSubjectName   = base_dir + 'NeonatalAtlas2/brainstem.nii.gz'
CeTemplateSubjectName   = base_dir + 'NeonatalAtlas2/cerebellum.nii.gz'
CoTemplateSubjectName   = base_dir + 'NeonatalAtlas2/cortex.nii.gz'
CSFTemplateSubjectName  = base_dir + 'NeonatalAtlas2/csf.nii.gz'
DGMTemplateSubjectName  = base_dir + 'NeonatalAtlas2/dgm.nii.gz'
WMTemplateSubjectName   = base_dir + 'NeonatalAtlas2/wm.nii.gz'

t2CurrentSubject    = nib.load(t2CurrentSubjectName)
t1CurrentSubject    = nib.load(t1CurrentSubjectName)
t1TemplateSubject   = nib.load(t1TemplateSubjectName)
t2TemplateSubject   = nib.load(t2TemplateSubjectName)
MaskTemplateSubject = nib.load(MaskTemplateSubjectName)
BSTemplateSubject   = nib.load(BSTemplateSubjectName)
CeTemplateSubject   = nib.load(CeTemplateSubjectName)
CoTemplateSubject   = nib.load(CoTemplateSubjectName)
CSFTemplateSubject  = nib.load(CSFTemplateSubjectName)
DGMTemplateSubject  = nib.load(DGMTemplateSubjectName)
WMTemplateSubject   = nib.load(WMTemplateSubjectName)

t2CurrentSubject_data    = t2CurrentSubject.get_data()
t1CurrentSubject_data    = t1CurrentSubject.get_data()
t1TemplateSubject_data   = t1TemplateSubject.get_data()[:,:,:,atlas_index]
t2TemplateSubject_data   = t2TemplateSubject.get_data()[:,:,:,atlas_index]
MaskTemplateSubject_data = MaskTemplateSubject.get_data()[:,:,:,atlas_index]
BSTemplateSubject_data   = BSTemplateSubject.get_data()[:,:,:,atlas_index]
CeTemplateSubject_data   = CeTemplateSubject.get_data()[:,:,:,atlas_index]
CoTemplateSubject_data   = CoTemplateSubject.get_data()[:,:,:,atlas_index]
CSFTemplateSubject_data  = CSFTemplateSubject.get_data()[:,:,:,atlas_index]
DGMTemplateSubject_data  = DGMTemplateSubject.get_data()[:,:,:,atlas_index]
WMTemplateSubject_data   = WMTemplateSubject.get_data()[:,:,:,atlas_index]

t2CSAffine   = t2CurrentSubject.get_affine()
t1CSAffine   = t1CurrentSubject.get_affine()
t1TSAffine   = t1TemplateSubject.get_affine()
t2TSAffine   = t2TemplateSubject.get_affine()
MaskTSAffine = MaskTemplateSubject.get_affine()
BSTSAffine   = BSTemplateSubject.get_affine()
CeTSAffine   = CeTemplateSubject.get_affine()
CoTSAffine   = CoTemplateSubject.get_affine()
CSFTSAffine  = CSFTemplateSubject.get_affine()
DGMTSAffine  = DGMTemplateSubject.get_affine()
WMTSAffine   = WMTemplateSubject.get_affine()

zoomsT2CS  = t2CurrentSubject.get_header().get_zooms()[:3]
zoomsT2TS  = t2TemplateSubject.get_header().get_zooms()[:3]


start_time = time.time()

scale = np.eye(4)
denom     = t2CurrentSubject_data.shape[0]*zoomsT2CS[0]
denom     = denom*t2CurrentSubject_data.shape[1]*zoomsT2CS[1]
denom     = denom*t2CurrentSubject_data.shape[2]*zoomsT2CS[2]
nume      = t2TemplateSubject_data.shape[0]*zoomsT2TS[0]
nume      = nume*t2TemplateSubject_data.shape[1]*zoomsT2TS[1]
nume      = nume*t2TemplateSubject_data.shape[2]*zoomsT2TS[2]
iso_scale = (float(nume)/float(denom))**(1.0/3)
scale[:3,:3] *= iso_scale
rigidTransformName = t2CurrentSubjectName[0:(t2CurrentSubjectName.index("/T2"))] + "/atlas" + atlas_label+ "_towards_neo_rigid.p"

if os.path.isfile(rigidTransformName) :
   rigidTransform = pickle.load(open(rigidTransformName,'r'))
else :
   transforms = ["RIGID","AFFINE"]
   level_iters = [[10000, 1000, 100], [100]]
   rigidTransform = dipy_align(t2CurrentSubject_data,t2CSAffine,
      t2TemplateSubject_data,t2TSAffine,
      transforms = transforms, level_iters = level_iters, prealign=None) #scale)
   pickle.dump(rigidTransform,open(rigidTransformName,'w'))


print "Rigid register (atlas): {} seconds.".format(time.time() - start_time)

t2TemplateSubject_data1 = rigidTransform.transform(t2TemplateSubject_data)
rt.overlay_slices(t2CurrentSubject_data, t2TemplateSubject_data1, slice_type=2, slice_index=25, ltitle='T2 Subject', rtitle='T2 Template', fname= results_dir + 'A'+atlas_label+'_T2_to_neo_rigid_reg_coronal_slice25.png')


start_time = time.time()

diff_map_name = t2CurrentSubjectName[0:(t2CurrentSubjectName.index("/T2"))] + "/atlas" + atlas_label + "_towards_neo_diff.p"

if os.path.isfile(diff_map_name):
   diff_map = pickle.load(open(diff_map_name,'r'))
else:
   metric = CCMetric(3)
   sdr = SymmetricDiffeomorphicRegistration(metric)
   # apply diffeomorphic registration
   diff_map = sdr.optimize(t2CurrentSubject_data, t2TemplateSubject_data, 
         t2CSAffine, t2TSAffine, prealign=rigidTransform.affine)
   pickle.dump(diff_map, open(diff_map_name, 'w'))


print "Diffeomorphic register (atlas): {} seconds.".format(time.time() - start_time)

t2TemplateSubject_data2   = diff_map.transform(t2TemplateSubject_data)
#   align the rest of the atlas using the same diffeomorphic map
t1TemplateSubject_data2   = diff_map.transform(t1TemplateSubject_data)
MaskTemplateSubject_data2 = diff_map.transform(MaskTemplateSubject_data,'nearest')
BSTemplateSubject_data2   = diff_map.transform(BSTemplateSubject_data,'nearest')
CeTemplateSubject_data2   = diff_map.transform(CeTemplateSubject_data,'nearest')
CoTemplateSubject_data2   = diff_map.transform(CoTemplateSubject_data,'nearest')
CSFTemplateSubject_data2  = diff_map.transform(CSFTemplateSubject_data,'nearest')
DGMTemplateSubject_data2  = diff_map.transform(DGMTemplateSubject_data,'nearest')
WMTemplateSubject_data2   = diff_map.transform(WMTemplateSubject_data,'nearest')

rt.overlay_slices(t2CurrentSubject_data, t2TemplateSubject_data2, slice_type=2, slice_index=25, ltitle='T2 Subject', rtitle='T2 Template', fname= results_dir + 'A'+atlas_label+'_T2_to_neo_diff_reg_coronal_slice25.png')
rt.overlay_slices(t2CurrentSubject_data, t1TemplateSubject_data2, slice_type=2, slice_index=25, ltitle='T2 Subject', rtitle='T1 Template', fname= results_dir + 'A'+atlas_label+'_T1_to_neo_diff_reg_coronal_slice25.png')
rt.overlay_slices(t2CurrentSubject_data, MaskTemplateSubject_data2, slice_type=2, slice_index=25, ltitle='T2 Subject', rtitle='Mask Template', fname= results_dir + 'A'+atlas_label+'_Mask_to_neo_diff_reg_coronal_slice25.png')
rt.overlay_slices(t2CurrentSubject_data, CSFTemplateSubject_data2, slice_type=2, slice_index=25, ltitle='T2 Subject', rtitle='CSF Template', fname= results_dir + 'A'+atlas_label+'_CSF_to_neo_diff_reg_coronal_slice25.png')
rt.overlay_slices(t2CurrentSubject_data, DGMTemplateSubject_data2, slice_type=2, slice_index=25, ltitle='T2 Subject', rtitle='DGM Template', fname= results_dir + 'A'+atlas_label+'_DGM_to_neo_diff_reg_coronal_slice25.png')
rt.overlay_slices(t2CurrentSubject_data, WMTemplateSubject_data2, slice_type=2, slice_index=25, ltitle='T2 Subject', rtitle='WM Template', fname= results_dir + 'A'+atlas_label+'_WM_to_neo_diff_reg_coronal_slice25.png')

A_T1   = nib.Nifti1Image(t1TemplateSubject_data2,t2CSAffine)
A_T2   = nib.Nifti1Image(t2TemplateSubject_data2,t2CSAffine)
A_Mask = nib.Nifti1Image(MaskTemplateSubject_data2,t2CSAffine)
A_BS   = nib.Nifti1Image(BSTemplateSubject_data2,t2CSAffine)
A_Ce   = nib.Nifti1Image(CeTemplateSubject_data2,t2CSAffine)
A_Co   = nib.Nifti1Image(CoTemplateSubject_data2,t2CSAffine)
A_CSF  = nib.Nifti1Image(CSFTemplateSubject_data2,t2CSAffine)
A_DGM  = nib.Nifti1Image(DGMTemplateSubject_data2,t2CSAffine)
A_WM   = nib.Nifti1Image(WMTemplateSubject_data2,t2CSAffine)

nib.save(A_T1,t2CurrentSubjectName[0:(t2CurrentSubjectName.index("/T2"))]+"/A"+atlas_label+"_T1.nii.gz")
nib.save(A_T2,t2CurrentSubjectName[0:(t2CurrentSubjectName.index("/T2"))]+"/A"+atlas_label+"_T2.nii.gz")
nib.save(A_Mask,t2CurrentSubjectName[0:(t2CurrentSubjectName.index("/T2"))]+"/A"+atlas_label+"_Mask.nii.gz")
nib.save(A_BS,t2CurrentSubjectName[0:(t2CurrentSubjectName.index("/T2"))]+"/A"+atlas_label+"_BS.nii.gz")
nib.save(A_Ce,t2CurrentSubjectName[0:(t2CurrentSubjectName.index("/T2"))]+"/A"+atlas_label+"_Ce.nii.gz")
nib.save(A_Co,t2CurrentSubjectName[0:(t2CurrentSubjectName.index("/T2"))]+"/A"+atlas_label+"_Co.nii.gz")
nib.save(A_CSF,t2CurrentSubjectName[0:(t2CurrentSubjectName.index("/T2"))]+"/A"+atlas_label+"_CSF.nii.gz")
nib.save(A_DGM,t2CurrentSubjectName[0:(t2CurrentSubjectName.index("/T2"))]+"/A"+atlas_label+"_DGM.nii.gz")
nib.save(A_WM,t2CurrentSubjectName[0:(t2CurrentSubjectName.index("/T2"))]+"/A"+atlas_label+"_WM.nii.gz")


#    ---------------------------------------------------------------------------------------------


