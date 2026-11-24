# Benchmark results

Machine: Snapdragon(R) X 12-core X1E80100 @ 3.40 GHz, 12 logical CPUs, 31.6 GB RAM, Windows 10.0.26300.

Times are medians in seconds. Speed-up = time in x64 (emulated) / time in the environment; higher is better.
Environments: **x64** = x64 Python and x64 packages, emulated (Prism); **arm64ec** = ARM64EC Python (native interpreter) with the same x64 packages (emulated); **arm64** = native ARM64 Python and packages.

## Startup and import time

| Task | x64 (s) | arm64ec (s) | arm64 (s) | arm64ec speed-up | arm64 speed-up |
| --- | ---: | ---: | ---: | ---: | ---: |
| python_startup | 0.045 | 0.043 | 0.026 | 1.04× | 1.73× |
| import_numpy_scipy | 0.475 | 0.434 | 0.349 | 1.09× | 1.36× |
| import_simpleitk | 0.207 | 0.192 | 0.145 | 1.08× | 1.43× |
| import_vtk_all | 0.810 | 0.790 | 0.606 | 1.02× | 1.34× |
| import_torch | 1.749 | 1.602 | 1.189 | 1.09× | 1.47× |
| import_bench_stack | 1.412 | 1.337 | 1.085 | 1.06× | 1.30× |
| **Geometric mean** | | | | **1.06×** | **1.43×** |

## 1. File I/O and DICOM geometry — 12 threads

| Task | x64 (s) | arm64ec (s) | arm64 (s) | arm64ec speed-up | arm64 speed-up |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1a_read_dicom_headers_sitk | 11.5 | 11.7 | 7.306 | 0.98× | 1.57× |
| 1a_read_dicom_headers_pydicom | 2.766 | 2.752 | 1.821 | 1.00× | 1.52× |
| 1b_check_geometry_pure_python_x50 | 0.883 | 0.694 | 0.483 | 1.27× | 1.83× |
| 1c_read_dicom_volumes_sitk | 12.9 | 14.0 | 8.401 | 0.92× | 1.54× |
| 1d_write_nrrd_raw | 2.614 | 2.434 | 1.808 | 1.07× | 1.45× |
| 1d_write_nrrd_gzip | 40.8 | 14.3 | 31.6 | 2.86× | 1.29× |
| 1e_write_nifti | 1.397 | 1.505 | 1.089 | 0.93× | 1.28× |
| 1e_write_nifti_gz | 34.4 | 12.6 | 27.1 | 2.73× | 1.27× |
| 1f_read_nrrd_raw | 1.407 | 1.355 | 1.034 | 1.04× | 1.36× |
| 1f_read_nrrd_gzip | 11.8 | 8.496 | 10.5 | 1.39× | 1.13× |
| 1f_read_nifti_raw_dataobj | 1.535 | 1.554 | 1.052 | 0.99× | 1.46× |
| 1f_read_nifti_gz_dataobj | 10.2 | 8.281 | 8.251 | 1.23× | 1.24× |
| 1f_read_nifti_gz_fdata_float32 | 11.9 | 9.929 | 9.773 | 1.19× | 1.21× |
| **Geometric mean** | | | | **1.25×** | **1.38×** |

## 2. Vectorized Python algorithms (numpy, scipy) — 1 thread

