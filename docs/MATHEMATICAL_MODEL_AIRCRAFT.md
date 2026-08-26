---
title: Математическая модель движения ЛА
---

# Математическая модель движения летательного аппарата

> **Просмотр формул:** в Cursor / VS Code включите `Markdown › Math: Enabled`  
> или откройте файл на GitHub — формулы рендерятся через KaTeX.

Математическая модель движения летательного аппарата (ЛА) реализована в виде системы обыкновенных дифференциальных уравнений (ОДУ) шести степеней свободы с учётом:

- нелинейной аэродинамики;
- тяги двигательной установки;
- модели гравитационного поля и вращения Земли (эллипсоид Красовского);
- переносных и кориолисовых ускорений;
- динамики приводов органов управления;
- автопилота удержания высоты, скорости и курса.

Модель соответствует блоку **FX1** (`src/model_python_port/fx1.py`) и интегрируется методом Рунге–Кутты 4-го порядка с шагом $\Delta t = 1\,\mathrm{мс}$.

**Номинальный режим полёта:** $H = 500\,\mathrm{м}$, $V = 80\,\mathrm{м/с}$, горизонтальный полёт.

---

## 1. Системы координат

| СК | Обозначение | Назначение |
|----|-------------|------------|
| Связанная | $O_b x_b y_b z_b$ | Оси жёстко связаны с ЛА |
| Географическая | $O_g$ | Север — $n$, вертикаль — $h$, восток — $e$ |
| Скоростная | $O_a$ | Ось $x_a$ вдоль воздушной скорости |

Переход из географической СК в связанную — матрица направляющих косинусов $\mathbf{C}_{gb}(\theta, \gamma, \psi)$:

- $\theta$ — тангаж;
- $\gamma$ — крен;
- $\psi$ — курс.

$$
\mathbf{C}_{gb} =
\begin{bmatrix}
\cos\psi\cos\theta & \sin\theta & -\sin\psi\cos\theta \\
-\cos\psi\sin\theta\cos\gamma + \sin\psi\sin\gamma & \cos\theta\cos\gamma & \cos\psi\sin\gamma + \sin\psi\sin\theta\cos\gamma \\
\cos\psi\sin\theta\sin\gamma + \sin\psi\cos\gamma & -\cos\theta\sin\gamma & \cos\psi\cos\gamma - \sin\psi\sin\theta\sin\gamma
\end{bmatrix}
$$

$$
\mathbf{g}_b = \mathbf{C}_{gb}\, \mathbf{g}_g
$$

---

## 2. Вектор состояния и управления

### 2.1. Вектор состояния (25 компонент)

$$
\mathbf{x} =
\bigl[
V_x,\, V_y,\, V_z,\,
\omega_x,\, \omega_y,\, \omega_z,\,
\gamma,\, \psi,\, \theta,\,
X_g,\, H,\, Z_g,\,
\varphi,\, \lambda,\, d,\,
\delta_T,\, \delta_V,\, \delta_N,\, \delta_E,\,
V_{wx},\, V_{wy},\, V_{wz},\,
H_{fl},\, \varepsilon,\, x_1
\bigr]^{\mathsf T}
$$

| Индекс | Переменная | Смысл |
|--------|------------|-------|
| 0–2 | $V_x, V_y, V_z$ | Скорость в связанной СК, м/с |
| 3–5 | $\omega_x, \omega_y, \omega_z$ | Угловая скорость, рад/с |
| 6–8 | $\gamma, \psi, \theta$ | Крен, курс, тангаж, рад |
| 9–11 | $X_g, H, Z_g$ | Координаты, м |
| 12–13 | $\varphi, \lambda$ | Широта, долгота, рад |
| 15–18 | $\delta_T, \delta_V, \delta_N, \delta_E$ | Приводы |

### 2.2. Вектор управления

$$
\mathbf{u} =
\bigl[
\delta_T^{\mathrm{cmd}},\,
\delta_V^{\mathrm{cmd}},\,
\delta_N^{\mathrm{cmd}},\,
\delta_E^{\mathrm{cmd}}
\bigr]^{\mathsf T}
$$

---

## 3. Параметры ЛА

