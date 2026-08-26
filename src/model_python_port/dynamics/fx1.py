"""
Модель правых частей уравнений движения ЛА (порт FX1.m).

Связывает аэродинамику, тягу, гравитационную модель Земли, переносные и
кориолисовы ускорения, кинематику по углам и координатам, а также динамику
приводов органов управления и упрощённую посадочную логику при малых высотах.
"""

import numpy as np

from ..common.earthmodel import earthmodel


def c_gb(tet, ph, psi):
    """
    Матрица направляющих косинусов перехода из географической СК в связанную ``C_gb``.

    Углы: тангаж ``tet``, крен ``ph`` (в вызове из FX1 передаётся крен ``GAM``),
    курс ``psi`` — в радианах, как в вложенной функции C_gb внутри FX1.m.
    """
    return np.array(
        [
            [np.cos(psi) * np.cos(tet), np.sin(tet), -np.sin(psi) * np.cos(tet)],
            [
                -np.cos(psi) * np.sin(tet) * np.cos(ph) + np.sin(psi) * np.sin(ph),
                np.cos(tet) * np.cos(ph),
                np.cos(psi) * np.sin(ph) + np.sin(psi) * np.sin(tet) * np.cos(ph),
            ],
            [
                np.cos(psi) * np.sin(tet) * np.sin(ph) + np.sin(psi) * np.cos(ph),
                -np.cos(tet) * np.sin(ph),
                np.cos(psi) * np.cos(ph) - np.sin(psi) * np.sin(tet) * np.sin(ph),
            ],
        ],
        dtype=float,
    )


