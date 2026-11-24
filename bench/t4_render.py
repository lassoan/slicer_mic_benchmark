"""Section 4: C++ visualization with VTK (offscreen render window, 1920x1080).

4a surface rendering of the smoothed bone surface (flying edges), full and decimated, camera rotating 1 deg/frame
4b GPU volume ray casting (vtkGPUVolumeRayCastMapper), CT bone transfer function
4c CPU volume ray casting (vtkFixedPointVolumeRayCastMapper), 10 deg/frame
4d frames 0 and 90 are saved as PNG for comparison between environments (compare.py)
"""

import numpy as np
import SimpleITK as sitk
from vtkmodules.util import numpy_support
from vtkmodules.vtkCommonDataModel import vtkPiecewiseFunction
from vtkmodules.vtkFiltersCore import vtkFlyingEdges3D, vtkPolyDataNormals, vtkQuadricDecimation, vtkWindowedSincPolyDataFilter
from vtkmodules.vtkIOImage import vtkPNGWriter
from vtkmodules.vtkRenderingCore import (vtkActor, vtkColorTransferFunction, vtkPolyDataMapper, vtkRenderer,
                                         vtkRenderWindow, vtkVolume, vtkVolumeProperty, vtkWindowToImageFilter)
from vtkmodules.vtkRenderingVolume import vtkFixedPointVolumeRayCastMapper, vtkGPUVolumeRayCastMapper
import vtkmodules.vtkRenderingOpenGL2  # noqa: F401  (registers the OpenGL render window)
import vtkmodules.vtkRenderingVolumeOpenGL2  # noqa: F401

from bench import config, harness
from bench.t3_cpp import to_vtk_image

DEFAULT_REPEATS = 3


def bone_surface(vi_ct):
    from vtkmodules.vtkImagingCore import vtkImageThreshold
    th = vtkImageThreshold()
    th.SetInputData(vi_ct)
    th.ThresholdByUpper(config.BONE_THRESHOLD)
    th.SetInValue(1)
    th.SetOutValue(0)
    th.SetOutputScalarTypeToUnsignedChar()
    fe = vtkFlyingEdges3D()
    fe.SetInputConnection(th.GetOutputPort())
    fe.SetValue(0, 0.5)
    sm = vtkWindowedSincPolyDataFilter()
    sm.SetInputConnection(fe.GetOutputPort())
    sm.SetNumberOfIterations(config.SMOOTH_ITERATIONS)
    sm.SetPassBand(config.SMOOTH_PASSBAND)
    sm.NormalizeCoordinatesOn()
    sm.BoundarySmoothingOff()
    sm.FeatureEdgeSmoothingOff()
    sm.NonManifoldSmoothingOn()
    n = vtkPolyDataNormals()
    n.SetInputConnection(sm.GetOutputPort())
    n.SplittingOff()
    n.ConsistencyOn()
    n.Update()
    return n.GetOutput()


def decimate(pd, keep):
    d = vtkQuadricDecimation()
    d.SetInputData(pd)
    d.SetTargetReduction(1.0 - keep)
    n = vtkPolyDataNormals()
    n.SetInputConnection(d.GetOutputPort())
    n.SplittingOff()
    n.Update()
    return n.GetOutput()


def make_window():
    rw = vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.SetSize(*config.RENDER_SIZE)
    rw.SetMultiSamples(0)
    ren = vtkRenderer()
    ren.SetBackground(0.1, 0.1, 0.15)
    rw.AddRenderer(ren)
    return rw, ren


def bone_volume_property():
    color = vtkColorTransferFunction()
    for x, rgb in [(-3024, (0, 0, 0)), (-16, (0.73, 0.25, 0.30)), (641, (0.90, 0.82, 0.56)), (3071, (1, 1, 1))]:
        color.AddRGBPoint(x, *rgb)
    opacity = vtkPiecewiseFunction()
    for x, o in [(-3024, 0), (-16, 0), (641, 0.72), (3071, 0.71)]:
        opacity.AddPoint(x, o)
    prop = vtkVolumeProperty()
    prop.SetColor(color)
    prop.SetScalarOpacity(opacity)
    prop.ShadeOn()
    prop.SetAmbient(0.2)
    prop.SetDiffuse(1.0)
    prop.SetSpecular(0.0)
    prop.SetInterpolationTypeToLinear()
    return prop


def save_png(rw, path):
    w2i = vtkWindowToImageFilter()
    w2i.SetInput(rw)
    w2i.ReadFrontBufferOff()
    w2i.Update()
    wr = vtkPNGWriter()
    wr.SetFileName(str(path))
    wr.SetInputConnection(w2i.GetOutputPort())
    wr.Write()