| Task | x64 (s) | arm64ec (s) | arm64 (s) | arm64ec speed-up | arm64 speed-up |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2a_window_level_uint8 | 1.971 | 2.092 | 1.827 | 0.94× | 1.08× |
| 2a_zscore_clip_float32 | 1.983 | 2.027 | 1.811 | 0.98× | 1.10× |
| 2a_elementwise_synthetic_512cubed | 2.708 | 2.807 | 1.444 | 0.96× | 1.88× |
| 2b_histogram | 3.052 | 3.411 | 1.685 | 0.89× | 1.81× |
| 2b_percentiles | 1.722 | 1.761 | 1.349 | 0.98× | 1.28× |
| 2b_unique | 1.910 | 2.109 | 0.891 | 0.91× | 2.14× |
| 2c_gaussian_filter | 21.7 | 24.6 | 19.1 | 0.88× | 1.14× |
| 2c_median_filter_crop | 20.5 | 19.9 | 19.4 | 1.03× | 1.05× |
| 2c_binary_dilate_erode | 5.955 | 6.436 | 3.331 | 0.93× | 1.79× |
| 2d_label_largest_component_edt | 19.4 | 20.3 | 19.0 | 0.96× | 1.02× |
| 2e_zoom_isotropic_1.5mm | 2.288 | 2.448 | 1.551 | 0.93× | 1.48× |
| 2e_affine_rotation | 18.6 | 20.6 | 11.4 | 0.91× | 1.63× |
| 2f_pca_bone_points_svd | 1.261 | 1.258 | 0.930 | 1.00× | 1.36× |
| 2f_svd_2000 | 3.724 | 3.437 | 2.609 | 1.08× | 1.43× |
| 2f_matmul_2000 | 0.268 | 0.260 | 0.151 | 1.03× | 1.78× |
| 2f_landmark_fit_lstsq_kabsch | 0.024 | 0.024 | 0.010 | 1.00× | 2.47× |
| 2f_eigh_batch_3x3 | 1.358 | 1.347 | 0.948 | 1.01× | 1.43× |
| 2g_fft_phase_correlation | 1.468 | 1.463 | 1.259 | 1.00× | 1.17× |
| **Geometric mean** | | | | **0.97×** | **1.45×** |

## 2. Vectorized Python algorithms (numpy, scipy) — 12 threads

| Task | x64 (s) | arm64ec (s) | arm64 (s) | arm64ec speed-up | arm64 speed-up |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2a_window_level_uint8 | 1.981 | 1.985 | 1.830 | 1.00× | 1.08× |
| 2a_zscore_clip_float32 | 1.951 | 1.925 | 1.787 | 1.01× | 1.09× |
| 2a_elementwise_synthetic_512cubed | 2.717 | 2.718 | 1.458 | 1.00× | 1.86× |
| 2b_histogram | 3.138 | 2.720 | 1.697 | 1.15× | 1.85× |
| 2b_percentiles | 1.724 | 1.699 | 1.348 | 1.01× | 1.28× |
| 2b_unique | 1.910 | 1.880 | 0.902 | 1.02× | 2.12× |
| 2c_gaussian_filter | 21.2 | 21.1 | 22.0 | 1.00× | 0.96× |
| 2c_median_filter_crop | 20.2 | 19.8 | 20.3 | 1.02× | 1.00× |
| 2c_binary_dilate_erode | 5.838 | 5.842 | 3.748 | 1.00× | 1.56× |
| 2d_label_largest_component_edt | 19.5 | 19.9 | 19.3 | 0.98× | 1.01× |
| 2e_zoom_isotropic_1.5mm | 2.239 | 2.231 | 1.765 | 1.00× | 1.27× |
| 2e_affine_rotation | 17.8 | 18.4 | 12.8 | 0.97× | 1.39× |
| 2f_pca_bone_points_svd | 1.237 | 1.235 | 0.983 | 1.00× | 1.26× |
| 2f_svd_2000 | 1.448 | 1.439 | 2.911 | 1.01× | 0.50× |
| 2f_matmul_2000 | 0.043 | 0.043 | 0.041 | 1.00× | 1.03× |
| 2f_landmark_fit_lstsq_kabsch | 0.025 | 0.026 | 0.016 | 0.95× | 1.57× |
| 2f_eigh_batch_3x3 | 1.367 | 1.399 | 1.114 | 0.98× | 1.23× |
| 2g_fft_phase_correlation | 1.445 | 1.451 | 0.687 | 1.00× | 2.10× |
| **Geometric mean** | | | | **1.01×** | **1.27×** |

## 3. C++ algorithms (SimpleITK, VTK) — 1 thread

