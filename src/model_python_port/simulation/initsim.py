"""
Сборка начальных данных для запуска расчётов (аналог фрагмента INITSIM.m).
"""

import numpy as np

from .initla import initla
from ..navigation.initivk import initivk
from .intstate import intstate
from ..common.earthmodel import earthmodel


def _balancing_cost(bal, htr, vtr, thetatr, gamtr, betatr, la):
    """
    Целевая функция балансировки (порт FCT.m).
    Минимизирует J = (m*dVx)^2 + (m*dVy)^2 + (Mz)^2.
    BAL = [δT, α, δV, δN, δE]
    """
    par = la["PAR"]
    pmax = la["PMAX"]
    r00 = 0.125
    gr = 180.0 / np.pi

    m = par[0]
    fi_p = par[1] * np.pi / 180.0
    jxx, jyy, jzz, jxy = par[2], par[3], par[4], par[5]

    cy0 = par[6]
    cy_alp = par[7]
    cy_deltav = par[8]
    cy_fi = par[9]

    cx0 = par[10]
    a_par = par[11]
    b_par = par[12]

    mz0 = par[19]
    mz_alp = par[20]
    mz_alp2 = par[21]
    mz_deltav = par[22]
    mz_fi = par[23]
    mz_wz = par[24]
    mz_dalp = par[25]

    x_t = par[47]
    s = par[48]
    l = par[49]
    ba = par[50]
    fist = par[51]
    alpkr = par[52]

    delta_t = bal[0]
    alpha = bal[1]
    delta_v = bal[2]
    delta_n = bal[3]
    delta_e = bal[4]

    beta = betatr
    tet = alpha + thetatr
    gam = gamtr

    alp = alpha * gr + alpkr
    be = beta * gr

    v = vtr
    vx1 = v * np.cos(beta) * np.cos(alpha)
    vy1 = -v * np.cos(beta) * np.sin(alpha)
    vz1 = v * np.sin(beta)

    cy = cy0 + cy_alp * alp + cy_deltav * delta_v + cy_fi * fist
    cx = cx0 + a_par * cy + b_par * cy**2

    _, _, _, gtg = earthmodel(htr, 0.0, 0.0)
    g = np.linalg.norm(gtg)
    rho = r00 * ((288.16 - 0.0066 * htr) / 288.16) ** 4.255
    q = 0.5 * rho * v**2 * s * g

    fx = cx * q
    fy = cy * q
    fx1_a = fx * np.cos(alpha) - fy * np.sin(alpha)
    fy1_a = fx * np.sin(alpha) + fy * np.cos(alpha)

    p = delta_t * pmax * (rho / r00) ** 0.75

    dvx1 = (1.0 / m) * (p * np.cos(fi_p) - fx1_a) - g * np.sin(tet)
    dvy1 = (1.0 / m) * (p * np.sin(fi_p) + fy1_a) - g * np.cos(tet) * np.cos(gam)

    dalp = -(dvy1 * vx1 - dvx1 * vy1) / (vx1**2 + vy1**2)

    mz = (mz0 + mz_alp * alp + mz_alp2 * alp**2 + mz_deltav * delta_v
          + mz_fi * fist + mz_wz * 0.0 * ba / v + mz_dalp * dalp * ba / v
          + (x_t - 25.0) * cy * 0.01)
    mz1 = mz * q * ba

    sigf1 = dvx1 * m
    sigf2 = dvy1 * m

    j = sigf1**2 + sigf2**2 + mz1**2
    return j


def _find_balancing(htr, vtr, thetatr, gamtr, betatr, la):
    """
    Находит вектор балансировки BAL = [δT, α, δV, δN, δE] методом координатного спуска.
    Аналог fminunc из MATLAB (порт BALANCING.m).
    """
    bal = np.array([0.3, 0.03, 0.0, 0.0, 0.0])

    cost = _balancing_cost(bal, htr, vtr, thetatr, gamtr, betatr, la)

    for iteration in range(200):
        improved = False
        for i in range(5):
            best_j = cost
            best_val = bal[i]
            step = 0.001 if i >= 2 else 0.005
            if i == 1:
                step = 0.001

            for direction in [-1, 1]:
                for mag in [step, step * 10, step * 100]:
                    trial = bal.copy()
                    trial[i] = best_val + direction * mag
                    j = _balancing_cost(trial, htr, vtr, thetatr, gamtr, betatr, la)
                    if j < best_j:
                        best_j = j
                        bal = trial
                        improved = True

        if not improved:
            break
        cost = best_j

    return bal


def _nominal_bal():
    """
    Вектор балансировки ``BAL`` для построения начального состояния.
    Задаёт номинальные относительную тягу, угол атаки в скоростной постановке
    и положения рулей (как в прежней заглушке balancing): ``[δT, α, δV, δN, δE]``.
    """
    return np.array([0.4, 0.02, 0.0, 0.0, 0.0], dtype=float)


def initsim():
    """
    Формирует словарь с параметрами ЛА, шагом моделирования и начальным состоянием.
    """
    la = initla()
    dt = 1e-3
    tmodel = 1000.0
    tglide = 10800.0
    la["TGLIDE"] = tglide

    htr = 500.0
    vtr = 80.0
    thetatr = 0.0
    gamtr = 0.0
    betatr = 0.0

    bal = _find_balancing(htr, vtr, thetatr, gamtr, betatr, la)
    tettr = thetatr + bal[1]
    x0 = intstate(htr, vtr, thetatr, betatr, gamtr, 0.0, 0.0, 0.0, [0.0, 0.0, 0.0], bal)
    u0 = np.array([bal[0], bal[2], 0.0, 0.0], dtype=float)
    u0_horiz = u0.copy()
    u0_glide = np.array([bal[0], bal[2], 0.0, 0.0], dtype=float)
    ivk = initivk(x0)

    return {
        "la": la,
        "dt": dt,
        "tmodel": tmodel,
        "tglide": tglide,
        "htr": htr,
        "vtr": vtr,
        "thetatr": thetatr,
        "gamtr": gamtr,
        "betatr": betatr,
        "tettr": tettr,
        "bal": bal,
        "x0": x0,
        "u0": u0,
        "u0_horiz": u0_horiz,
        "u0_glide": u0_glide,
        "ivk": ivk,
    }
