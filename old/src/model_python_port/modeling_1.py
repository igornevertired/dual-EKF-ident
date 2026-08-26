"""
Порт ``MODELING_1.m`` (один канал БИНС 1 + ГНСС 1 + ОФК 1).

Поток на каждом шаге ``dt``:
1. ``FX1`` + RK4 — истинная траектория ЛА;
2. ``bins1`` — навигационное решение БИНС по зашумлённым ДУС/ДЛУ;
3. ``gnss_1`` — измерения ``[Fi, Lm, H, Vn, Ve, Vh]``;
4. каждые ``mg`` шагов — ``BINS_OFK_2ch`` + ``ofk`` (error-state, 6 каналов).

Логи пишутся на тактах ОФК с прореживанием ``dt_log``.
"""

from __future__ import annotations

import numpy as np

from .autopilot_model import autopilot
from .bins1 import Bins1Sensors, bins1
from .bins_ofk_2ch import build_bins_ofk_6ch_matrices
from .core import rk4_step
from .fx1 import fx1 as fx1_func
from .fx1 import c_gb
from .gnss_1 import gnss_1
from .initsim import initsim
from .ofk import ofk
from .sensor_error_params import gnss_measurement_covariance, ofk_initial_covariance_diagonal

# Обратная связь только по 4 каналам, как в ``MODELING_1.m`` (Fi, Lm, Vn, Ve).
# H и Vh в BINS1 принудительно берутся из эталона траектории.
_OFK_TO_NP = (
    (3, 0),   # Vn
    (4, 2),   # Ve
    (5, 4),   # Fi
    (6, 5),   # Lm
)


def _apply_ofk_feedback(np_bins: np.ndarray, x_corr: np.ndarray) -> None:
    for state_i, np_i in _OFK_TO_NP:
        np_bins[np_i] -= x_corr[state_i]


