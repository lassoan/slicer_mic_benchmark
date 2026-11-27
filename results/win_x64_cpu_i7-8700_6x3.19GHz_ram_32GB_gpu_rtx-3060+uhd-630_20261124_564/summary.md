# Benchmark results

Machine: Alienware Alienware Aurora R8 | Windows 11 Education 25H2 x64 | Intel(R) Core(TM) i7-8700 CPU @ 3.20GHz (6C/12T) | 32.0 GB RAM | NVIDIA GeForce RTX 3060 | Intel(R) UHD Graphics 630.

Times are medians in seconds.
Environments: **x64** = x64 Python and x64 packages.

## Startup and import time

| Task | x64 (s) |
| --- | ---: |
| python_startup | 0.042 |
| import_numpy_scipy | 0.969 |
| import_simpleitk | 0.232 |
| import_vtk_all | 0.951 |
| import_torch | 2.548 |
| import_bench_stack | 2.294 |

## 1. File I/O and DICOM geometry — 12 threads

| Task | x64 (s) |
| --- | ---: |
| 1a_read_dicom_headers_sitk | 19.9 |
| 1a_read_dicom_headers_pydicom | 4.792 |
| 1b_check_geometry_pure_python_x50 | 0.751 |
| 1c_read_dicom_volumes_sitk | 21.7 |
| 1d_write_nrrd_raw | 17.3 |
| 1d_write_nrrd_gzip | 50.0 |
| 1e_write_nifti | 36.0 |
| 1e_write_nifti_gz | 43.3 |
| 1f_read_nrrd_raw | 1.835 |
| 1f_read_nrrd_gzip | 13.3 |
| 1f_read_nifti_raw_dataobj | 1.872 |
| 1f_read_nifti_gz_dataobj | 12.2 |
| 1f_read_nifti_gz_fdata_float32 | 13.7 |

CPU load from other processes during the run (% of machine, mean / max): x64 8.8 / 15.8

## 2. Vectorized Python algorithms (numpy, scipy) — 1 thread

| Task | x64 (s) |
| --- | ---: |
| 2a_window_level_uint8 | 1.838 |
| 2a_zscore_clip_float32 | 2.375 |
| 2a_elementwise_synthetic_512cubed | 1.756 |
| 2b_histogram | 3.253 |
| 2b_percentiles | 1.513 |
| 2b_unique | 1.994 |
| 2c_gaussian_filter | 12.9 |
| 2c_median_filter_crop | 25.4 |
| 2c_binary_dilate_erode | 6.356 |
| 2d_label_largest_component_edt | 17.2 |
| 2e_zoom_isotropic_1.5mm | 2.754 |
| 2e_affine_rotation | 22.7 |
| 2f_pca_bone_points_svd | 1.118 |
| 2f_svd_2000 | 3.731 |
| 2f_matmul_2000 | 0.160 |
| 2f_landmark_fit_lstsq_kabsch | 0.017 |
| 2f_eigh_batch_3x3 | 1.171 |
| 2g_fft_phase_correlation | 1.893 |

CPU load from other processes during the run (% of machine, mean / max): x64 8.1 / 13.0

## 2. Vectorized Python algorithms (numpy, scipy) — 12 threads

| Task | x64 (s) |
| --- | ---: |
| 2a_window_level_uint8 | 1.952 |
| 2a_zscore_clip_float32 | 2.506 |
| 2a_elementwise_synthetic_512cubed | 1.752 |
| 2b_histogram | 3.609 |
| 2b_percentiles | 1.495 |
| 2b_unique | 1.978 |
| 2c_gaussian_filter | 13.1 |
| 2c_median_filter_crop | 25.4 |
| 2c_binary_dilate_erode | 6.276 |
| 2d_label_largest_component_edt | 16.8 |
| 2e_zoom_isotropic_1.5mm | 2.703 |
| 2e_affine_rotation | 22.1 |
| 2f_pca_bone_points_svd | 1.063 |
| 2f_svd_2000 | 2.585 |
| 2f_matmul_2000 | 0.067 |
| 2f_landmark_fit_lstsq_kabsch | 0.018 |
| 2f_eigh_batch_3x3 | 1.166 |
| 2g_fft_phase_correlation | 1.874 |

CPU load from other processes during the run (% of machine, mean / max): x64 8.0 / 14.3

## 3. C++ algorithms (SimpleITK, VTK) — 1 thread

| Task | x64 (s) |
| --- | ---: |
| 3a_curvature_anisotropic_diffusion | 52.3 |
| 3a_gradient_anisotropic_diffusion | 33.9 |
| 3b_bone_labelmap_threshold_cc_relabel | 2.624 |
| 3c_label_intensity_statistics | 13.3 |
| 3c_label_shape_statistics | 2.624 |
| 3d_histogram_vtkImageAccumulate | 1.597 |
| 3d_image_statistics_sitk | 1.674 |
| 3e_flying_edges | 1.002 |
| 3e_windowed_sinc_smoothing | 7.104 |
| 3e_polydata_normals | 3.905 |
| 3f_polydata_to_labelmap_stencil | 76.3 |

CPU load from other processes during the run (% of machine, mean / max): x64 7.9 / 14.6

## 3. C++ algorithms (SimpleITK, VTK) — 12 threads

