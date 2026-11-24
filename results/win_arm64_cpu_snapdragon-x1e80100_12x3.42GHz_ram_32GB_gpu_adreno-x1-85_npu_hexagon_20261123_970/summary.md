# Benchmark results

Machine: Snapdragon(R) X 12-core X1E80100 @ 3.40 GHz, 12 logical CPUs, 31.6 GB RAM, Windows 10.0.26300.

Times are medians in seconds. Speed-up = time in x64 (emulated) / time in the environment; higher is better.
Environments: **x64** = x64 Python and x64 packages, emulated (Prism); **arm64ec** = ARM64EC Python (native interpreter) with the same x64 packages (emulated); **arm64** = native ARM64 Python and packages.

## Startup and import time

| Task | x64 (s) | arm64ec (s) | arm64 (s) | arm64ec speed-up | arm64 speed-up |
| --- | ---: | ---: | ---: | ---: | ---: |
| python_startup | 0.042 | 0.040 | 0.025 | 1.06× | 1.71× |
| import_numpy_scipy | 0.487 | 0.422 | 0.339 | 1.16× | 1.43× |
| import_simpleitk | 0.202 | 0.188 | 0.141 | 1.08× | 1.44× |
| import_vtk_all | 0.755 | 0.727 | 0.600 | 1.04× | 1.26× |
| import_torch | 1.728 | 1.563 | 1.157 | 1.11× | 1.49× |
| import_bench_stack | 1.353 | 1.272 | 1.037 | 1.06× | 1.31× |
| **Geometric mean** | | | | **1.08×** | **1.43×** |

## 1. File I/O and DICOM geometry — 12 threads

| Task | x64 (s) | arm64ec (s) | arm64 (s) | arm64ec speed-up | arm64 speed-up |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1a_read_dicom_headers_sitk | 11.2 | 11.1 | 6.932 | 1.01× | 1.62× |
| 1a_read_dicom_headers_pydicom | 2.759 | 2.451 | 1.789 | 1.13× | 1.54× |
| 1b_check_geometry_pure_python_x50 | 0.883 | 0.661 | 0.490 | 1.34× | 1.80× |
| 1c_read_dicom_volumes_sitk | 12.5 | 12.3 | 8.013 | 1.02× | 1.56× |
| 1d_write_nrrd_raw | 2.788 | 2.689 | 1.910 | 1.04× | 1.46× |
| 1d_write_nrrd_gzip | 41.2 | 14.5 | 32.0 | 2.85× | 1.29× |
| 1e_write_nifti | 1.514 | 1.558 | 1.053 | 0.97× | 1.44× |
| 1e_write_nifti_gz | 34.4 | 12.9 | 27.2 | 2.67× | 1.26× |
| 1f_read_nrrd_raw | 1.450 | 1.463 | 1.101 | 0.99× | 1.32× |
| 1f_read_nrrd_gzip | 11.8 | 8.447 | 10.6 | 1.40× | 1.12× |
| 1f_read_nifti_raw_dataobj | 1.507 | 1.509 | 1.044 | 1.00× | 1.44× |
| 1f_read_nifti_gz_dataobj | 10.2 | 8.332 | 8.263 | 1.22× | 1.23× |
| 1f_read_nifti_gz_fdata_float32 | 11.8 | 9.932 | 9.814 | 1.19× | 1.20× |
| **Geometric mean** | | | | **1.28×** | **1.39×** |

CPU load from other processes during the run (% of machine, mean / max): x64 1.5 / 6.0, arm64ec 2.2 / 8.0, arm64 1.6 / 5.8

## 2. Vectorized Python algorithms (numpy, scipy) — 1 thread

