"""Section 2: vectorized Python algorithms (numpy, scipy) on the CT volumes of config.COMPUTE_CASES.

Each task processes all compute cases; signatures are rounded so they can be compared across environments.
"""

import math

import nrrd
import numpy as np
import scipy.fft
import scipy.linalg
import scipy.ndimage as ndi

from bench import config, harness

DEFAULT_REPEATS = 3


def load_case(case):
    data, header = nrrd.read(str(config.NRRD_DIR / f"{case}.nrrd"))
    arr = np.ascontiguousarray(data.T)  # (z, y, x) int16
    spacing_xyz = np.linalg.norm(np.asarray(header["space directions"], dtype=float), axis=1)
    return arr, tuple(spacing_xyz[::-1])  # spacing in (z, y, x) order


def center_crop(a, size):
    sl = []
    for n in a.shape:
        s = min(size, n)
        start = (n - s) // 2
        sl.append(slice(start, start + s))
    return a[tuple(sl)]


def r(x, nd=4):
    """Round for signatures (relative precision)."""
    x = float(x)
    if x == 0 or not math.isfinite(x):
        return x
    return round(x, nd - int(math.floor(math.log10(abs(x)))) - 1)


def run(runner, cases=None, tasks=None, threads=1, env="unknown"):
    cases = cases or config.COMPUTE_CASES
    harness.set_library_threads(threads)
    vols = {c: load_case(c) for c in cases}
    vols_f = {c: v.astype(np.float32) for c, (v, _) in vols.items()}

    def want(name):
        return tasks is None or any(name.startswith(t) for t in tasks)

    # --- 2a element-wise
    if want("2a"):
        def t_window():
            out = {}
            lo = config.LEVEL - config.WINDOW / 2
            for c, (v, _) in vols.items():
                wl = np.clip((v.astype(np.float32) - lo) * (255.0 / config.WINDOW), 0, 255).astype(np.uint8)
                out[c] = int(wl.sum(dtype=np.int64))
            return out
        runner.run("2a_window_level_uint8", t_window)

        def t_zscore():
            out = {}
            for c, vf in vols_f.items():
                z = (vf - vf.mean()) / vf.std()
                z = np.clip(z, -3, 3)
                out[c] = r(np.abs(z).sum(dtype=np.float64))
            return out
        runner.run("2a_zscore_clip_float32", t_zscore)

        rng = np.random.default_rng(config.SYNTH_SEED)
        synth = rng.standard_normal((config.SYNTH_SIZE,) * 3, dtype=np.float32)

        def t_synth():
            y = np.sqrt(np.abs(synth)) * 2.0 + np.exp(-synth * synth) - np.tanh(synth)
            return {"sum": r(y.sum(dtype=np.float64))}
        runner.run("2a_elementwise_synthetic_512cubed", t_synth)
        del synth

    # --- 2b reductions
    if want("2b"):
        def t_hist():
            out = {}
            for c, (v, _) in vols.items():
                h, _ = np.histogram(v, bins=config.HIST_BINS, range=config.HIST_RANGE)
                out[c] = int(h.argmax())
            return out
        runner.run("2b_histogram", t_hist)

        def t_pct():
            return {c: [float(x) for x in np.percentile(v, [1, 50, 99])] for c, (v, _) in vols.items()}
        runner.run("2b_percentiles", t_pct)

        def t_unique():
            return {c: len(np.unique(v // 100)) for c, (v, _) in vols.items()}
        runner.run("2b_unique", t_unique)

    # --- 2c scipy.ndimage filters
    if want("2c"):
        def t_gauss():
            return {c: r(ndi.gaussian_filter(vf, config.GAUSSIAN_SIGMA).sum(dtype=np.float64)) for c, vf in vols_f.items()}
        runner.run("2c_gaussian_filter", t_gauss)

        def t_median():
            return {c: r(ndi.median_filter(center_crop(vf, config.CROP), config.MEDIAN_SIZE).sum(dtype=np.float64))
                    for c, vf in vols_f.items()}
        runner.run("2c_median_filter_crop", t_median)

        def t_morph():
            out = {}
            for c, (v, _) in vols.items():
                m = v > config.BODY_THRESHOLD
                d = ndi.binary_dilation(m, iterations=config.MORPH_ITERATIONS)
                e = ndi.binary_erosion(d, iterations=config.MORPH_ITERATIONS)
                out[c] = int(e.sum())
            return out
        runner.run("2c_binary_dilate_erode", t_morph)

    # --- 2d labeling and distance
    if want("2d"):
        def t_label_edt():
            out = {}
            for c, (v, spacing) in vols.items():
                lab, n = ndi.label(v > config.BODY_THRESHOLD)
                sizes = np.bincount(lab.ravel())
                sizes[0] = 0
                body = lab == sizes.argmax()
                # Distance transform on the centered CROP^3 region (full volumes take minutes)
                dist = ndi.distance_transform_edt(center_crop(body, config.CROP), sampling=spacing)
                out[c] = [int(n), r(dist.max())]
            return out
        runner.run("2d_label_largest_component_edt", t_label_edt)

    # --- 2e resampling
    if want("2e"):
        def t_zoom():
            out = {}
            for c, vf in vols_f.items():
                spacing = vols[c][1]
                z = ndi.zoom(vf, [s / config.RESAMPLE_SPACING for s in spacing], order=1)
                out[c] = list(z.shape)
            return out
        runner.run("2e_zoom_isotropic_1.5mm", t_zoom)

        def t_affine():
            a = math.radians(config.ROTATION_DEG)
            rot = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
            out = {}
            for c, vf in vols_f.items():
                center = np.array(vf.shape) / 2
                offset = center - rot @ center
                res = ndi.affine_transform(vf, rot, offset=offset, order=1, cval=-1024)
                out[c] = r(res.mean(dtype=np.float64))
            return out
        runner.run("2e_affine_rotation", t_affine)

    # --- 2f linear algebra
    if want("2f"):
        def t_pca():
            out = {}
            for c, (v, spacing) in vols.items():
                pts = np.argwhere(v > config.BONE_THRESHOLD).astype(np.float64) * np.array(spacing)
                pts -= pts.mean(axis=0)
                s = np.linalg.svd(pts, full_matrices=False, compute_uv=False)
                out[c] = [r(x) for x in s]
            return out
        runner.run("2f_pca_bone_points_svd", t_pca)

        rng = np.random.default_rng(config.SYNTH_SEED)
        m = rng.standard_normal((config.SVD_SIZE, config.SVD_SIZE))

        def t_svd():
            s = np.linalg.svd(m, compute_uv=True)[1]
            return {"smax": r(s[0]), "smin": r(s[-1])}
        runner.run("2f_svd_2000", t_svd)

        def t_matmul():
            p = m @ m.T
            return {"trace": r(np.trace(p))}
        runner.run("2f_matmul_2000", t_matmul)

        src = rng.standard_normal((config.LSTSQ_POINTS, 3)) * 100
        true_affine = np.array([[0.98, -0.1, 0.05, 3.0], [0.1, 1.02, 0.0, -7.0], [-0.05, 0.02, 0.99, 12.0]])
        dst = src @ true_affine[:, :3].T + true_affine[:, 3] + rng.standard_normal(src.shape) * 0.5

        def t_lstsq():
            # Affine fit with least squares and rigid fit with SVD (Kabsch), repeated as in iterative registration
            for _ in range(20):
                a = np.hstack([src, np.ones((len(src), 1))])
                sol, *_ = np.linalg.lstsq(a, dst, rcond=None)
                cs, cd = src.mean(0), dst.mean(0)
                u, _, vt = np.linalg.svd((src - cs).T @ (dst - cd))
                rot = vt.T @ u.T
            return {"affine00": r(sol[0, 0]), "rot_det": r(np.linalg.det(rot))}
        runner.run("2f_landmark_fit_lstsq_kabsch", t_lstsq)

        tensors = rng.standard_normal((config.EIGH_BATCH, 3, 3)).astype(np.float32)
        tensors = tensors @ tensors.transpose(0, 2, 1)

        def t_eigh():
            w = np.linalg.eigh(tensors)[0]
            return {"mean_max_eig": r(w[:, -1].mean(dtype=np.float64))}
        runner.run("2f_eigh_batch_3x3", t_eigh)

    # --- 2g FFT
    if want("2g"):
        def t_fft():
            out = {}
            for c, vf in vols_f.items():
                a = center_crop(vf, config.CROP)
                b = np.roll(a, config.FFT_SHIFT, axis=(0, 1, 2))
                fa = scipy.fft.rfftn(a, workers=threads)
                fb = scipy.fft.rfftn(b, workers=threads)
                cross = fb * np.conj(fa)
                cross /= np.abs(cross) + 1e-12
                corr = scipy.fft.irfftn(cross, s=a.shape, workers=threads)
                peak = np.unravel_index(np.argmax(corr), corr.shape)
                shift = [int(p if p <= n // 2 else p - n) for p, n in zip(peak, a.shape)]
                out[c] = shift
            return out
        runner.run("2g_fft_phase_correlation", t_fft)

    return {"cases": cases}