| Task | x64 (s) |
| --- | ---: |
| 3a_curvature_anisotropic_diffusion | 14.0 |
| 3a_gradient_anisotropic_diffusion | 9.425 |
| 3b_bone_labelmap_threshold_cc_relabel | 1.136 |
| 3c_label_intensity_statistics | 2.466 |
| 3c_label_shape_statistics | 1.182 |
| 3d_histogram_vtkImageAccumulate | 1.620 |
| 3d_image_statistics_sitk | 0.265 |
| 3e_flying_edges | 0.215 |
| 3e_windowed_sinc_smoothing | 2.214 |
| 3e_polydata_normals | 3.192 |
| 3f_polydata_to_labelmap_stencil | 20.6 |

CPU load from other processes during the run (% of machine, mean / max): x64 16.3 / 40.0

## 4. C++ visualization (VTK, offscreen 1920x1080) — 1 thread

| Task | x64 (s) |
| --- | ---: |
| 4a_surface_full_first_frame_case01 | 0.226 |
| 4a_surface_full_360_frames_case01 | 0.523 |
| 4a_surface_decimated_first_frame_case01 | 0.181 |
| 4a_surface_decimated_360_frames_case01 | 0.455 |
| 4b_gpu_volume_first_frame_case01 | 0.212 |
| 4b_gpu_volume_60_frames_case01 | 0.784 |
| 4c_cpu_volume_36_frames_case01 | 75.6 |
| 4a_surface_full_first_frame_case18 | 0.323 |
| 4a_surface_full_360_frames_case18 | 0.887 |
| 4a_surface_decimated_first_frame_case18 | 0.196 |
| 4a_surface_decimated_360_frames_case18 | 0.531 |
| 4b_gpu_volume_first_frame_case18 | 0.903 |
| 4b_gpu_volume_60_frames_case18 | 1.830 |

CPU load from other processes during the run (% of machine, mean / max): x64 8.1 / 18.4

## 4. C++ visualization (VTK, offscreen 1920x1080) — 12 threads

| Task | x64 (s) |
| --- | ---: |
| 4a_surface_full_first_frame_case01 | 0.213 |
| 4a_surface_full_360_frames_case01 | 0.517 |
| 4a_surface_decimated_first_frame_case01 | 0.188 |
| 4a_surface_decimated_360_frames_case01 | 0.453 |
| 4b_gpu_volume_first_frame_case01 | 0.213 |
| 4b_gpu_volume_60_frames_case01 | 0.776 |
| 4c_cpu_volume_36_frames_case01 | 16.0 |
| 4a_surface_full_first_frame_case18 | 0.297 |
| 4a_surface_full_360_frames_case18 | 0.845 |
| 4a_surface_decimated_first_frame_case18 | 0.191 |
| 4a_surface_decimated_360_frames_case18 | 0.528 |
| 4b_gpu_volume_first_frame_case18 | 0.877 |
| 4b_gpu_volume_60_frames_case18 | 1.855 |

CPU load from other processes during the run (% of machine, mean / max): x64 11.4 / 19.9

## 5. AI segmentation (CPU) — 12 threads

| Task | x64 (s) |
| --- | ---: |
| 5a_totalseg_fast_case01 | 43.6 |
| 5a_totalseg_fast_case02 | 36.2 |
| 5a_totalseg_fast_case03 | 36.5 |
| 5a_totalseg_fast_case11 | 33.0 |
| 5a_totalseg_fast_case13 | 24.5 |
| 5b_totalseg_full_case01 | 488.1 |
| 5c_monai_abdominal-organs-3mm-v2.0.0_case01 | 25.6 |
| 5c_monai_abdominal-organs-3mm-v2.0.0_case02 | 37.1 |
| 5c_monai_abdominal-organs-3mm-v2.0.0_case03 | 25.8 |
| 5c_monai_abdominal-organs-3mm-v2.0.0_case11 | 23.5 |
| 5c_monai_abdominal-organs-3mm-v2.0.0_case13 | 9.093 |
| 5d_totalseg_full_cuda_case01 (run later: x64, 2026-11-27) | 110.5 |

CPU load from other processes during the run (% of machine, mean / max): x64 12.5 / 24.2

## 6. ONNX Runtime vs PyTorch, MONAIAuto3DSeg network (CPU) — 12 threads

| Task | x64 (s) |
| --- | ---: |
| 6a_patch_torch_t1 | 12.6 |
| 6a_patch_onnxruntime_t1 | 13.6 |
| 6a_patch_torch_t12 | 4.086 |
| 6a_patch_onnxruntime_t12 | 4.714 |
| 6b_sliding_window_torch_case01 | 18.7 |
| 6b_sliding_window_onnxruntime_case01 | 19.7 |
| 6b_sliding_window_torch_case02 | 42.2 |
| 6b_sliding_window_onnxruntime_case02 | 43.8 |
| 6b_sliding_window_torch_case03 | 42.7 |
| 6b_sliding_window_onnxruntime_case03 | 44.1 |
| 6b_sliding_window_torch_case11 | 20.5 |
| 6b_sliding_window_onnxruntime_case11 | 19.5 |
| 6b_sliding_window_torch_case13 | 18.6 |
| 6b_sliding_window_onnxruntime_case13 | 19.4 |

CPU load from other processes during the run (% of machine, mean / max): x64 10.4 / 21.1