| Параметр | Обозначение | Значение |
|----------|-------------|----------|
| Масса | $m$ | $1.7 \times 10^{5}$ кг |
| $J_{xx}$ | — | $8.4 \times 10^{6}$ кг·м² |
| $J_{yy}$ | — | $3.0 \times 10^{7}$ кг·м² |
| $J_{zz}$ | — | $2.3 \times 10^{7}$ кг·м² |
| $J_{xy}$ | — | $-0.7 \times 10^{6}$ кг·м² |
| $P_{\max}$ | — | $2.6 \times 10^{5}$ Н |
| $S$ | — | 330 м² |
| $l$ | — | 48.06 м |
| $b_a$ | — | 7.57 м |
| $\varphi_p$ | — | 5° |

---

## 4. Аэродинамическая модель

### 4.1. Скорость и углы

$$
V_a = \sqrt{(V_x - V_{wx})^2 + (V_y - V_{wy})^2 + (V_z - V_{wz})^2}
$$

$$
\alpha = -\arctan\frac{V_{ay}}{V_{ax}},
\qquad
\beta = \arcsin\frac{V_{az}}{V_a}
$$

$$
\alpha_g = \alpha \cdot \frac{180}{\pi} + \alpha_{kr},
\qquad
\beta_g = \beta \cdot \frac{180}{\pi}
$$

### 4.2. Плотность воздуха

$$
\rho = \rho_0 \left( \frac{288.16 - 0.0066\, H}{288.16} \right)^{4.255},
\qquad
\rho_0 = 0.125\;\mathrm{кг/м^3}
$$

### 4.3. Скоростной напор

$$
q = \tfrac{1}{2}\, \rho\, V^2\, S\, \|\mathbf{g}_{Tg}\|
$$

### 4.4. Аэродинамические коэффициенты

$$
C_y = C_{y0} + C_y^{\alpha}\, \alpha_g + C_y^{\delta_V}\, \delta_V + C_y^{\varphi_i}\, \varphi_{ist}
$$

$$
C_x = C_{x0} + a_1 C_y + b_1 C_y^2
+ \left( C_x^{\delta_V} + C_x^{\alpha\delta_V}\, \alpha_g + C_x^{\alpha^2\delta_V}\, \alpha_g^2 \right) \delta_V
+ \left( C_x^{\varphi_i} + C_x^{\alpha\varphi_i}\, \alpha_g + C_x^{\alpha^2\varphi_i}\, \alpha_g^2 \right) \varphi_{ist}
$$

$$
C_z = C_z^{\beta}\, \beta_g + C_z^{\delta_N}\, \delta_N
$$

### 4.5. Силы

$$
F_x = C_x\, q, \quad F_y = C_y\, q, \quad F_z = C_z\, q
$$

$$
F_{x_b} = F_x \cos\alpha - F_y \sin\alpha
$$

$$
F_{y_b} = F_x \sin\alpha + F_y \cos\alpha
$$

$$
F_{z_b} = F_z
$$

### 4.6. Моменты

$$
\Omega_x = \frac{\omega_{xe}\, l}{2V},
\quad
\Omega_y = \frac{\omega_{ye}\, l}{2V},
\quad
\Omega_z = \frac{\omega_{ze}\, b_a}{V}
$$

$$
M_x = m_x\, q\, l,
\quad
M_y = m_y\, q\, l,
\quad
M_z = m_z\, q\, b_a
$$

### 4.7. Тяга

$$
P = \delta_T \cdot P_{\max} \left( \frac{\rho}{\rho_0} \right)^{0.75}
$$

$$
F_{Tx} = P \cos\varphi_p,
\qquad
F_{Ty} = P \sin\varphi_p
$$

---

## 5. Уравнения поступательного движения (ЦМ)

$$
\dot{\mathbf{V}}_b
= \frac{1}{m}\, \mathbf{F}_{\mathrm{aero}}
+ \mathbf{a}_p + \mathbf{a}_k + \mathbf{a}_t + \mathbf{g}_b
$$

$$
\dot V_x = \frac{1}{m}(P\cos\varphi_p - F_{x_b}) + a_{p,x} + a_{k,x} + a_{t,x} + g_{b,x}
$$

$$
\dot V_y = \frac{1}{m}(P\sin\varphi_p + F_{y_b}) + a_{p,y} + a_{k,y} + a_{t,y} + g_{b,y}
$$