def image_checksum(rw):
    w2i = vtkWindowToImageFilter()
    w2i.SetInput(rw)
    w2i.ReadFrontBufferOff()
    w2i.Update()
    a = numpy_support.vtk_to_numpy(w2i.GetOutput().GetPointData().GetScalars())
    return round(float(a.mean()), 2)


def run(runner, cases=None, tasks=None, threads=1, env="unknown"):
    cases = cases or [config.RENDER_CASE, config.RENDER_CASE_LARGE]
    harness.set_library_threads(threads)
    img_dir = config.RESULTS_DIR / env / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    def want(name):
        return tasks is None or any(name.startswith(t) for t in tasks)

    # GL capabilities (renderer, version) for the record
    rw, ren = make_window()
    rw.Render()
    gl_info = rw.ReportCapabilities()
    rw.Finalize()
    print("  " + "\n  ".join(l for l in gl_info.splitlines() if "OpenGL" in l and ("vendor" in l or "renderer" in l or "version" in l)))

    for case in cases:
        ct = sitk.ReadImage(str(config.NRRD_DIR / f"{case}.nrrd"))
        vi = to_vtk_image(sitk.GetArrayViewFromImage(ct), ct)
        surface = bone_surface(vi)
        surfaces = {"full": surface, "decimated": decimate(surface, config.DECIMATE_KEEP)}
        print(f"  {case}: surface {surface.GetNumberOfPolys()} triangles, decimated {surfaces['decimated'].GetNumberOfPolys()}")

        def setup_surface(pd):
            rw, ren = make_window()
            mapper = vtkPolyDataMapper()
            mapper.SetInputData(pd)
            mapper.ScalarVisibilityOff()
            actor = vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(0.95, 0.9, 0.8)
            ren.AddActor(actor)
            ren.ResetCamera()
            ren.GetActiveCamera().Elevation(-80)
            ren.GetActiveCamera().OrthogonalizeViewUp()
            ren.ResetCamera()
            return rw, ren

        def setup_volume(mapper):
            rw, ren = make_window()
            mapper.SetInputData(vi)
            mapper.AutoAdjustSampleDistancesOff()
            mapper.SetSampleDistance(0.5 * min(vi.GetSpacing()))
            vol = vtkVolume()
            vol.SetMapper(mapper)
            vol.SetProperty(bone_volume_property())
            ren.AddVolume(vol)
            ren.ResetCamera()
            ren.GetActiveCamera().Elevation(-80)
            ren.GetActiveCamera().OrthogonalizeViewUp()
            ren.ResetCamera()
            return rw, ren

        def first_frame(setup):
            def fn():
                rw, ren = setup()
                rw.Render()
                rw.WaitForCompletion()
                rw.Finalize()
                return {}
            return fn

        def rotate(setup, frames, step, name):
            def fn():
                rw, ren = setup()
                rw.Render()
                rw.WaitForCompletion()
                cam = ren.GetActiveCamera()
                checks = []
                import time
                t0 = time.perf_counter()
                for i in range(frames):
                    cam.Azimuth(step)
                    rw.Render()
                    rw.WaitForCompletion()
                elapsed = time.perf_counter() - t0
                checks.append(image_checksum(rw))
                save_png(rw, img_dir / f"{name}-{case}-last.png")
                rw.Finalize()
                return {"frames": frames, "fps": round(frames / elapsed, 2), "last_frame_mean": checks[0]}
            return fn

        if want("4a"):
            for kind, pd in surfaces.items():
                setup = lambda pd=pd: setup_surface(pd)  # noqa: E731
                runner.run(f"4a_surface_{kind}_first_frame_{case}", first_frame(setup))
                runner.run(f"4a_surface_{kind}_{config.SURFACE_FRAMES}_frames_{case}",
                           rotate(setup, config.SURFACE_FRAMES, 1.0, f"surface_{kind}"))
        if want("4b"):
            setup = lambda: setup_volume(vtkGPUVolumeRayCastMapper())  # noqa: E731
            runner.run(f"4b_gpu_volume_first_frame_{case}", first_frame(setup))
            runner.run(f"4b_gpu_volume_{config.VOLUME_GPU_FRAMES}_frames_{case}",
                       rotate(setup, config.VOLUME_GPU_FRAMES, 1.0, "gpu_volume"))
        if want("4c") and case == config.RENDER_CASE:
            setup = lambda: setup_volume(vtkFixedPointVolumeRayCastMapper())  # noqa: E731
            runner.run(f"4c_cpu_volume_{config.VOLUME_CPU_FRAMES}_frames_{case}",
                       rotate(setup, config.VOLUME_CPU_FRAMES, 10.0, "cpu_volume"))
    return {"cases": cases, "gl_info": gl_info}
