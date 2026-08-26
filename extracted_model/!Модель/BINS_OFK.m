function [X, F, G, H, Q, NP_ref1] = BINS_OFK(A1, W1, C1, NP1, dt, X0, DVBE_n)
    global wnNxo wnNyo wnNzo wnWxo wnWyo wnWzo
    % X - North; Y - East; Z - Hight(вниз)
    W0 = 1.25*10^-3;  % Schuler frequency

    [Psi, Theta, Gamma] = C_ANG(C1);
    C2 = zeros(3,3);
    C2(1,1) = cos(Theta)*cos(Psi);
    C2(1,2) = -cos(Gamma)*sin(Psi) + sin(Gamma)*sin(Theta)*cos(Psi);
    C2(1,3) = sin(Gamma)*sin(Psi) + cos(Psi)*sin(Theta)*cos(Psi);
    C2(2,1) = cos(Theta)*sin(Psi);
    C2(2,2) = cos(Gamma)*cos(Psi) + sin(Gamma)*sin(Theta)*sin(Psi);
    C2(2,3) = -sin(Gamma)*cos(Psi) + cos(Gamma)*sin(Theta)*sin(Psi);
    C2(3,1) = -sin(Theta);
    C2(3,2) = sin(Gamma)*cos(Theta);
    C2(3,3) = cos(Gamma)*cos(Theta);

    Alt = NP1(4); Fi = NP1(5); Lm = NP1(6);
    Vn = NP1(1); Vh = -NP1(2); Ve = NP1(3);
%     Psi = X0(7); Theta = X0(8); Gamma = X0(9);
    
    % Расчет параметров для матрицы F
    N = C2*[A1(1); A1(3); -A1(2)];
    [Gg,Re,Rn,GTg] = EARTHMODEL(Alt,Fi,Lm);
    O3 = zeros(3,3);
    Ue = 7292115.0E-11;
    e = 0.0818191908425;
    g0 = 9.7803253359*(1 + 0.001931853*(sin(Fi))^2)/(sqrt(1-e^2*(sin(Fi))^2));
    r_es = Rn*sqrt(1 + (-2*e + e^2)*(sin(Fi))^2);
    WF = [Ue*cos(Fi); 0; Ue*sin(Fi)] + [Ve/Re; -Vn/Rn; Ve*tan(Fi)/Re];
  
    % Матрица F
    F11 = -[0,     -WF(3), WF(2);
            WF(3),  0,    -WF(1);
           -WF(2),  WF(1), 0];
    
    F12 = [0,    -1/Re,       0;
           1/Rn,  0,          0;
           0,     tan(Fi)/Re, 0];
        
    F13 = [Ue*sin(Fi),                       0,  Ve/Re^2;
           0,                                0, -Vn/Rn^2;
           Ue*cos(Fi) + Ve/(Re*(cos(Fi))^2), 0, -Ve*tan(Fi)/Re];

    F21 = [0,     -N(3),  N(2);
           N(3),   0,    -N(1);
          -N(2),   N(1),  0];

    F22 = [Vh/Rn,                     -2*Ve*tan(Fi)/Re-2*Ue*sin(Fi), Vn/Rn;
           Ve*tan(Fi)/Re+2*Ue*sin(Fi), (Vn*tan(Fi)+Vh)/Re,           Ve/Re+2*Ue*cos(Fi);
          -2*Vn/Rn,                   -2*Ve/Re-2*Ue*cos(Fi),         0];

    F23 = [Ve^2/(Re*(cos(Fi))^2)-2*Ve*Ue*cos(Fi),                  0, Ve^2*tan(Fi)/Re^2-Vn*Vh/Rn^2;
           Vn*Ve/(Re*(cos(Fi))^2)+2*Vn*Ue*cos(Fi)-2*Vh*Ue*sin(Fi), 0, (-Vn*Ve*tan(Fi)+Ve*Vh)/Re^2;
           2*Ve*Ue*sin(Fi),                                        0, Ve^2/Re^2+Vn^2/Rn^2-2*g0/r_es];

    F32 = [1/Rn, 0,              0;
           0,    1/(Re*cos(Fi)), 0;
           0,    0,             -1];

    F33 = [0,                           0, -Vn/Rn^2;
           Ve*sin(Fi)/(Re*(cos(Fi))^2), 0, -Ve/(Re^2*cos(Fi));
           0,                           0,  0];

    F = [F11 F12 F13 O3 C2;
         F21 F22 F23 C2 O3;
         O3  F32 F33 O3 O3;
         O3  O3  O3  O3 O3;
         O3  O3  O3  O3 O3];
    
    % Матрица G
    G = [O3 C2;
         C2 O3;
         O3 O3;
         O3 O3;
         O3 O3];

    % Матрица H
    H = zeros(4,15);
    H(1,7) = 1;
    H(2,8) = 1;
    H(3,4) = 1;
    H(4,5) = 1;

    % Решение уравнения
    %Wsh = [wnNxo; wnNyo; wnNzo; wnWxo; wnWyo; wnWzo];
    % dX = F*X0 + G*Wsh;
    % X = X0 + dX*dt; % Вектор состояния системы
    % x1 = X(7); x2 = X(8); x4 = X(4); x5 = X(5);
    % dLm = x1;%/(Rn*cos(Fi));
    % dFi = x2;%/Re;
    % NP_ref1 = [dFi; dLm]; % Измерения БИНС
    
    Wq = [7.7570e-08; 7.7570e-08; 7.7570e-08; 0.00035; 0.00035; 0.00035];
    Q = diag(([Wq].^2)/dt);

end