def fx1(x, u, time, la):
    """
    Правые части системы ОДУ состояния ЛА и выходы для подсистемы БИНС.

    Состояние ``x`` — 25 компонент (скорость и угловая скорость в связанной СК,
    углы ориентации, координаты, географические углы, приводы, ветер, вспомогательные
    переменные приземления). Управление ``u`` — четыре канала (тяга и три руля).
    Словарь ``la`` должен содержать ``PAR``, ``PMAX``, постоянные времени приводов
    и при необходимости ``TGLIDE`` для включения дополнительного слагаемого по тяге
    после заданного времени.

    Возвращает
    ----------
    dx : ndarray, shape (25,)
        Производные состояния.
    af_bi_b : ndarray, shape (3,)
        Удельная аэродинамическая сила без гравитации (для БИНС), м/с².
    wbi_b : ndarray, shape (3,)
        Абсолютная угловая скорость ЛА в связанной СК, рад/с.
    """
    par = la["PAR"]
    pmax = float(la["PMAX"])
    t_throttle = float(la["T_THROTTLE"])
    t_elev = float(la["T_ELEV"])
    t_rud = float(la["T_RUD"])
    t_ail = float(la["T_AIL"])
    tglide = float(la.get("TGLIDE", 1.0e30))

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
    cx_deltav = par[13]
    cx_alp_deltav = par[14]
    cx_alp2_deltav = par[15]
    cx_fi = par[16]
    cx_alp_fi = par[17]
    cx_alp2_fi = par[18]

    mz0 = par[19]
    mz_alp = par[20]
    mz_alp2 = par[21]
    mz_deltav = par[22]
    mz_fi = par[23]
    mz_wz = par[24]
    mz_dalp = par[25]

    cz_be = par[26]
    cz_deltan = par[27]

    mx_deltan = par[28]
    mx_alp_deltan = par[29]
    mx_be = par[30]
    mx_alp_be = par[31]
    mx_deltae = par[32]
    mx_wx = par[33]
    mx_alp_wx = par[34]
    mx_alp2_wx = par[35]
    mx_wy = par[36]
    mx_alp_wy = par[37]

    my_be = par[38]
    my_deltan = par[39]
    my_wx = par[40]
    my_alp_wx = par[41]
    my_alp2_wx = par[42]
    my_wy = par[43]
    my_alp_wy = par[44]
    my_alp2_wy = par[45]
    my_dbe = par[46]

    x_t = par[47]
    s = par[48]
    l = par[49]
    ba = par[50]
    fist = par[51]
    alpkr = par[52]

    gr = 180.0 / np.pi
    r00 = 0.125
    a = 6378245.0
    b = 6356856.0
    e2 = (a**2 - b**2) / a**2
    ue = 7292115.0e-11

    vx1, vy1, vz1 = x[0], x[1], x[2]
    wx1, wy1, wz1 = x[3], x[4], x[5]
    gam, psi, tet = x[6], x[7], x[8]
    _xg, h, _zg = x[9], x[10], x[11]
    fi, lamd = x[12], x[13]
    _d = x[14]
    delta_t = x[15]
    delta_v = x[16]
    delta_n = x[17]
    delta_e = x[18]
    vwx1, vwy1, vwz1 = x[19], x[20], x[21]
    hfl, eps_st, x1 = x[22], x[23], x[24]

    cgb = c_gb(tet, gam, psi)

    gg, r1, r2, gtg = earthmodel(h, fi, lamd)
    gb = cgb @ gg

    vax1 = vx1 - vwx1
    vay1 = vy1 - vwy1
    vaz1 = vz1 - vwz1
    va = np.sqrt(vax1**2 + vay1**2 + vaz1**2)
    eps_v = 1e-9
    va = max(va, eps_v)
    alpha = -np.arctan2(vay1, vax1 + eps_v * np.sign(vax1 + eps_v))
    beta = np.arcsin(np.clip(vaz1 / va, -1.0, 1.0))

    alp = alpha * gr + alpkr
    be = beta * gr

    cy = cy0 + cy_alp * alp + cy_deltav * delta_v + cy_fi * fist
    cx = (
        cx0
        + a_par * cy
        + b_par * cy**2
        + (cx_deltav + cx_alp_deltav * alp + cx_alp2_deltav * alp**2) * delta_v
        + (cx_fi + cx_alp_fi * alp + cx_alp2_fi * alp**2) * fist
    )
    cz = cz_be * be + cz_deltan * delta_n

    rho = r00 * ((288.16 - 0.0066 * h) / 288.16) ** 4.255
    v = np.sqrt(vx1**2 + vy1**2 + vz1**2)
    v = max(v, eps_v)
    qdyn = 0.5 * rho * v**2 * s * np.linalg.norm(gtg)

    fx = cx * qdyn
    fy = cy * qdyn
    fz = cz * qdyn

    fx1_a = fx * np.cos(alpha) - fy * np.sin(alpha)
    fy1_a = fx * np.sin(alpha) + fy * np.cos(alpha)
    fz1_a = fz

    p = delta_t * pmax * (rho / r00) ** 0.75

    wei_g = np.array([ue * np.cos(fi), ue * np.sin(fi), 0.0], dtype=float)
    wei_b = cgb @ wei_g
    wbi_b = np.array([wx1, wy1, wz1], dtype=float)
    vbe_b = np.array([vx1, vy1, vz1], dtype=float)

    rg = np.array([-r1 * e2 * np.sin(fi) * np.cos(fi), r1 * (1.0 - e2 * (np.sin(fi) ** 2)), 0.0], dtype=float)
    ap_g = -np.cross(wei_g, np.cross(wei_g, rg))
    ap_b = cgb @ ap_g
    ak_b = -2.0 * np.cross(wei_b, vbe_b)
    wbe_b = wbi_b - wei_b
    at_b = -np.cross(wbe_b, vbe_b)

    dvx1 = (1.0 / m) * (p * np.cos(fi_p) - fx1_a) + ap_b[0] + ak_b[0] + at_b[0] + gb[0]
    dvy1 = (1.0 / m) * (p * np.sin(fi_p) + fy1_a) + ap_b[1] + ak_b[1] + at_b[1] + gb[1]
    dvz1 = fz1_a / m + ap_b[2] + at_b[2] + gb[2]

    denom_xy = vax1**2 + vay1**2
    denom_xy = max(denom_xy, eps_v**2)
    dalp = -(dvy1 * vax1 - dvx1 * vay1) / denom_xy

    v2_all = vax1**2 + vay1**2 + vaz1**2
    sqrt_xy = np.sqrt(vax1**2 + vay1**2)
    sqrt_xy = max(sqrt_xy, eps_v)
    dbe = (dvz1 * v2_all - vaz1 * (vax1 * dvx1 + vay1 * dvy1 + vaz1 * dvz1)) / (sqrt_xy * v2_all)

    omgx = wbe_b[0] * np.cos(alpha) - wbe_b[1] * np.sin(alpha)
    omgy = wbe_b[0] * np.sin(alpha) + wbe_b[1] * np.cos(alpha)
    omgz = wbe_b[2]

    mx = (
        (mx_deltan + mx_alp_deltan * alp) * delta_n
        + (mx_be + mx_alp_be * alp) * be
        + mx_deltae * delta_e
        + (mx_wx + mx_alp_wx * alp + mx_alp2_wx * alp**2) * omgx * l / (2.0 * v)
        + (mx_wy + mx_alp_wy * alp) * omgy * l / (2.0 * v)
    )
    my = (
        my_be * be
        + my_deltan * delta_n
        + (my_wx + my_alp_wx * alp + my_alp2_wx * alp**2) * omgx * l / (2.0 * v)
        + (my_wy + my_alp_wy * alp + my_alp2_wy * alp**2) * omgy * l / (2.0 * v)
        + my_dbe * dbe * l / (2.0 * v)
    )
    mz = (
        mz0
        + mz_alp * alp
        + mz_alp2 * alp**2
        + mz_deltav * delta_v
        + mz_fi * fist
        + mz_wz * omgz * ba / v
        + mz_dalp * dalp * ba / v
        + (x_t - 25.0) * cy * 0.01
    )

    mx_a = mx * qdyn * l
    my_a = my * qdyn * l
    mz_a = mz * qdyn * ba

    mx1 = mx_a * np.cos(alpha) + my_a * np.sin(alpha)
    my1 = -mx_a * np.sin(alpha) + my_a * np.cos(alpha)
    mz1 = mz_a

    det_j = jxx * jyy - jxy**2
    dwx1 = (
        jyy * mx1
        + jxy * my1
        + jxy * (jxx + jyy - jzz) * wx1 * wz1
        + (jyy**2 - jyy * jzz + jxy**2) * wy1 * wz1
    ) / det_j
    dwy1 = (
        jxy * mx1
        + jxx * my1
        - (jxx**2 - jxx * jzz + jxy**2) * wx1 * wz1
        + jxy * (jxx + jyy - jzz) * wy1 * wz1
    ) / det_j
    dwz1 = (mz1 - (jyy - jxx) * wx1 * wy1 - jxy * (wy1**2 - wx1**2)) / jzz

    dxg = (
        vx1 * np.cos(psi) * np.cos(tet)
        - vy1 * (np.cos(psi) * np.sin(tet) * np.cos(gam) - np.sin(psi) * np.sin(gam))
        + vz1 * (np.sin(psi) * np.cos(gam) + np.cos(psi) * np.sin(tet) * np.sin(gam))
    )
    dh = vx1 * np.sin(tet) + vy1 * np.cos(tet) * np.cos(gam) - vz1 * np.cos(tet) * np.sin(gam)
    dzg = (
        -vx1 * np.sin(psi) * np.cos(tet)
        + vy1 * (np.cos(psi) * np.sin(gam) + np.sin(psi) * np.sin(tet) * np.cos(gam))
        + vz1 * (np.cos(psi) * np.cos(gam) - np.sin(psi) * np.sin(tet) * np.sin(gam))
    )

    wge_g = np.array([dzg / r1, dzg * np.tan(fi) / r1, -dxg / r2], dtype=float)
    wgi_g = wge_g + wei_g
    wgi_b = cgb @ wgi_g
    wbg_b = wbi_b - wgi_b

    dpsi = (wbg_b[1] * np.cos(gam) - wbg_b[2] * np.sin(gam)) / np.cos(tet)
    dtet = wbg_b[2] * np.cos(gam) + wbg_b[1] * np.sin(gam)
    dgam = wbg_b[0] - dpsi * np.sin(tet)

    dfi = dxg / r2
    dlamd = dzg / r1 / np.cos(fi)

    dd = 0.0
    if time > tglide:
        theta_path = np.arcsin(np.clip(dh / np.sqrt(dxg**2 + dzg**2 + eps_v**2), -1.0, 1.0))
        thetatr = -3.0 * np.pi / 180.0
        dd = v * np.sin(theta_path - thetatr)

    dvwx1, dvwy1, dvwz1 = 0.0, 0.0, 0.0

    ddelta_t = (u[0] - delta_t) / t_throttle
    ddelta_v = (u[1] - delta_v) / t_elev
    ddelta_n = (u[2] - delta_n) / t_rud
    ddelta_e = (u[3] - delta_e) / t_ail

    dhfl, deps, dx1 = 0.0, 0.0, 0.0
    if h <= 15.0:
        dhfl = -0.5 * hfl
        deps = hfl - h
        dx1 = -10.0 * x1 + eps_st

    dx = np.array(
        [
            dvx1,
            dvy1,
            dvz1,
            dwx1,
            dwy1,
            dwz1,
            dgam,
            dpsi,
            dtet,
            dxg,
            dh,
            dzg,
            dfi,
            dlamd,
            dd,
            ddelta_t,
            ddelta_v,
            ddelta_n,
            ddelta_e,
            dvwx1,
            dvwy1,
            dvwz1,
            dhfl,
            deps,
            dx1,
        ],
        dtype=float,
    )

    axb = (1.0 / m) * (p * np.cos(fi_p) - fx1_a)
    ayb = (1.0 / m) * (p * np.sin(fi_p) + fy1_a)
    azb = fz1_a / m
    af_bi_b = np.array([axb, ayb, azb], dtype=float)

    return dx, af_bi_b, wbi_b
