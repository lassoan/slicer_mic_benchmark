# Benchmark results

Machine: GIGABYTE AORUS 17 YE5 | Windows 11 Education 25H2 x64 | 12th Gen Intel(R) Core(TM) i7-12700H (14C/20T) | 32.0 GB RAM | NVIDIA GeForce RTX 3080 Ti Laptop GPU | Intel(R) Iris(R) Xe Graphics.

Times are medians in seconds.
Environments: **x64** = x64 Python and x64 packages.

## Startup and import time

| Task | x64 (s) |
| --- | ---: |
| python_startup | 0.033 |
| import_numpy_scipy | 0.451 |
| import_simpleitk | 0.194 |
| import_vtk_all | 0.655 |
| import_torch | 1.661 |
| import_bench_stack | 1.322 |

## 1. File I/O and DICOM geometry — 20 threads

| Task | x64 (s) |
| --- | ---: |
| 1a_read_dicom_headers_sitk | 7.738 |
| 1a_read_dicom_headers_pydicom | 2.203 |
| 1b_check_geometry_pure_python_x50 | 0.448 |
| 1c_read_dicom_volumes_sitk | 9.035 |
| 1d_write_nrrd_raw | 2.641 |
| 1d_write_nrrd_gzip | 36.0 |
| 1e_write_nifti | 1.953 |
| 1e_write_nifti_gz | 31.5 |
| 1f_read_nrrd_raw | 1.468 |
| 1f_read_nrrd_gzip | 12.9 |
| 1f_read_nifti_raw_dataobj | 1.197 |
| 1f_read_nifti_gz_dataobj | 10.9 |
| 1f_read_nifti_gz_fdata_float32 | 12.0 |

CPU load from other processes during the run (% of machine, mean / max): x64 6.8 / 27.6

## 2. Vectorized Python algorithms (numpy, scipy) — 1 thread

| Task | x64 (s) |
| --- | ---: |
| 2a_window_level_uint8 | 1.464 |
| 2a_zscore_clip_float32 | 2.001 |
| 2a_elementwise_synthetic_512cubed | 1.359 |
| 2b_histogram | 2.968 |
| 2b_percentiles | 1.240 |
| 2b_unique | 1.302 |
| 2c_gaussian_filter | 10.4 |
| 2c_median_filter_crop | 21.5 |
| 2c_binary_dilate_erode | 3.603 |
| 2d_label_largest_component_edt | 14.0 |
| 2e_zoom_isotropic_1.5mm | 1.852 |
| 2e_affine_rotation | 13.7 |
| 2f_pca_bone_points_svd | 0.861 |
| 2f_svd_2000 | 2.343 |
| 2f_matmul_2000 | 0.140 |
| 2f_landmark_fit_lstsq_kabsch | 0.010 |
| 2f_eigh_batch_3x3 | 0.754 |
| 2g_fft_phase_correlation | 1.332 |

CPU load from other processes during the run (% of machine, mean / max): x64 2.2 / 12.1

## 2. Vectorized Python algorithms (numpy, scipy) — 20 threads

| Task | x64 (s) |
| --- | ---: |
| 2a_window_level_uint8 | 1.449 |
| 2a_zscore_clip_float32 | 1.993 |
| 2a_elementwise_synthetic_512cubed | 1.378 |
| 2b_histogram | 2.255 |
| 2b_percentiles | 1.262 |
| 2b_unique | 1.287 |
| 2c_gaussian_filter | 10.4 |
| 2c_median_filter_crop | 21.4 |
| 2c_binary_dilate_erode | 3.590 |
| 2d_label_largest_component_edt | 14.2 |
| 2e_zoom_isotropic_1.5mm | 1.850 |
| 2e_affine_rotation | 13.7 |
| 2f_pca_bone_points_svd | 0.842 |
| 2f_svd_2000 | 1.871 |
| 2f_matmul_2000 | 0.037 |
| 2f_landmark_fit_lstsq_kabsch | 0.010 |
| 2f_eigh_batch_3x3 | 0.779 |
| 2g_fft_phase_correlation | 1.378 |

CPU load from other processes during the run (% of machine, mean / max): x64 1.4 / 4.9

## 3. C++ algorithms (SimpleITK, VTK) — 1 thread

| Task | x64 (s) |
| --- | ---: |
| 3a_curvature_anisotropic_diffusion | 28.3 |
| 3a_gradient_anisotropic_diffusion | 16.5 |
| 3b_bone_labelmap_threshold_cc_relabel | 1.718 |
| 3c_label_intensity_statistics | 9.846 |
| 3c_label_shape_statistics | 1.480 |
| 3d_histogram_vtkImageAccumulate | 0.900 |
| 3d_image_statistics_sitk | 1.079 |
| 3e_flying_edges | 0.677 |
| 3e_windowed_sinc_smoothing | 4.839 |
| 3e_polydata_normals | 2.914 |
| 3f_polydata_to_labelmap_stencil | 58.9 |

CPU load from other processes during the run (% of machine, mean / max): x64 1.4 / 4.9

## 3. C++ algorithms (SimpleITK, VTK) — 20 threads