| Task | x64 (s) | arm64ec (s) | arm64 (s) | arm64ec speed-up | arm64 speed-up |
| --- | ---: | ---: | ---: | ---: | ---: |
| 3a_curvature_anisotropic_diffusion | 39.4 | 45.9 | 17.8 | 0.86× | 2.22× |
| 3a_gradient_anisotropic_diffusion | 24.1 | 28.7 | 12.7 | 0.84× | 1.90× |
| 3b_bone_labelmap_threshold_cc_relabel | 3.457 | 4.041 | 3.170 | 0.86× | 1.09× |
| 3c_label_intensity_statistics | 13.3 | 13.0 | 9.205 | 1.02× | 1.45× |
| 3c_label_shape_statistics | 2.691 | 2.645 | 1.867 | 1.02× | 1.44× |
| 3d_histogram_vtkImageAccumulate | 1.103 | 1.201 | 1.082 | 0.92× | 1.02× |
| 3d_image_statistics_sitk | 2.066 | 1.813 | 1.752 | 1.14× | 1.18× |
| 3e_flying_edges | 1.173 | 1.040 | 0.788 | 1.13× | 1.49× |
| 3e_windowed_sinc_smoothing | 4.942 | 4.415 | 5.196 | 1.12× | 0.95× |
| 3e_polydata_normals | 4.176 | 3.752 | 2.933 | 1.11× | 1.42× |
| 3f_polydata_to_labelmap_stencil | 99.1 | 104.9 | 63.8 | 0.94× | 1.55× |
| **Geometric mean** | | | | **0.99×** | **1.39×** |

## 3. C++ algorithms (SimpleITK, VTK) — 12 threads

| Task | x64 (s) | arm64ec (s) | arm64 (s) | arm64ec speed-up | arm64 speed-up |
| --- | ---: | ---: | ---: | ---: | ---: |
| 3a_curvature_anisotropic_diffusion | 8.296 | 8.760 | 4.189 | 0.95× | 1.98× |
| 3a_gradient_anisotropic_diffusion | 6.631 | 6.634 | 3.842 | 1.00× | 1.73× |
| 3b_bone_labelmap_threshold_cc_relabel | 0.763 | 0.837 | 0.642 | 0.91× | 1.19× |
| 3c_label_intensity_statistics | 2.094 | 2.249 | 1.620 | 0.93× | 1.29× |
| 3c_label_shape_statistics | 1.154 | 1.134 | 0.791 | 1.02× | 1.46× |
| 3d_histogram_vtkImageAccumulate | 1.112 | 1.133 | 1.250 | 0.98× | 0.89× |
| 3d_image_statistics_sitk | 0.206 | 0.236 | 0.216 | 0.87× | 0.95× |
| 3e_flying_edges | 0.172 | 0.170 | 0.127 | 1.01× | 1.35× |
| 3e_windowed_sinc_smoothing | 1.410 | 1.536 | 1.181 | 0.92× | 1.19× |
| 3e_polydata_normals | 3.017 | 2.946 | 2.469 | 1.02× | 1.22× |
| 3f_polydata_to_labelmap_stencil | 16.6 | 16.3 | 9.758 | 1.02× | 1.71× |
| **Geometric mean** | | | | **0.97×** | **1.32×** |

## 4. C++ visualization (VTK, offscreen 1920x1080) — 1 thread