| Task | x64 (s) | arm64ec (s) | arm64 (s) | arm64ec speed-up | arm64 speed-up |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2a_window_level_uint8 | 2.003 | 2.006 | 1.898 | 1.00× | 1.06× |
| 2a_zscore_clip_float32 | 2.025 | 1.979 | 1.845 | 1.02× | 1.10× |
| 2a_elementwise_synthetic_512cubed | 2.759 | 2.708 | 1.510 | 1.02× | 1.83× |
| 2b_histogram | 3.026 | 3.440 | 1.741 | 0.88× | 1.74× |
| 2b_percentiles | 1.743 | 1.707 | 1.355 | 1.02× | 1.29× |
| 2b_unique | 1.962 | 1.924 | 0.915 | 1.02× | 2.14× |
| 2c_gaussian_filter | 23.3 | 25.1 | 21.1 | 0.93× | 1.11× |
| 2c_median_filter_crop | 20.4 | 20.1 | 19.6 | 1.02× | 1.04× |
| 2c_binary_dilate_erode | 5.873 | 5.872 | 3.392 | 1.00× | 1.73× |
| 2d_label_largest_component_edt | 19.9 | 19.7 | 19.3 | 1.01× | 1.03× |
| 2e_zoom_isotropic_1.5mm | 2.236 | 2.276 | 1.553 | 0.98× | 1.44× |
| 2e_affine_rotation | 18.0 | 18.1 | 11.5 | 1.00× | 1.57× |
| 2f_pca_bone_points_svd | 1.235 | 1.241 | 0.936 | 1.00× | 1.32× |
| 2f_svd_2000 | 3.404 | 3.442 | 2.656 | 0.99× | 1.28× |
| 2f_matmul_2000 | 0.254 | 0.258 | 0.158 | 0.99× | 1.60× |
| 2f_landmark_fit_lstsq_kabsch | 0.024 | 0.024 | 0.011 | 0.98× | 2.21× |
| 2f_eigh_batch_3x3 | 1.348 | 1.348 | 0.953 | 1.00× | 1.41× |
| 2g_fft_phase_correlation | 1.480 | 1.430 | 1.277 | 1.03× | 1.16× |
| **Geometric mean** | | | | **0.99×** | **1.41×** |

CPU load from other processes during the run (% of machine, mean / max): x64 1.2 / 3.3, arm64ec 2.3 / 8.7, arm64 1.2 / 5.2

## 2. Vectorized Python algorithms (numpy, scipy) — 12 threads

| Task | x64 (s) | arm64ec (s) | arm64 (s) | arm64ec speed-up | arm64 speed-up |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2a_window_level_uint8 | 1.996 | 2.038 | 1.825 | 0.98× | 1.09× |
| 2a_zscore_clip_float32 | 2.014 | 2.019 | 1.832 | 1.00× | 1.10× |
| 2a_elementwise_synthetic_512cubed | 2.798 | 2.753 | 1.485 | 1.02× | 1.88× |
| 2b_histogram | 3.090 | 2.794 | 1.752 | 1.11× | 1.76× |
| 2b_percentiles | 1.733 | 1.719 | 1.347 | 1.01× | 1.29× |
| 2b_unique | 1.974 | 1.944 | 0.903 | 1.02× | 2.19× |
| 2c_gaussian_filter | 23.1 | 22.9 | 20.6 | 1.01× | 1.12× |
| 2c_median_filter_crop | 20.3 | 20.0 | 19.6 | 1.02× | 1.04× |
| 2c_binary_dilate_erode | 5.874 | 5.882 | 3.378 | 1.00× | 1.74× |
| 2d_label_largest_component_edt | 19.6 | 19.6 | 19.3 | 1.00× | 1.02× |
| 2e_zoom_isotropic_1.5mm | 2.240 | 2.244 | 1.551 | 1.00× | 1.44× |
| 2e_affine_rotation | 18.1 | 18.0 | 11.5 | 1.00× | 1.57× |
| 2f_pca_bone_points_svd | 1.246 | 1.236 | 0.942 | 1.01× | 1.32× |
| 2f_svd_2000 | 1.430 | 1.439 | 2.110 | 0.99× | 0.68× |
| 2f_matmul_2000 | 0.042 | 0.042 | 0.044 | 1.01× | 0.96× |
| 2f_landmark_fit_lstsq_kabsch | 0.025 | 0.025 | 0.011 | 0.99× | 2.34× |
| 2f_eigh_batch_3x3 | 1.364 | 1.360 | 0.982 | 1.00× | 1.39× |
| 2g_fft_phase_correlation | 1.475 | 1.464 | 0.674 | 1.01× | 2.19× |
| **Geometric mean** | | | | **1.01×** | **1.38×** |

