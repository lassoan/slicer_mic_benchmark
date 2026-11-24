"""Section 3: C++ algorithms (SimpleITK/ITK and VTK) on the CT volumes of config.COMPUTE_CASES.

3a anisotropic diffusion (curvature, gradient)      3b bone label map (threshold, connected components, relabel)
3c label statistics (intensity and shape)           3d histogram (vtkImageAccumulate), image statistics
3e surface: flying edges -> windowed sinc smoothing -> normals
3f surface -> label map (vtkPolyDataToImageStencil -> vtkImageStencilToImage), Dice against 3b
"""

import numpy as np
import SimpleITK as sitk
from vtkmodules.util import numpy_support
from vtkmodules.vtkCommonDataModel import vtkImageData
from vtkmodules.vtkFiltersCore import vtkFlyingEdges3D, vtkMassProperties, vtkPolyDataNormals, vtkWindowedSincPolyDataFilter
from vtkmodules.vtkImagingStatistics import vtkImageAccumulate
from vtkmodules.vtkImagingStencil import vtkImageStencilToImage, vtkPolyDataToImageStencil

from bench import config, harness
from bench.t2_numpy import r

DEFAULT_REPEATS = 3


def to_vtk_image(arr_zyx, img):
    vi = vtkImageData()
    nz, ny, nx = arr_zyx.shape
    vi.SetDimensions(nx, ny, nz)
    vi.SetSpacing(img.GetSpacing())
    vi.SetOrigin(img.GetOrigin())
    vtk_arr = numpy_support.numpy_to_vtk(arr_zyx.ravel(), deep=True)
    vi.GetPointData().SetScalars(vtk_arr)
    return vi


def dice(a, b):
    a = a.astype(bool)
    b = b.astype(bool)
    return 2.0 * np.logical_and(a, b).sum() / (a.sum() + b.sum())