$$
\dot V_z = \frac{F_{z_b}}{m} + a_{p,z} + a_{t,z} + g_{b,z}
$$

---

## 6. Модель Земли

### 6.1. Эллипсоид Красовского

$$
a = 6\,378\,245\;\mathrm{м},
\quad
b = 6\,356\,856\;\mathrm{м},
\quad
e^2 = \frac{a^2 - b^2}{a^2}
$$

$$
\omega_e = 7.292115 \times 10^{-5}\;\mathrm{рад/с}
$$

### 6.2. Радиусы кривизны

$$
\chi = \sqrt{1 - e^2 \sin^2\varphi}
$$

$$
R_M = \frac{a}{\chi} + H,
\qquad
R_N = \frac{a(1-e^2)}{\chi^3} + H
$$

### 6.3. Гравитация

$$
g_r = -\frac{\mu_0}{r^2} - \frac{3}{2}\, \frac{J_2}{r^4}\, (3\sin^2\varphi_e - 1)
$$

$$
g_{\varphi_e} = -\frac{3}{2}\, \frac{J_2}{r^4}\, \sin 2\varphi_e
$$

$$
g_n = g_r \cos\mu + g_{\varphi_e} \sin\mu,
\qquad
g_\varphi = -g_r \sin\mu + g_{\varphi_e} \cos\mu
$$

$$
\mathbf{g}_g = \begin{bmatrix} g_\varphi \\ g_n \\ 0 \end{bmatrix}
$$

$$
g_{Tn} = g_n - r\, \omega_e^2 \cos\varphi_e \cos\varphi
$$

### 6.4. Ускорения вращения Земли

$$
\boldsymbol{\omega}_{ei}^g =
\begin{bmatrix}
\omega_e \cos\varphi \\
\omega_e \sin\varphi \\
0
\end{bmatrix}
$$

$$
\mathbf{a}_p = -\boldsymbol{\omega}_{ei}^g \times (\boldsymbol{\omega}_{ei}^g \times \mathbf{r}_n)
$$

$$
\mathbf{a}_k = -2\, \boldsymbol{\omega}_{ei}^b \times \mathbf{V}_b
$$

$$
\boldsymbol{\omega}_{eg}^g =
\begin{bmatrix}
\dot Z_g / R_M \\
\dot Z_g \tan\varphi / R_M \\
-\dot X_g / R_N
\end{bmatrix}
$$

$$
\mathbf{a}_t = -(\boldsymbol{\omega}_{eg}^b + \boldsymbol{\omega}_{ei}^b) \times \mathbf{V}_b
$$

---

## 7. Уравнения вращательного движения

$$
\dot\omega_x =
\frac{
J_{yy} M_x + J_{xy} M_y
+ J_{xy}(J_{xx}+J_{yy}-J_{zz})\,\omega_x\omega_z
+ (J_{yy}^2 - J_{yy}J_{zz} + J_{xy}^2)\,\omega_y\omega_z
}{J_{xx}J_{yy} - J_{xy}^2}
$$

$$
\dot\omega_y =
\frac{
J_{xy} M_x + J_{xx} M_y
- (J_{xx}^2 - J_{xx}J_{zz} + J_{xy}^2)\,\omega_x\omega_z
+ J_{xy}(J_{xx}+J_{yy}-J_{zz})\,\omega_y\omega_z
}{J_{xx}J_{yy} - J_{xy}^2}
$$

$$
\dot\omega_z =
\frac{
M_z - (J_{yy}-J_{xx})\,\omega_x\omega_y - J_{xy}(\omega_y^2 - \omega_x^2)
}{J_{zz}}
$$

---

## 8. Кинематика

### 8.1. Положение

$$
\dot X_g = V_x\cos\psi\cos\theta
- V_y(\cos\psi\sin\theta\cos\gamma - \sin\psi\sin\gamma)
+ V_z(\sin\psi\cos\gamma + \cos\psi\sin\theta\sin\gamma)
$$

$$
\dot H = V_x\sin\theta + V_y\cos\theta\cos\gamma - V_z\cos\theta\sin\gamma
$$