CPU load from other processes during the run (% of machine, mean / max): x64 1.1 / 3.7, arm64ec 1.1 / 3.1, arm64 1.3 / 4.3

## 3. C++ algorithms (SimpleITK, VTK) — 1 thread

| Task | x64 (s) | arm64ec (s) | arm64 (s) | arm64ec speed-up | arm64 speed-up |
| --- | ---: | ---: | ---: | ---: | ---: |
| 3a_curvature_anisotropic_diffusion | 36.1 | 36.0 | 16.7 | 1.00× | 2.16× |
| 3a_gradient_anisotropic_diffusion | 22.9 | 23.0 | 12.2 | 1.00× | 1.88× |
| 3b_bone_labelmap_threshold_cc_relabel | 3.164 | 3.168 | 3.106 | 1.00× | 1.02× |
| 3c_label_intensity_statistics | 11.4 | 11.4 | 8.895 | 1.00× | 1.28× |
| 3c_label_shape_statistics | 2.368 | 2.383 | 1.654 | 0.99× | 1.43× |
| 3d_histogram_vtkImageAccumulate | 0.951 | 0.935 | 1.096 | 1.02× | 0.87× |
| 3d_image_statistics_sitk | 1.755 | 1.767 | 1.745 | 0.99× | 1.01× |
| 3e_flying_edges | 1.052 | 1.050 | 0.785 | 1.00× | 1.34× |
| 3e_windowed_sinc_smoothing | 4.404 | 4.407 | 5.083 | 1.00× | 0.87× |
| 3e_polydata_normals | 3.931 | 3.969 | 2.693 | 0.99× | 1.46× |
| 3f_polydata_to_labelmap_stencil | 106.9 | 102.6 | 62.7 | 1.04× | 1.71× |
| **Geometric mean** | | | | **1.00×** | **1.31×** |

CPU load from other processes during the run (% of machine, mean / max): x64 1.1 / 4.2, arm64ec 1.0 / 2.5, arm64 0.9 / 3.4

## 3. C++ algorithms (SimpleITK, VTK) — 12 threads

| Task | x64 (s) | arm64ec (s) | arm64 (s) | arm64ec speed-up | arm64 speed-up |
| --- | ---: | ---: | ---: | ---: | ---: |
| 3a_curvature_anisotropic_diffusion | 8.237 | 8.551 | 4.178 | 0.96× | 1.97× |
| 3a_gradient_anisotropic_diffusion | 6.431 | 6.641 | 3.799 | 0.97× | 1.69× |
| 3b_bone_labelmap_threshold_cc_relabel | 0.748 | 0.759 | 0.625 | 0.98× | 1.20× |
| 3c_label_intensity_statistics | 2.008 | 2.419 | 1.545 | 0.83× | 1.30× |
| 3c_label_shape_statistics | 1.199 | 1.266 | 0.726 | 0.95× | 1.65× |
| 3d_histogram_vtkImageAccumulate | 1.100 | 1.091 | 1.220 | 1.01× | 0.90× |
| 3d_image_statistics_sitk | 0.204 | 0.199 | 0.181 | 1.03× | 1.13× |
| 3e_flying_edges | 0.163 | 0.170 | 0.126 | 0.96× | 1.29× |
| 3e_windowed_sinc_smoothing | 1.483 | 1.424 | 1.140 | 1.04× | 1.30× |
| 3e_polydata_normals | 2.921 | 2.886 | 2.110 | 1.01× | 1.38× |
| 3f_polydata_to_labelmap_stencil | 17.8 | 17.9 | 10.1 | 0.99× | 1.76× |
| **Geometric mean** | | | | **0.97×** | **1.38×** |