| Task | x64 (s) |
| --- | ---: |
| 3a_curvature_anisotropic_diffusion | 6.186 |
| 3a_gradient_anisotropic_diffusion | 5.064 |
| 3b_bone_labelmap_threshold_cc_relabel | 1.036 |
| 3c_label_intensity_statistics | 1.665 |
| 3c_label_shape_statistics | 0.669 |
| 3d_histogram_vtkImageAccumulate | 0.898 |
| 3d_image_statistics_sitk | 0.111 |
| 3e_flying_edges | 0.113 |
| 3e_windowed_sinc_smoothing | 1.260 |
| 3e_polydata_normals | 2.301 |
| 3f_polydata_to_labelmap_stencil | 10.0 |

CPU load from other processes during the run (% of machine, mean / max): x64 1.8 / 5.5

## 4. C++ visualization (VTK, offscreen 1920x1080) — 1 thread

| Task | x64 (s) |
| --- | ---: |
| 4a_surface_full_first_frame_case01 | 0.236 |
| 4a_surface_full_360_frames_case01 | 0.396 |
| 4a_surface_decimated_first_frame_case01 | 0.180 |
| 4a_surface_decimated_360_frames_case01 | 0.368 |
| 4b_gpu_volume_first_frame_case01 | 0.215 |
| 4b_gpu_volume_60_frames_case01 | 0.699 |
| 4c_cpu_volume_36_frames_case01 | 50.3 |
| 4a_surface_full_first_frame_case18 | 0.315 |
| 4a_surface_full_360_frames_case18 | 0.644 |
| 4a_surface_decimated_first_frame_case18 | 0.209 |
| 4a_surface_decimated_360_frames_case18 | 0.434 |
| 4b_gpu_volume_first_frame_case18 | 0.624 |
| 4b_gpu_volume_60_frames_case18 | 1.464 |

CPU load from other processes during the run (% of machine, mean / max): x64 1.7 / 5.7

## 4. C++ visualization (VTK, offscreen 1920x1080) — 20 threads

| Task | x64 (s) |
| --- | ---: |
| 4a_surface_full_first_frame_case01 | 0.220 |
| 4a_surface_full_360_frames_case01 | 0.401 |
| 4a_surface_decimated_first_frame_case01 | 0.180 |
| 4a_surface_decimated_360_frames_case01 | 0.353 |
| 4b_gpu_volume_first_frame_case01 | 0.201 |
| 4b_gpu_volume_60_frames_case01 | 0.692 |
| 4c_cpu_volume_36_frames_case01 | 8.987 |
| 4a_surface_full_first_frame_case18 | 0.289 |
| 4a_surface_full_360_frames_case18 | 0.597 |
| 4a_surface_decimated_first_frame_case18 | 0.183 |
| 4a_surface_decimated_360_frames_case18 | 0.433 |
| 4b_gpu_volume_first_frame_case18 | 0.626 |
| 4b_gpu_volume_60_frames_case18 | 1.488 |

CPU load from other processes during the run (% of machine, mean / max): x64 2.5 / 5.0

## 5. AI segmentation (CPU) — 20 threads

| Task | x64 (s) |
| --- | ---: |
| 5a_totalseg_fast_case01 | 36.9 |
| 5a_totalseg_fast_case02 | 25.0 |
| 5a_totalseg_fast_case03 | 25.6 |
| 5a_totalseg_fast_case11 | 23.0 |
| 5a_totalseg_fast_case13 | 17.7 |
| 5b_totalseg_full_case01 | 340.9 |
| 5c_monai_abdominal-organs-3mm-v2.0.0_case01 | 17.1 |
| 5c_monai_abdominal-organs-3mm-v2.0.0_case02 | 24.1 |
| 5c_monai_abdominal-organs-3mm-v2.0.0_case03 | 17.2 |
| 5c_monai_abdominal-organs-3mm-v2.0.0_case11 | 15.6 |
| 5c_monai_abdominal-organs-3mm-v2.0.0_case13 | 6.234 |

CPU load from other processes during the run (% of machine, mean / max): x64 3.0 / 7.9

## 6. ONNX Runtime vs PyTorch, MONAIAuto3DSeg network (CPU) — 20 threads

| Task | x64 (s) |
| --- | ---: |
| 6a_patch_torch_t1 | 10.3 |
| 6a_patch_onnxruntime_t1 | 11.5 |
| 6a_patch_torch_t20 | 2.924 |
| 6a_patch_onnxruntime_t20 | 4.040 |
| 6b_sliding_window_torch_case01 | 12.1 |
| 6b_sliding_window_onnxruntime_case01 | 17.6 |
| 6b_sliding_window_torch_case02 | 27.4 |
| 6b_sliding_window_onnxruntime_case02 | 39.2 |
| 6b_sliding_window_torch_case03 | 28.8 |
| 6b_sliding_window_onnxruntime_case03 | 38.8 |
| 6b_sliding_window_torch_case11 | 13.1 |
| 6b_sliding_window_onnxruntime_case11 | 17.4 |
| 6b_sliding_window_torch_case13 | 12.7 |
| 6b_sliding_window_onnxruntime_case13 | 17.7 |

CPU load from other processes during the run (% of machine, mean / max): x64 2.0 / 8.1