def run(runner, cases=None, tasks=None, threads=1, env="unknown"):
    cases = cases or config.COMPUTE_CASES
    harness.set_library_threads(threads)
    cts = {c: sitk.ReadImage(str(config.NRRD_DIR / f"{c}.nrrd")) for c in cases}
    cts_f = {c: sitk.Cast(img, sitk.sitkFloat32) for c, img in cts.items()}
    for c, img in cts.items():
        if not np.allclose(img.GetDirection(), np.eye(3).ravel()):
            print(f"  note: {c} has non-identity direction (ignored for the VTK image)")

    def want(name):
        return tasks is None or any(name.startswith(t) for t in tasks)

    state = {}

    # --- 3a anisotropic diffusion
    if want("3a"):
        def crop(img, size):
            n = img.GetSize()
            start = [max(0, (k - size) // 2) for k in n]
            return sitk.RegionOfInterest(img, [min(size, k) for k in n], start)
        crops = {c: crop(img, config.DIFFUSION_CROP) for c, img in cts_f.items()}

        def diffusion(filter_cls):
            out = {}
            for c, img in crops.items():
                f = filter_cls()
                # Stable time step for 3D: < min spacing / 2^(N+1); use min spacing / 20
                f.SetTimeStep(min(img.GetSpacing()) / 20.0)
                f.SetConductanceParameter(config.DIFFUSION_CONDUCTANCE)
                f.SetNumberOfIterations(config.DIFFUSION_ITERATIONS)
                res = f.Execute(img)
                st = sitk.StatisticsImageFilter()
                st.Execute(res)
                out[c] = [r(st.GetMean()), r(st.GetSigma())]
            return out
        runner.run("3a_curvature_anisotropic_diffusion", lambda: diffusion(sitk.CurvatureAnisotropicDiffusionImageFilter))
        runner.run("3a_gradient_anisotropic_diffusion", lambda: diffusion(sitk.GradientAnisotropicDiffusionImageFilter))

    # --- 3b label map (also needed by 3c, 3e, 3f)
    def t_labels():
        state["labels"] = {}
        out = {}
        for c, img in cts.items():
            bone = sitk.BinaryThreshold(img, config.BONE_THRESHOLD, 30000, 1, 0)
            cc = sitk.ConnectedComponent(bone)
            relabel = sitk.RelabelComponentImageFilter()
            relabel.SetMinimumObjectSize(config.MIN_COMPONENT_SIZE)
            lab = relabel.Execute(cc)
            state["labels"][c] = lab
            out[c] = relabel.GetNumberOfObjects()
        return out
    runner.run("3b_bone_labelmap_threshold_cc_relabel", t_labels)

    # --- 3c label statistics
    if want("3c"):
        def t_label_stats():
            out = {}
            for c, img in cts.items():
                ls = sitk.LabelStatisticsImageFilter()
                ls.Execute(img, state["labels"][c])
                labels = sorted(ls.GetLabels())
                out[c] = {"n": len(labels), "mean1": r(ls.GetMean(1)), "count1": ls.GetCount(1)}
            return out
        runner.run("3c_label_intensity_statistics", t_label_stats)

        def t_shape_stats():
            out = {}
            for c in cases:
                ss = sitk.LabelShapeStatisticsImageFilter()
                ss.ComputeOrientedBoundingBoxOn()
                ss.ComputeFeretDiameterOff()
                ss.ComputePerimeterOn()
                ss.Execute(state["labels"][c])
                out[c] = {"vol1": r(ss.GetPhysicalSize(1)), "obb1": [r(x) for x in ss.GetOrientedBoundingBoxSize(1)]}
            return out
        runner.run("3c_label_shape_statistics", t_shape_stats)

    # --- 3d histogram and statistics
    vtk_cts = {c: to_vtk_image(sitk.GetArrayViewFromImage(img), img) for c, img in cts.items()}
    if want("3d"):
        def t_accumulate():
            out = {}
            for c, vi in vtk_cts.items():
                acc = vtkImageAccumulate()
                acc.SetInputData(vi)
                acc.SetComponentExtent(0, config.ACCUMULATE_BINS - 1, 0, 0, 0, 0)
                acc.SetComponentOrigin(-1024, 0, 0)
                acc.SetComponentSpacing(1, 0, 0)
                acc.IgnoreZeroOff()
                acc.Update()
                out[c] = [acc.GetVoxelCount(), r(acc.GetMean()[0])]
            return out
        runner.run("3d_histogram_vtkImageAccumulate", t_accumulate)

        def t_stats():
            out = {}
            for c, img in cts.items():
                st = sitk.StatisticsImageFilter()
                st.Execute(img)
                out[c] = [st.GetMinimum(), st.GetMaximum(), r(st.GetMean())]
            return out
        runner.run("3d_image_statistics_sitk", t_stats)

    # --- 3e surface
    if want("3e") or want("3f"):
        bone_vtk = {c: to_vtk_image((sitk.GetArrayViewFromImage(lab) > 0).astype(np.uint8), lab)
                    for c, lab in state["labels"].items()}

        def t_fe():
            state["fe"] = {}
            out = {}
            for c, vi in bone_vtk.items():
                fe = vtkFlyingEdges3D()
                fe.SetInputData(vi)
                fe.SetValue(0, 0.5)
                fe.ComputeNormalsOff()
                fe.ComputeGradientsOff()
                fe.ComputeScalarsOff()
                fe.Update()
                state["fe"][c] = fe.GetOutput()
                out[c] = [fe.GetOutput().GetNumberOfPoints(), fe.GetOutput().GetNumberOfPolys()]
            return out
        runner.run("3e_flying_edges", t_fe)

        def t_smooth():
            state["smooth"] = {}
            out = {}
            for c, pd in state["fe"].items():
                sm = vtkWindowedSincPolyDataFilter()
                sm.SetInputData(pd)
                sm.SetNumberOfIterations(config.SMOOTH_ITERATIONS)
                sm.SetPassBand(config.SMOOTH_PASSBAND)
                sm.BoundarySmoothingOff()
                sm.FeatureEdgeSmoothingOff()
                sm.NonManifoldSmoothingOn()
                sm.NormalizeCoordinatesOn()
                sm.Update()
                state["smooth"][c] = sm.GetOutput()
                mp = vtkMassProperties()
                mp.SetInputData(sm.GetOutput())
                out[c] = r(mp.GetSurfaceArea())
            return out
        runner.run("3e_windowed_sinc_smoothing", t_smooth)

        def t_normals():
            state["surface"] = {}
            out = {}
            for c, pd in state["smooth"].items():
                n = vtkPolyDataNormals()
                n.SetInputData(pd)
                n.SplittingOff()
                n.ConsistencyOn()
                n.ComputePointNormalsOn()
                n.Update()
                state["surface"][c] = n.GetOutput()
                out[c] = n.GetOutput().GetNumberOfPoints()
            return out
        runner.run("3e_polydata_normals", t_normals)

    # --- 3f surface back to label map
    if want("3f"):
        def t_stencil():
            state["relabeled"] = {}
            for c, pd in state["surface"].items():
                ref = bone_vtk[c]
                st = vtkPolyDataToImageStencil()
                st.SetInputData(pd)
                st.SetOutputOrigin(ref.GetOrigin())
                st.SetOutputSpacing(ref.GetSpacing())
                st.SetOutputWholeExtent(ref.GetExtent())
                st.Update()
                s2i = vtkImageStencilToImage()
                s2i.SetInputConnection(st.GetOutputPort())
                s2i.SetInsideValue(1)
                s2i.SetOutsideValue(0)
                s2i.SetOutputScalarTypeToUnsignedChar()
                s2i.Update()
                state["relabeled"][c] = s2i.GetOutput()
            return {c: int(numpy_support.vtk_to_numpy(im.GetPointData().GetScalars()).sum(dtype=np.int64))
                    for c, im in state["relabeled"].items()}
        runner.run("3f_polydata_to_labelmap_stencil", t_stencil)
        # Output check (not timed): Dice between the original and the reconstructed label map
        dices = {}
        for c, im in state["relabeled"].items():
            a = numpy_support.vtk_to_numpy(im.GetPointData().GetScalars())
            b = numpy_support.vtk_to_numpy(bone_vtk[c].GetPointData().GetScalars())
            dices[c] = round(float(dice(a, b)), 4)
        runner.results["3f_polydata_to_labelmap_stencil"]["dice"] = dices
        print(f"  3f Dice: {dices}")

    return {"cases": cases}