| Task | x64 (s) | arm64ec (s) | arm64 (s) | arm64ec speed-up | arm64 speed-up |
| --- | ---: | ---: | ---: | ---: | ---: |
| 4a_surface_full_first_frame_case01 | 0.110 | 0.115 | 0.079 | 0.96× | 1.39× |
| 4a_surface_full_360_frames_case01 | 1.055 | 1.087 | 0.999 | 0.97× | 1.06× |
| 4a_surface_decimated_first_frame_case01 | 0.074 | 0.065 | 0.053 | 1.14× | 1.40× |
| 4a_surface_decimated_360_frames_case01 | 0.586 | 0.626 | 0.628 | 0.94× | 0.93× |
| 4b_gpu_volume_first_frame_case01 | 0.155 | 0.198 | 0.137 | 0.78× | 1.13× |
| 4b_gpu_volume_60_frames_case01 | 9.578 | 9.622 | 9.601 | 1.00× | 1.00× |
| 4c_cpu_volume_36_frames_case01 | 59.1 | 60.2 | 42.9 | 0.98× | 1.38× |
| 4a_surface_full_first_frame_case18 | 0.168 | 0.171 | 0.152 | 0.98× | 1.11× |
| 4a_surface_full_360_frames_case18 | 2.926 | 2.388 | 2.243 | 1.23× | 1.30× |
| 4a_surface_decimated_first_frame_case18 | 0.086 | 0.076 | 0.064 | 1.14× | 1.34× |
| 4a_surface_decimated_360_frames_case18 | 0.937 | 1.051 | 1.133 | 0.89× | 0.83× |
| 4b_gpu_volume_first_frame_case18 | 0.873 | 0.857 | 0.511 | 1.02× | 1.71× |
| 4b_gpu_volume_60_frames_case18 | 26.0 | 26.6 | 26.1 | 0.98× | 1.00× |
| **Geometric mean** | | | | **0.99×** | **1.17×** |

## 4. C++ visualization (VTK, offscreen 1920x1080) — 12 threads

| Task | x64 (s) | arm64ec (s) | arm64 (s) | arm64ec speed-up | arm64 speed-up |
| --- | ---: | ---: | ---: | ---: | ---: |
| 4a_surface_full_first_frame_case01 | 0.080 | 0.079 | 0.059 | 1.01× | 1.35× |
| 4a_surface_full_360_frames_case01 | 1.049 | 1.172 | 0.938 | 0.89× | 1.12× |
| 4a_surface_decimated_first_frame_case01 | 0.067 | 0.065 | 0.050 | 1.03× | 1.34× |
| 4a_surface_decimated_360_frames_case01 | 0.641 | 0.892 | 0.623 | 0.72× | 1.03× |
| 4b_gpu_volume_first_frame_case01 | 0.192 | 0.180 | 0.141 | 1.07× | 1.36× |
| 4b_gpu_volume_60_frames_case01 | 9.767 | 9.642 | 9.523 | 1.01× | 1.03× |
| 4c_cpu_volume_36_frames_case01 | 10.8 | 10.6 | 7.570 | 1.01× | 1.42× |
| 4a_surface_full_first_frame_case18 | 0.115 | 0.114 | 0.090 | 1.01× | 1.28× |
| 4a_surface_full_360_frames_case18 | 2.459 | 2.350 | 2.211 | 1.05× | 1.11× |
| 4a_surface_decimated_first_frame_case18 | 0.071 | 0.072 | 0.059 | 0.98× | 1.20× |
| 4a_surface_decimated_360_frames_case18 | 1.063 | 1.079 | 0.999 | 0.99× | 1.06× |
| 4b_gpu_volume_first_frame_case18 | 0.827 | 0.808 | 0.524 | 1.02× | 1.58× |
| 4b_gpu_volume_60_frames_case18 | 26.6 | 26.6 | 26.2 | 1.00× | 1.01× |
| **Geometric mean** | | | | **0.98×** | **1.21×** |

## 5. AI segmentation (CPU) — 12 threads