CPU load from other processes during the run (% of machine, mean / max): x64 1.1 / 2.5, arm64ec 1.5 / 8.6, arm64 1.9 / 5.3

## 4. C++ visualization (VTK, offscreen 1920x1080) — 1 thread

| Task | x64 (s) | arm64ec (s) | arm64 (s) | arm64ec speed-up | arm64 speed-up |
| --- | ---: | ---: | ---: | ---: | ---: |
| 4a_surface_full_first_frame_case01 | 0.099 | 0.095 | 0.078 | 1.05× | 1.27× |
| 4a_surface_full_360_frames_case01 | 1.084 | 1.484 | 1.024 | 0.73× | 1.06× |
| 4a_surface_decimated_first_frame_case01 | 0.071 | 0.068 | 0.062 | 1.04× | 1.14× |
| 4a_surface_decimated_360_frames_case01 | 0.863 | 0.582 | 0.546 | 1.48× | 1.58× |
| 4b_gpu_volume_first_frame_case01 | 0.196 | 0.203 | 0.136 | 0.97× | 1.44× |
| 4b_gpu_volume_60_frames_case01 | 9.716 | 9.702 | 9.526 | 1.00× | 1.02× |
| 4c_cpu_volume_36_frames_case01 | 56.5 | 56.7 | 43.1 | 1.00× | 1.31× |
| 4a_surface_full_first_frame_case18 | 0.174 | 0.174 | 0.140 | 1.00× | 1.24× |
| 4a_surface_full_360_frames_case18 | 2.319 | 2.196 | 2.183 | 1.06× | 1.06× |
| 4a_surface_decimated_first_frame_case18 | 0.081 | 0.076 | 0.064 | 1.07× | 1.28× |
| 4a_surface_decimated_360_frames_case18 | 0.949 | 1.096 | 1.045 | 0.87× | 0.91× |
| 4b_gpu_volume_first_frame_case18 | 0.846 | 0.844 | 0.510 | 1.00× | 1.66× |
| 4b_gpu_volume_60_frames_case18 | 26.8 | 26.8 | 26.8 | 1.00× | 1.00× |
| **Geometric mean** | | | | **1.01×** | **1.21×** |

CPU load from other processes during the run (% of machine, mean / max): x64 1.7 / 8.1, arm64ec 1.5 / 4.0, arm64 1.5 / 4.0

## 4. C++ visualization (VTK, offscreen 1920x1080) — 12 threads

| Task | x64 (s) | arm64ec (s) | arm64 (s) | arm64ec speed-up | arm64 speed-up |
| --- | ---: | ---: | ---: | ---: | ---: |
| 4a_surface_full_first_frame_case01 | 0.080 | 0.081 | 0.062 | 0.98× | 1.29× |
| 4a_surface_full_360_frames_case01 | 1.028 | 1.148 | 0.928 | 0.90× | 1.11× |
| 4a_surface_decimated_first_frame_case01 | 0.073 | 0.072 | 0.052 | 1.01× | 1.40× |
| 4a_surface_decimated_360_frames_case01 | 0.871 | 0.654 | 0.610 | 1.33× | 1.43× |
| 4b_gpu_volume_first_frame_case01 | 0.190 | 0.153 | 0.142 | 1.24× | 1.34× |
| 4b_gpu_volume_60_frames_case01 | 9.769 | 9.694 | 9.540 | 1.01× | 1.02× |
| 4c_cpu_volume_36_frames_case01 | 10.8 | 10.3 | 8.335 | 1.05× | 1.30× |
| 4a_surface_full_first_frame_case18 | 0.117 | 0.117 | 0.103 | 1.00× | 1.13× |
| 4a_surface_full_360_frames_case18 | 2.271 | 2.443 | 2.170 | 0.93× | 1.05× |
| 4a_surface_decimated_first_frame_case18 | 0.095 | 0.069 | 0.058 | 1.37× | 1.63× |
| 4a_surface_decimated_360_frames_case18 | 1.053 | 1.210 | 1.167 | 0.87× | 0.90× |
| 4b_gpu_volume_first_frame_case18 | 0.903 | 0.817 | 0.601 | 1.11× | 1.50× |
| 4b_gpu_volume_60_frames_case18 | 26.8 | 26.8 | 26.5 | 1.00× | 1.01× |
| **Geometric mean** | | | | **1.05×** | **1.22×** |