def run_modeling_1(tmodel=60.0, dt=1e-3, mg=10, dt_log=0.1):
    sim = initsim()
    la = sim["la"]
    htr, vtr, tettr = sim["htr"], sim["vtr"], sim["tettr"]

    x = sim["x0"].copy()
    u0 = sim["u0"].copy()
    ivk = sim["ivk"]

    q = ivk["Qu"].copy()
    cbn = ivk["CBN0"].copy()
    cgb0 = c_gb(x[8], x[6], x[7])
    v_nav0 = cgb0.T @ np.array([x[0], x[1], x[2]])
    np_bins = np.array([v_nav0[0], v_nav0[1], v_nav0[2], x[10], x[12], x[13]], dtype=float)

    sensors = Bins1Sensors(42)
    rng_gnss = np.random.default_rng(123)

    x_ofk = np.zeros(15, dtype=float)
    p_ofk = np.diag(ofk_initial_covariance_diagonal())
    r_gnss = gnss_measurement_covariance(dt)

    step_ofk = mg
    ofk_log_stride = max(1, int(round(dt_log / (dt * mg))))
    n_ofk_epochs = int(tmodel / (dt * mg)) + 1
    n_out = int(np.ceil(n_ofk_epochs / ofk_log_stride)) + 1

    log = {
        "time": np.zeros(n_out),
        "true_h": np.zeros(n_out),
        "true_fi": np.zeros(n_out),
        "true_lam": np.zeros(n_out),
        "true_vn": np.zeros(n_out),
        "true_ve": np.zeros(n_out),
        "true_vh": np.zeros(n_out),
        "bins_h": np.zeros(n_out),
        "bins_fi": np.zeros(n_out),
        "bins_lam": np.zeros(n_out),
        "bins_vn": np.zeros(n_out),
        "bins_ve": np.zeros(n_out),
        "bins_vh": np.zeros(n_out),
        "ofk_h": np.zeros(n_out),
        "ofk_fi": np.zeros(n_out),
        "ofk_lam": np.zeros(n_out),
        "ofk_vn": np.zeros(n_out),
        "ofk_ve": np.zeros(n_out),
        "ofk_vh": np.zeros(n_out),
        "gnss_fi": np.full(n_out, np.nan),
        "gnss_lam": np.full(n_out, np.nan),
        "gnss_h": np.full(n_out, np.nan),
        "gnss_vn": np.full(n_out, np.nan),
        "gnss_ve": np.full(n_out, np.nan),
        "gnss_vh": np.full(n_out, np.nan),
        "ofk_std_fi": np.zeros(n_out),
        "ofk_std_lam": np.zeros(n_out),
        "ofk_std_h": np.zeros(n_out),
        "ofk_std_vn": np.zeros(n_out),
        "ofk_std_ve": np.zeros(n_out),
        "ofk_std_vh": np.zeros(n_out),
        "err_bins_fi": np.zeros(n_out),
        "err_bins_lam": np.zeros(n_out),
        "err_bins_vn": np.zeros(n_out),
        "err_bins_ve": np.zeros(n_out),
        "err_bins_vh": np.zeros(n_out),
        "err_bins_h": np.zeros(n_out),
        "err_ofk_fi": np.zeros(n_out),
        "err_ofk_lam": np.zeros(n_out),
        "err_ofk_vn": np.zeros(n_out),
        "err_ofk_ve": np.zeros(n_out),
        "err_ofk_vh": np.zeros(n_out),
        "err_ofk_h": np.zeros(n_out),
        "u": np.zeros((4, n_out)),
    }

    u = u0.copy()
    log_idx = 0
    ap_count = 0
    ap_steps = int(0.01 / dt)
    ofk_count = 0
    ofk_log_count = 0
    n_steps = int(tmodel / dt)

    for i in range(n_steps):
        t = (i + 1) * dt

        fx1 = lambda x, u, t: fx1_func(x, u, t, la)
        result = rk4_step(fx1, t - dt, dt, x, u)
        x = result[0]
        af_bi_b = result[2]
        wbi_b = result[3]
        dx_est = result[1]

        cgb = c_gb(x[8], x[6], x[7])
        v_nav = cgb.T @ np.array([x[0], x[1], x[2]])

        ap_count += 1
        if ap_count >= ap_steps:
            ap_count = 0
            u = autopilot(x, dx_est, t, u0, htr, vtr, tettr)

        q, cbn, np_bins, a_dlu = bins1(
            af_bi_b, wbi_b, np_bins, cbn, q, dt, x[10], v_nav[1], sensors
        )

        np_gnss, _v_gnss = gnss_1(
            x[12], x[13], x[10], v_nav[0], v_nav[2], v_nav[1], rng=rng_gnss
        )

        z = np.array(
            [
                np_bins[4] - np_gnss[0],
                np_bins[5] - np_gnss[1],
                np_bins[0] - np_gnss[3],
                np_bins[2] - np_gnss[4],
                np_bins[1] - np_gnss[5],
                np_bins[3] - np_gnss[2],
            ],
            dtype=float,
        )

        ofk_count += 1
        ofk_updated = False
        p_post = p_ofk
        if ofk_count >= step_ofk or i == 0:
            ofk_count = 0
            ofk_updated = True
            f, g, h, q_mat = build_bins_ofk_6ch_matrices(a_dlu, cbn, np_bins, dt * mg)
            x_ofk, p_post = ofk(f, g, h, q_mat, r_gnss, z, x_ofk, p_ofk, dt * mg)
            p_ofk = p_post
            _apply_ofk_feedback(np_bins, x_ofk)
            x_ofk[:] = 0.0

        np_etalon = np.array([v_nav[0], v_nav[1], v_nav[2], x[10], x[12], x[13]], dtype=float)
        nper = np_bins - np_etalon

        if ofk_updated and (ofk_log_count % ofk_log_stride == 0):
            log["time"][log_idx] = t
            log["true_h"][log_idx] = x[10]
            log["true_fi"][log_idx] = x[12]
            log["true_lam"][log_idx] = x[13]
            log["true_vn"][log_idx] = v_nav[0]
            log["true_ve"][log_idx] = v_nav[2]
            log["true_vh"][log_idx] = v_nav[1]
            log["bins_h"][log_idx] = np_bins[3]
            log["bins_fi"][log_idx] = np_bins[4]
            log["bins_lam"][log_idx] = np_bins[5]
            log["bins_vn"][log_idx] = np_bins[0]
            log["bins_ve"][log_idx] = np_bins[2]
            log["bins_vh"][log_idx] = np_bins[1]
            log["ofk_h"][log_idx] = np_bins[3]
            log["ofk_fi"][log_idx] = np_bins[4]
            log["ofk_lam"][log_idx] = np_bins[5]
            log["ofk_vn"][log_idx] = np_bins[0]
            log["ofk_ve"][log_idx] = np_bins[2]
            log["ofk_vh"][log_idx] = np_bins[1]
            log["gnss_fi"][log_idx] = np_gnss[0]
            log["gnss_lam"][log_idx] = np_gnss[1]
            log["gnss_h"][log_idx] = np_gnss[2]
            log["gnss_vn"][log_idx] = np_gnss[3]
            log["gnss_ve"][log_idx] = np_gnss[4]
            log["gnss_vh"][log_idx] = np_gnss[5]
            log["ofk_std_fi"][log_idx] = np.sqrt(p_post[5, 5])
            log["ofk_std_lam"][log_idx] = np.sqrt(p_post[6, 6])
            log["ofk_std_h"][log_idx] = np.sqrt(p_post[14, 14])
            log["ofk_std_vn"][log_idx] = np.sqrt(p_post[3, 3])
            log["ofk_std_ve"][log_idx] = np.sqrt(p_post[4, 4])
            log["ofk_std_vh"][log_idx] = np.sqrt(p_post[13, 13])
            log["err_bins_fi"][log_idx] = nper[4]
            log["err_bins_lam"][log_idx] = nper[5]
            log["err_bins_h"][log_idx] = nper[3]
            log["err_bins_vn"][log_idx] = nper[0]
            log["err_bins_ve"][log_idx] = nper[2]
            log["err_bins_vh"][log_idx] = nper[1]
            log["err_ofk_fi"][log_idx] = np_bins[4] - x[12]
            log["err_ofk_lam"][log_idx] = np_bins[5] - x[13]
            log["err_ofk_h"][log_idx] = np_bins[3] - x[10]
            log["err_ofk_vn"][log_idx] = np_bins[0] - v_nav[0]
            log["err_ofk_ve"][log_idx] = np_bins[2] - v_nav[2]
            log["err_ofk_vh"][log_idx] = np_bins[1] - v_nav[1]
            log["u"][:, log_idx] = u
            log_idx += 1
            ofk_log_count += 1
        elif ofk_updated:
            ofk_log_count += 1

        if i % 20000 == 0:
            v = np.sqrt(x[0] ** 2 + x[1] ** 2 + x[2] ** 2)
            print(f"t={t:.1f}s  H={x[10]:.1f}m  V={v:.1f}m/s  Vn={v_nav[0]:.2f}m/s")

    out = {}
    for k, v in log.items():
        arr = np.asarray(v)
        if k == "u" and arr.ndim == 2:
            out[k] = arr[:, :log_idx].copy()
        else:
            out[k] = arr[:log_idx]
    out["u0"] = np.asarray(sim["u0"], dtype=float).copy()
    return out


run_simulation = run_modeling_1