| Task | x64 (s) | arm64ec (s) | arm64 (s) | arm64ec speed-up | arm64 speed-up |
| --- | ---: | ---: | ---: | ---: | ---: |
| 5a_totalseg_fast_case01 | 37.0 | 38.7 | 128.2 | 0.96× | 0.29× |
| 5a_totalseg_fast_case02 | 30.1 | 31.5 | 126.9 | 0.96× | 0.24× |
| 5a_totalseg_fast_case03 | 30.6 | 31.4 | 136.3 | 0.97× | 0.22× |
| 5a_totalseg_fast_case11 | 27.9 | 29.9 | 103.4 | 0.93× | 0.27× |
| 5a_totalseg_fast_case13 | 20.6 | 21.5 | 62.7 | 0.96× | 0.33× |
| 5b_totalseg_full_case01 | 455.2 | 559.6 | 3214.9 | 0.81× | 0.14× |
| 5c_monai_abdominal-organs-3mm-v2.0.0_case01 | 19.2 | 26.8 | 95.1 | 0.71× | 0.20× |
| 5c_monai_abdominal-organs-3mm-v2.0.0_case02 | 27.5 | 42.2 | 139.2 | 0.65× | 0.20× |
| 5c_monai_abdominal-organs-3mm-v2.0.0_case03 | 21.2 | 32.1 | 95.2 | 0.66× | 0.22× |
| 5c_monai_abdominal-organs-3mm-v2.0.0_case11 | 20.4 | 33.7 | 91.8 | 0.60× | 0.22× |
| 5c_monai_abdominal-organs-3mm-v2.0.0_case13 | 9.334 | 12.1 | 26.4 | 0.77× | 0.35× |
| **Geometric mean** | | | | **0.81×** | **0.24×** |

## 6. ONNX Runtime vs PyTorch, MONAIAuto3DSeg network (CPU) — 12 threads

| Task | x64 (s) | arm64ec (s) | arm64 (s) | arm64ec speed-up | arm64 speed-up |
| --- | ---: | ---: | ---: | ---: | ---: |
| 6a_patch_torch_t1 | 19.4 | 19.3 | 35.7 | 1.01× | 0.54× |
| 6a_patch_onnxruntime_t1 | 17.3 | 17.3 | 12.5 | 1.00× | 1.38× |
| 6a_patch_torch_t12 | 3.373 | 3.375 | 22.3 | 1.00× | 0.15× |
| 6a_patch_onnxruntime_t12 | 5.039 | 4.601 | 2.654 | 1.10× | 1.90× |
| 6b_sliding_window_torch_case01 | 16.4 | 16.7 | 91.5 | 0.98× | 0.18× |
| 6b_sliding_window_onnxruntime_case01 | 19.5 | 19.4 | 11.6 | 1.01× | 1.69× |
| 6b_sliding_window_torch_case02 | 37.9 | 37.3 | 205.3 | 1.01× | 0.18× |
| 6b_sliding_window_onnxruntime_case02 | 42.3 | 43.2 | 28.7 | 0.98× | 1.48× |
| 6b_sliding_window_torch_case03 | 38.1 | 37.7 | 204.6 | 1.01× | 0.19× |
| 6b_sliding_window_onnxruntime_case03 | 43.5 | 43.4 | 27.6 | 1.00× | 1.58× |
| 6b_sliding_window_torch_case11 | 17.3 | 16.6 | 91.3 | 1.04× | 0.19× |
| 6b_sliding_window_onnxruntime_case11 | 20.2 | 19.9 | 10.5 | 1.01× | 1.92× |
| 6b_sliding_window_torch_case13 | 16.6 | 16.1 | 91.1 | 1.03× | 0.18× |
| 6b_sliding_window_onnxruntime_case13 | 19.3 | 20.6 | 10.9 | 0.93× | 1.77× |
| 6a_patch_npu_qnn_fp16 | – | – | 0.734 | – | – |
| 6b_sliding_window_npu_qnn_fp16_case01 | – | – | 3.194 | – | – |
| 6b_sliding_window_npu_qnn_fp16_case02 | – | – | 6.927 | – | – |
| 6b_sliding_window_npu_qnn_fp16_case03 | – | – | 6.950 | – | – |
| 6b_sliding_window_npu_qnn_fp16_case11 | – | – | 3.369 | – | – |
| 6b_sliding_window_npu_qnn_fp16_case13 | – | – | 3.106 | – | – |
| **Geometric mean** | | | | **1.01×** | **0.59×** |

CPU load from other processes during the run (% of machine, mean / max): x64 1.3 / 3.8, arm64ec 1.3 / 3.7, arm64 1.7 / 6.5

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
