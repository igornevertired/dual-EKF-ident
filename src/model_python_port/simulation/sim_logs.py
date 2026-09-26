"""Буферы и запись логов симуляции. На механизацию и фильтры не влияет."""

from __future__ import annotations

import numpy as np

from ..filtering.ofk2_ekf import N_MEAS, N_PARAM
from ..filtering.ofk2_theory import PARAM_NAMES, coeff_delta_ekf_minus_theory


def _alloc_gnss_log(n_gnss: int) -> dict[str, np.ndarray]:
    z = np.zeros
    nan = np.nan
    log: dict[str, np.ndarray] = {
        "time": z(n_gnss),
        "true_h": z(n_gnss),
        "true_fi": z(n_gnss),
        "true_lam": z(n_gnss),
        "true_vn": z(n_gnss),
        "true_ve": z(n_gnss),
        "true_vh": z(n_gnss),
        "bins_h": z(n_gnss),
        "bins_fi": z(n_gnss),
        "bins_lam": z(n_gnss),
        "bins_vn": z(n_gnss),
        "bins_ve": z(n_gnss),
        "bins_vh": z(n_gnss),
        "ofk_h": z(n_gnss),
        "ofk_fi": z(n_gnss),
        "ofk_lam": z(n_gnss),
        "ofk_vn": z(n_gnss),
        "ofk_ve": z(n_gnss),
        "ofk_vh": z(n_gnss),
        "gnss_fi": np.full(n_gnss, nan),
        "gnss_lam": np.full(n_gnss, nan),
        "gnss_h": np.full(n_gnss, nan),
        "gnss_vn": np.full(n_gnss, nan),
        "gnss_ve": np.full(n_gnss, nan),
        "gnss_vh": np.full(n_gnss, nan),
        "ofk_std_fi": z(n_gnss),
        "ofk_std_lam": z(n_gnss),
        "ofk_std_h": z(n_gnss),
        "ofk_std_vn": z(n_gnss),
        "ofk_std_ve": z(n_gnss),
        "ofk_std_vh": z(n_gnss),
        "err_bins_fi": z(n_gnss),
        "err_bins_lam": z(n_gnss),
        "err_bins_vn": z(n_gnss),
        "err_bins_ve": z(n_gnss),
        "err_bins_vh": z(n_gnss),
        "err_bins_h": z(n_gnss),
        "err_ofk_fi": z(n_gnss),
        "err_ofk_lam": z(n_gnss),
        "err_ofk_vn": z(n_gnss),
        "err_ofk_ve": z(n_gnss),
        "err_ofk_vh": z(n_gnss),
        "err_ofk_h": z(n_gnss),
        "u": z((4, n_gnss)),
        "sp_alpha": z(n_gnss),
        "sp_q": z(n_gnss),
        "sp_de": z(n_gnss),
        "sp_az": z(n_gnss),
        "sp_params": z((N_PARAM, n_gnss)),
        "sp_delta": z((N_MEAS, n_gnss)),
        "sp_z": z((6, n_gnss)),
        "z_nav": z((6, n_gnss)),
        "true_alpha": z(n_gnss),
        "true_q": z(n_gnss),
        "true_az": z(n_gnss),
        "d_params": z((N_PARAM, n_gnss)),
        "d_params_trim": z((N_PARAM, n_gnss)),
        "sp_theory_inst": z((N_PARAM, n_gnss)),
        "sp_std": z((N_PARAM, n_gnss)),
    }
    for name in PARAM_NAMES:
        log[f"ofk2_std_{name}"] = z(n_gnss)
    return log