CPU load from other processes during the run (% of machine, mean / max): x64 1.8 / 4.0, arm64ec 1.9 / 3.8, arm64 1.9 / 4.7

## 5. AI segmentation (CPU) — 12 threads

| Task | x64 (s) | arm64ec (s) | arm64 (s) | arm64ec speed-up | arm64 speed-up |
| --- | ---: | ---: | ---: | ---: | ---: |
| 5a_totalseg_fast_case01 | 38.2 | 37.9 | 105.1 | 1.01× | 0.36× |
| 5a_totalseg_fast_case02 | 30.6 | 30.0 | 99.5 | 1.02× | 0.31× |
| 5a_totalseg_fast_case03 | 33.6 | 31.0 | 99.7 | 1.08× | 0.34× |
| 5a_totalseg_fast_case11 | 30.9 | 30.5 | 95.8 | 1.01× | 0.32× |
| 5a_totalseg_fast_case13 | 21.4 | 21.2 | 54.2 | 1.01× | 0.39× |
| 5b_totalseg_full_case01 | 468.2 | 480.9 | 3036.8 | 0.97× | 0.15× |
| 5c_monai_abdominal-organs-3mm-v2.0.0_case01 | 21.1 | 21.6 | 95.6 | 0.98× | 0.22× |
| 5c_monai_abdominal-organs-3mm-v2.0.0_case02 | 31.9 | 31.4 | 139.8 | 1.02× | 0.23× |
| 5c_monai_abdominal-organs-3mm-v2.0.0_case03 | 23.2 | 21.8 | 95.1 | 1.06× | 0.24× |
| 5c_monai_abdominal-organs-3mm-v2.0.0_case11 | 19.9 | 20.8 | 93.3 | 0.96× | 0.21× |
| 5c_monai_abdominal-organs-3mm-v2.0.0_case13 | 8.539 | 8.529 | 26.7 | 1.00× | 0.32× |
| **Geometric mean** | | | | **1.01×** | **0.27×** |

CPU load from other processes during the run (% of machine, mean / max): x64 2.3 / 8.2, arm64ec 2.2 / 6.0, arm64 2.5 / 19.5

## 6. ONNX Runtime vs PyTorch, MONAIAuto3DSeg network (CPU) — 12 threads