$$
\dot Z_g = -V_x\sin\psi\cos\theta
+ V_y(\cos\psi\sin\gamma + \sin\psi\sin\theta\cos\gamma)
+ V_z(\cos\psi\cos\gamma - \sin\psi\sin\theta\sin\gamma)
$$

### 8.2. Геодезические координаты

$$
\dot\varphi = \frac{\dot X_g}{R_N},
\qquad
\dot\lambda = \frac{\dot Z_g}{R_M \cos\varphi}
$$

### 8.3. Углы Эйлера

$$
\boldsymbol{\omega}_{bg}^b =
\boldsymbol{\omega}_{bi}^b
- \mathbf{C}_{gb}\, (\boldsymbol{\omega}_{eg}^g + \boldsymbol{\omega}_{ei}^g)
$$

$$
\dot\psi = \frac{\omega_{bg,y}\cos\gamma - \omega_{bg,z}\sin\gamma}{\cos\theta}
$$

$$
\dot\theta = \omega_{bg,z}\cos\gamma + \omega_{bg,y}\sin\gamma
$$

$$
\dot\gamma = \omega_{bg,x} - \dot\psi\sin\theta
$$

---

## 9. Приводы

$$
\dot\delta_T = \frac{\delta_T^{\mathrm{cmd}} - \delta_T}{\tau_T},
\quad \tau_T = 5\;\mathrm{с}
$$

$$
\dot\delta_V = \frac{\delta_V^{\mathrm{cmd}} - \delta_V}{\tau_V},
\quad \tau_V = 0.1\;\mathrm{с}
$$

$$
\dot\delta_N = \frac{\delta_N^{\mathrm{cmd}} - \delta_N}{\tau_N},
\quad \tau_N = \tau_E = \frac{1}{20.2}\;\mathrm{с}
$$

$$
\dot\delta_E = \frac{\delta_E^{\mathrm{cmd}} - \delta_E}{\tau_E}
$$

---

## 10. Автопилот

$$
\mathbf{u} = \mathbf{u}_0 + \Delta\mathbf{u},
\qquad
\mathbf{u} \in [\mathbf{u}_{\min},\, \mathbf{u}_{\max}]
$$

$$
\Delta\delta_T = k_{V1}(V_{tr} - V) + k_{V2}\, \dot V + k_H(H_{tr} - H)
$$

$$
\Delta\delta_V = k_{Wz}\, \omega_z + k_\theta(\theta_{tr} - \theta)
+ k_{H2}(H_{tr} - H) + k_{V3}(V_{tr} - V)
$$

$$
\Delta\delta_N = k_{Wx}\, \omega_x + k_\gamma\, \gamma
$$

$$
\Delta\delta_E = k_{Wy}\, \omega_y + k_\psi(\psi - \psi_{tr})
$$

---

## 11. Численное интегрирование

$$
\dot{\mathbf{x}} = \mathbf{f}(\mathbf{x},\, \mathbf{u},\, t)
$$

$$
\mathbf{x}_{k+1} = \mathbf{x}_k + \frac{\Delta t}{6}
(\mathbf{k}_1 + 2\mathbf{k}_2 + 2\mathbf{k}_3 + \mathbf{k}_4)
$$

$$
J = (m\, \dot V_x)^2 + (m\, \dot V_y)^2 + M_z^2 \to \min
$$

---

## 12. Блок-схема

```
Автопилот → Приводы → FX1 (силы, моменты, Земля) → RK4 → x
    ↑__________________________________________________|
```

---

## 13. Связь с БИНС/ГНСС

- $\mathbf{a}_{f,bi,b}$ — ускорение без гравитации (акселерометр);
- $\boldsymbol{\omega}_{bi,b}$ — угловая скорость (ДУС);
- $H$, $\varphi$, $\lambda$ — истинные координаты;
- $\mathbf{v}_{nav} = \mathbf{C}_{gb}\, [V_x, V_y, V_z]^{\mathsf T}$ — навигационные скорости.

---

## Связанные документы

- [SIMULATION_BINS_GNSS.md](SIMULATION_BINS_GNSS.md)
- [BINS_GNSS_PARAMETERS_AND_AIRCRAFT.md](BINS_GNSS_PARAMETERS_AND_AIRCRAFT.md)