class SimLogs:
    """Два буфера: 10 Гц (ГНСС/ОФК-1) и 50 Гц (ОФК-2)."""

    def __init__(self, n_gnss: int, n_ofk2_max: int):
        self.gnss_idx = 0
        self.ofk2_idx = 0
        self.log = _alloc_gnss_log(n_gnss)
        n = n_ofk2_max
        self.ofk2_time = np.zeros(n)
        self.ofk2_params = np.zeros((N_PARAM, n))
        self.ofk2_theory = np.zeros((N_PARAM, n))
        self.ofk2_std = np.zeros((N_PARAM, n))
        self.ofk2_d_params = np.zeros((N_PARAM, n))
        self.ofk2_d_params_trim = np.zeros((N_PARAM, n))
        self.ofk2_innov_prior = np.full((N_MEAS, n), np.nan)
        self.ofk2_innov_std = np.full((N_MEAS, n), np.nan)
        self.ofk2_reg = np.zeros((5, n))
        self.ofk2_true_aq = np.zeros((4, n))

    def write_gnss(
        self,
        *,
        t: float,
        x: np.ndarray,
        v_nav: np.ndarray,
        np_bins: np.ndarray,
        np_cons: np.ndarray,
        np_gnss: np.ndarray,
        p_ofk: np.ndarray,
        nper_pre: np.ndarray,
        nper_post: np.ndarray,
        true_alpha: float,
        true_q: float,
        true_az: float,
        u: np.ndarray,
        z: np.ndarray,
    ) -> None:
        i = self.gnss_idx
        log = self.log
        log["time"][i] = t
        log["true_h"][i] = x[10]
        log["true_fi"][i] = x[12]
        log["true_lam"][i] = x[13]
        log["true_vn"][i] = v_nav[0]
        log["true_ve"][i] = v_nav[2]
        log["true_vh"][i] = v_nav[1]
        log["bins_h"][i] = np_bins[3]
        log["bins_fi"][i] = np_bins[4]
        log["bins_lam"][i] = np_bins[5]
        log["bins_vn"][i] = np_bins[0]
        log["bins_ve"][i] = np_bins[2]
        log["bins_vh"][i] = np_bins[1]
        log["ofk_h"][i] = np_cons[3]
        log["ofk_fi"][i] = np_cons[4]
        log["ofk_lam"][i] = np_cons[5]
        log["ofk_vn"][i] = np_cons[0]
        log["ofk_ve"][i] = np_cons[2]
        log["ofk_vh"][i] = np_cons[1]
        log["gnss_fi"][i] = np_gnss[0]
        log["gnss_lam"][i] = np_gnss[1]
        log["gnss_h"][i] = np_gnss[2]
        log["gnss_vn"][i] = np_gnss[3]
        log["gnss_ve"][i] = np_gnss[4]
        log["gnss_vh"][i] = np_gnss[5]
        log["ofk_std_fi"][i] = np.sqrt(p_ofk[5, 5])
        log["ofk_std_lam"][i] = np.sqrt(p_ofk[6, 6])
        log["ofk_std_h"][i] = np.sqrt(p_ofk[14, 14])
        log["ofk_std_vn"][i] = np.sqrt(p_ofk[3, 3])
        log["ofk_std_ve"][i] = np.sqrt(p_ofk[4, 4])
        log["ofk_std_vh"][i] = np.sqrt(p_ofk[13, 13])
        log["err_bins_fi"][i] = nper_pre[4]
        log["err_bins_lam"][i] = nper_pre[5]
        log["err_bins_h"][i] = nper_pre[3]
        log["err_bins_vn"][i] = nper_pre[0]
        log["err_bins_ve"][i] = nper_pre[2]
        log["err_bins_vh"][i] = nper_pre[1]
        log["err_ofk_fi"][i] = nper_post[4]
        log["err_ofk_lam"][i] = nper_post[5]
        log["err_ofk_h"][i] = nper_post[3]
        log["err_ofk_vn"][i] = nper_post[0]
        log["err_ofk_ve"][i] = nper_post[2]
        log["err_ofk_vh"][i] = nper_post[1]
        log["true_alpha"][i] = true_alpha
        log["true_q"][i] = true_q
        log["true_az"][i] = true_az
        log["u"][:, i] = u
        log["z_nav"][:, i] = z
        self.gnss_idx = i + 1

    def write_ofk2(
        self,
        *,
        t: float,
        x: np.ndarray,
        x_sp: np.ndarray,
        p_sp: np.ndarray,
        th_inst_vec: np.ndarray,
        th_vec: np.ndarray,
        innov_prior_sp: np.ndarray,
        innov_std_sp: np.ndarray,
        da: float,
        q_meas: float,
        dde: float,
        dv: float,
        dtheta: float,
    ) -> None:
        k = self.ofk2_idx
        self.ofk2_time[k] = t
        self.ofk2_params[:, k] = x_sp[:N_PARAM]
        self.ofk2_theory[:, k] = th_inst_vec
        self.ofk2_std[:, k] = np.sqrt(np.diag(p_sp))
        self.ofk2_d_params[:, k] = x_sp[:N_PARAM] - th_inst_vec
        self.ofk2_d_params_trim[:, k] = x_sp[:N_PARAM] - th_vec
        self.ofk2_innov_prior[:, k] = innov_prior_sp
        self.ofk2_innov_std[:, k] = innov_std_sp
        self.ofk2_reg[:, k] = (da, q_meas, dde, dv, dtheta)
        self.ofk2_true_aq[0, k] = -np.arctan2(
            x[1], x[0] if abs(x[0]) > 1e-9 else 1e-9
        )
        self.ofk2_true_aq[1, k] = x[5]
        self.ofk2_true_aq[2, k] = np.sqrt(x[0] ** 2 + x[1] ** 2 + x[2] ** 2)
        self.ofk2_true_aq[3, k] = x[8]
        self.ofk2_idx = k + 1

    def write_ofk2_on_last_gnss(
        self,
        *,
        z_sp: np.ndarray,
        innov_sp: np.ndarray,
        alpha_gnss: float,
        q_meas: float,
        de_meas: float,
        az_meas: float,
        x_sp: np.ndarray,
        th_inst_vec: np.ndarray,
        th_vec: np.ndarray,
        p_sp: np.ndarray,
    ) -> None:
        if self.gnss_idx <= 0:
            return
        j = self.gnss_idx - 1
        log = self.log
        std_sp = np.sqrt(np.diag(p_sp))
        log["sp_z"][:, j] = z_sp
        log["sp_delta"][:, j] = innov_sp
        log["sp_alpha"][j] = alpha_gnss
        log["sp_q"][j] = q_meas
        log["sp_de"][j] = de_meas
        log["sp_az"][j] = az_meas
        log["sp_params"][:, j] = x_sp[:N_PARAM]
        log["sp_theory_inst"][:, j] = th_inst_vec
        log["d_params"][:, j] = coeff_delta_ekf_minus_theory(x_sp, th_inst_vec)
        log["d_params_trim"][:, j] = coeff_delta_ekf_minus_theory(x_sp, th_vec)
        log["sp_std"][:, j] = std_sp
        for k, name in enumerate(PARAM_NAMES):
            log[f"ofk2_std_{name}"][j] = std_sp[k]

    def finalize(
        self,
        *,
        sim: dict,
        sp_theory: dict,
        th_vec: np.ndarray,
        elevator_doublet_amp_deg: float,
        coeff_start_err: float,
        ofk2_start_scale: float | None,
        ofk2_q_std: float,
        aero_step_t: float | None,
        ofk1_feedback: bool,
    ) -> dict:
        out: dict = {}
        n = self.gnss_idx
        for key, val in self.log.items():
            arr = np.asarray(val)
            out[key] = arr[:, :n].copy() if arr.ndim == 2 else arr[:n].copy()
        k = self.ofk2_idx
        out["u0"] = np.asarray(sim["u0"], dtype=float).copy()
        out["bal"] = np.asarray(sim["bal"], dtype=float).copy()
        out["sp_theory"] = {name: float(val) for name, val in sp_theory.items()}
        out["sp_theory_vec"] = th_vec.copy()
        out["sp_theory_vec_trim"] = th_vec.copy()
        out["ofk2_time"] = self.ofk2_time[:k].copy()
        out["ofk2_params"] = self.ofk2_params[:, :k].copy()
        out["ofk2_theory"] = self.ofk2_theory[:, :k].copy()
        out["ofk2_std"] = self.ofk2_std[:, :k].copy()
        out["ofk2_d_params"] = self.ofk2_d_params[:, :k].copy()
        out["ofk2_d_params_trim"] = self.ofk2_d_params_trim[:, :k].copy()
        out["ofk2_innov_prior"] = self.ofk2_innov_prior[:, :k].copy()
        out["ofk2_innov_std"] = self.ofk2_innov_std[:, :k].copy()
        out["ofk2_reg"] = self.ofk2_reg[:, :k].copy()
        out["ofk2_true_aq"] = self.ofk2_true_aq[:, :k].copy()
        out["elevator_doublet_amp_deg"] = float(elevator_doublet_amp_deg)
        out["coeff_start_err"] = float(coeff_start_err)
        out["ofk2_start_scale"] = (
            None if ofk2_start_scale is None else float(ofk2_start_scale)
        )
        out["ofk2_q_std"] = float(ofk2_q_std)
        out["aero_step_t"] = None if aero_step_t is None else float(aero_step_t)
        out["ofk1_feedback"] = bool(ofk1_feedback)
        return out
