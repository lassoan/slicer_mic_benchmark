# Replicates: win_arm64_cpu_snapdragon-x1e80100_12x3.42GHz_ram_32GB_gpu_adreno-x1-85_npu_hexagon_20261123_970 vs win_arm64_cpu_snapdragon-x1e80100_12x3.42GHz_ram_32GB_gpu_adreno-x1-85_npu_hexagon_20261123_754

Geometric-mean speed-up vs x64 in each replicate:

| Section | Threads | arm64ec (20261123_970) | arm64ec (20261123_754) | arm64 (20261123_970) | arm64 (20261123_754) |
| --- | ---: | ---: | ---: | ---: | ---: |
| ai | 12 | 1.01× | 0.81× | 0.27× | 0.24× |
| cpp | 1 | 1.00× | 0.99× | 1.31× | 1.39× |
| cpp | 12 | 0.97× | 0.97× | 1.38× | 1.32× |
| io | 12 | 1.28× | 1.25× | 1.39× | 1.38× |
| numpy | 1 | 0.99× | 0.97× | 1.41× | 1.45× |
| numpy | 12 | 1.01× | 1.01× | 1.38× | 1.27× |
| onnx | 12 | 1.01× | 1.01× | 0.59× | 0.59× |
| render | 1 | 1.01× | 0.99× | 1.21× | 1.17× |
| render | 12 | 1.05× | 0.98× | 1.22× | 1.21× |
| startup | 0 | 1.08× | 1.06× | 1.43× | 1.43× |

Tasks whose median time differs by more than 15% between the replicates:

| Section | Threads | Env | Task | 20261123_970 (s) | 20261123_754 (s) | ratio |
| --- | ---: | --- | --- | ---: | ---: | ---: |
| ai | 12 | x64 | 5c_monai_abdominal-organs-3mm-v2.0.0_case02 | 31.939 | 27.479 | 1.16 |
| ai | 12 | arm64ec | 5b_totalseg_full_case01 | 480.941 | 559.569 | 0.86 |
| ai | 12 | arm64ec | 5c_monai_abdominal-organs-3mm-v2.0.0_case01 | 21.554 | 26.842 | 0.80 |
| ai | 12 | arm64ec | 5c_monai_abdominal-organs-3mm-v2.0.0_case02 | 31.450 | 42.199 | 0.75 |
| ai | 12 | arm64ec | 5c_monai_abdominal-organs-3mm-v2.0.0_case03 | 21.769 | 32.053 | 0.68 |
| ai | 12 | arm64ec | 5c_monai_abdominal-organs-3mm-v2.0.0_case11 | 20.838 | 33.737 | 0.62 |
| ai | 12 | arm64ec | 5c_monai_abdominal-organs-3mm-v2.0.0_case13 | 8.529 | 12.069 | 0.71 |
| ai | 12 | arm64 | 5a_totalseg_fast_case01 | 105.062 | 128.210 | 0.82 |
| ai | 12 | arm64 | 5a_totalseg_fast_case02 | 99.468 | 126.858 | 0.78 |
| ai | 12 | arm64 | 5a_totalseg_fast_case03 | 99.712 | 136.260 | 0.73 |
| ai | 12 | arm64 | 5a_totalseg_fast_case13 | 54.195 | 62.703 | 0.86 |
| cpp | 1 | x64 | 3c_label_intensity_statistics | 11.426 | 13.338 | 0.86 |
| cpp | 1 | x64 | 3d_histogram_vtkImageAccumulate | 0.951 | 1.103 | 0.86 |
| cpp | 1 | x64 | 3d_image_statistics_sitk | 1.755 | 2.066 | 0.85 |
| cpp | 1 | arm64ec | 3a_curvature_anisotropic_diffusion | 35.988 | 45.888 | 0.78 |
| cpp | 1 | arm64ec | 3a_gradient_anisotropic_diffusion | 22.967 | 28.659 | 0.80 |
| cpp | 1 | arm64ec | 3b_bone_labelmap_threshold_cc_relabel | 3.168 | 4.041 | 0.78 |
| cpp | 1 | arm64ec | 3d_histogram_vtkImageAccumulate | 0.935 | 1.201 | 0.78 |
| cpp | 12 | arm64ec | 3d_image_statistics_sitk | 0.199 | 0.236 | 0.84 |
| cpp | 12 | arm64 | 3d_image_statistics_sitk | 0.181 | 0.216 | 0.84 |
| cpp | 12 | arm64 | 3e_polydata_normals | 2.110 | 2.469 | 0.85 |
| numpy | 12 | arm64 | 2f_svd_2000 | 2.110 | 2.911 | 0.72 |
| numpy | 12 | arm64 | 2f_landmark_fit_lstsq_kabsch | 0.011 | 0.016 | 0.67 |
| render | 1 | x64 | 4a_surface_decimated_360_frames_case01 | 0.863 | 0.586 | 1.47 |
| render | 1 | x64 | 4b_gpu_volume_first_frame_case01 | 0.196 | 0.155 | 1.27 |
| render | 1 | x64 | 4a_surface_full_360_frames_case18 | 2.319 | 2.926 | 0.79 |
| render | 1 | arm64ec | 4a_surface_full_first_frame_case01 | 0.095 | 0.115 | 0.83 |
| render | 1 | arm64ec | 4a_surface_full_360_frames_case01 | 1.484 | 1.087 | 1.37 |
| render | 1 | arm64 | 4a_surface_decimated_first_frame_case01 | 0.062 | 0.053 | 1.17 |
| render | 1 | arm64 | 4a_surface_decimated_360_frames_case01 | 0.546 | 0.628 | 0.87 |
| render | 12 | x64 | 4a_surface_decimated_360_frames_case01 | 0.871 | 0.641 | 1.36 |
| render | 12 | x64 | 4a_surface_decimated_first_frame_case18 | 0.095 | 0.071 | 1.34 |
| render | 12 | arm64ec | 4a_surface_decimated_360_frames_case01 | 0.654 | 0.892 | 0.73 |
| render | 12 | arm64ec | 4b_gpu_volume_first_frame_case01 | 0.153 | 0.180 | 0.85 |
| render | 12 | arm64 | 4a_surface_full_first_frame_case18 | 0.103 | 0.090 | 1.15 |
| render | 12 | arm64 | 4a_surface_decimated_360_frames_case18 | 1.167 | 0.999 | 1.17 |