| Task | x64 (s) | arm64ec (s) | arm64 (s) | arm64ec speed-up | arm64 speed-up |
| --- | ---: | ---: | ---: | ---: | ---: |
| 6a_patch_torch_t1 | 19.3 | 19.4 | 35.8 | 0.99× | 0.54× |
| 6a_patch_onnxruntime_t1 | 17.1 | 17.4 | 12.5 | 0.98× | 1.37× |
| 6a_patch_torch_t12 | 3.369 | 3.328 | 22.4 | 1.01× | 0.15× |
| 6a_patch_onnxruntime_t12 | 4.590 | 4.646 | 2.628 | 0.99× | 1.75× |
| 6b_sliding_window_torch_case01 | 15.9 | 16.0 | 91.9 | 1.00× | 0.17× |
| 6b_sliding_window_onnxruntime_case01 | 20.1 | 20.6 | 11.0 | 0.98× | 1.84× |
| 6b_sliding_window_torch_case02 | 37.6 | 37.3 | 204.5 | 1.01× | 0.18× |
| 6b_sliding_window_onnxruntime_case02 | 43.1 | 42.8 | 28.6 | 1.01× | 1.51× |
| 6b_sliding_window_torch_case03 | 37.7 | 37.6 | 203.9 | 1.00× | 0.18× |
| 6b_sliding_window_onnxruntime_case03 | 43.9 | 43.1 | 28.1 | 1.02× | 1.56× |
| 6b_sliding_window_torch_case11 | 16.6 | 17.5 | 91.1 | 0.95× | 0.18× |
| 6b_sliding_window_onnxruntime_case11 | 20.6 | 19.6 | 10.8 | 1.05× | 1.91× |
| 6b_sliding_window_torch_case13 | 17.5 | 16.0 | 91.7 | 1.09× | 0.19× |
| 6b_sliding_window_onnxruntime_case13 | 21.8 | 19.8 | 10.9 | 1.10× | 2.00× |
| 6a_patch_npu_qnn_fp16 | – | – | 0.740 | – | – |
| 6b_sliding_window_npu_qnn_fp16_case01 | – | – | 3.237 | – | – |
| 6b_sliding_window_npu_qnn_fp16_case02 | – | – | 6.932 | – | – |
| 6b_sliding_window_npu_qnn_fp16_case03 | – | – | 6.939 | – | – |
| 6b_sliding_window_npu_qnn_fp16_case11 | – | – | 3.364 | – | – |
| 6b_sliding_window_npu_qnn_fp16_case13 | – | – | 3.126 | – | – |
| **Geometric mean** | | | | **1.01×** | **0.59×** |

CPU load from other processes during the run (% of machine, mean / max): x64 1.6 / 8.2, arm64ec 1.6 / 6.4, arm64 1.8 / 9.8

## Output checks

Rendered last frames, mean absolute pixel difference from x64 (0–255):

| Image | arm64ec | arm64 |
| --- | ---: | ---: |
| cpu_volume-case01-last | 0.0 | 0.0 |
| gpu_volume-case01-last | 0.0 | 0.0 |
| gpu_volume-case18-last | 0.0 | 0.0 |
| surface_decimated-case01-last | 0.0 | 0.0 |
| surface_decimated-case18-last | 0.0 | 0.0 |
| surface_full-case01-last | 0.0 | 0.0 |
| surface_full-case18-last | 0.0 | 0.0 |

AI segmentations, Dice per label against x64 (mean / minimum over labels):

| Segmentation | arm64ec | arm64 |
| --- | ---: | ---: |
| case01-monai-abdominal-organs-3mm-v2 | 1.0 / 1.0 | 1.0 / 1.0 |
| case01-totalseg-fast | 1.0 / 1.0 | 1.0 / 1.0 |
| case01-totalseg-full | 1.0 / 1.0 | 1.0 / 1.0 |
| case02-monai-abdominal-organs-3mm-v2 | 1.0 / 1.0 | 1.0 / 1.0 |
| case02-totalseg-fast | 1.0 / 1.0 | 1.0 / 1.0 |
| case03-monai-abdominal-organs-3mm-v2 | 1.0 / 1.0 | 1.0 / 1.0 |
| case03-totalseg-fast | 1.0 / 1.0 | 1.0 / 1.0 |
| case11-monai-abdominal-organs-3mm-v2 | 1.0 / 1.0 | 1.0 / 1.0 |
| case11-totalseg-fast | 1.0 / 1.0 | 1.0 / 1.0 |
| case13-monai-abdominal-organs-3mm-v2 | 1.0 / 1.0 | 1.0 / 1.0 |
| case13-totalseg-fast | 1.0 / 1.0 | 1.0 / 1.0 |

Task signatures that differ from x64 (relative tolerance 0.002):

- onnx t12 6b_sliding_window_onnxruntime_case13 [arm64]: /fg 64378 != 64647
