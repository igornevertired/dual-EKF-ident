function [X, F, G, H, Q, NP_ref1] = BINS_OFK2(A1, W1, C1, NP1, dt, X0, DVBE_n)
    global wnNxo wnNyo wnNzo wnWxo wnWyo wnWzo
    % X - East; Y - North; - Z - Hight
    W0 = 1.25*10^-3;  % Schuler frequency
    Ue = 7292115.0E-11; % Угл. скорость вращения Земли
        
    Fi = NP1(5); Lm = NP1(6); Alt = NP1(4);
    Vn = NP1(1); Ve = NP1(3); Vh = NP1(2);
%     Psi = X0(7); Theta = X0(8); Gamma = X0(9);
    
    % Расчет параметров для матрицы F
    N = C1*A1;
    Ny = N(1); Nz = N(2); Nx = N(3);
    dVe = DVBE_n(3); dVn = DVBE_n(1);

    [Gg,R1,R2,GTg] = EARTHMODEL(Alt,Fi,Lm);
    
    % Расчет угловых ускорений в географической СК
    Ue = 7292115.0E-11;
    Wx = -Vn/R2;
    Wy = Ue*cos(Fi) + Ve/R1;
    Wz = Ue*sin(Fi) + Ve*tan(Fi)/R1;
    Awx = -(1/R1)*(dVn - Vh*Vn/R1); % dot_We
    Awy = (1/R2)*(dVe - Ue*sin(Fi)*Vn - Vh*Ve/R2); % dot_Wn
%     Awz = (1/R2)*(Ue*cos(Fi)*Vn + Nx*tan(Fi) + Vh*Wz + Ve*Vn/(R2*(cos(Fi))^2)); % dot_Wh
        Awz = (1/R2)*(Ue*cos(Fi)*Vn + (dVe + Vh*Ve/R2)*tan(Fi) + Ve*Vn/(R2*(cos(Fi))^2));
    % Расчет коэффициентов для матрицы F
    a1 = -W0^2 + Wy^2 + Wz^2;
    a2 = -(Wx*Wy - Awz);
    a4 = -(Wx*Wy + Awz);
    a5 = -W0^2 + Wx^2 + Wz^2;

    % Матрица F
    F = [0  0    1       0       0       0     0   0 0 0 0 0 0;
         0  0    0       1       0       0     0   0 0 0 0 0 0;
         a1 a2   0       2*Wz    0       Nz   -Ny  0 0 0 C1(1,1) C1(1,2) C1(1,3);
         a4 a5   -2*Wz   0      -Nz      0     Nx  0 0 0 C1(3,1) C1(3,2) C1(3,3);
         0  0    0       0       0       Wz   -Wy  C1(1,1) C1(1,2) C1(1,3) 0 0 0;
         0  0    0       0      -Wz      0     Wx  C1(2,1) C1(2,2) C1(2,3) 0 0 0;
         0  0    0       0       Wy     -Wx    0   C1(3,1) C1(3,2) C1(3,3) 0 0 0;
         0  0    0       0       0       0     0   0 0 0 0 0 0;
         0  0    0       0       0       0     0   0 0 0 0 0 0;
         0  0    0       0       0       0     0   0 0 0 0 0 0;
         0  0    0       0       0       0     0   0 0 0 0 0 0;
         0  0    0       0       0       0     0   0 0 0 0 0 0;
         0  0    0       0       0       0     0   0 0 0 0 0 0];



    % Матрица W
    Wsh = [wnNxo; wnNyo; wnNzo; wnWxo; wnWyo; wnWzo];
    
    % Матрица G
    G = [0       0       0       0       0       0;
         0       0       0       0       0       0;
         0       0       0       C1(1,1)       C1(1,2)       C1(1,3);
         0       0       0       C1(2,1)       C1(2,2)       C1(2,3);
         C1(1,1)       C1(1,2)       C1(1,3)       0       0       0;
         C1(2,1)       C1(2,2)       C1(2,3)       0       0       0;
         C1(3,1)       C1(3,2)       C1(3,3)       0       0       0;
         0       0       0       0       0       0;
         0       0       0       0       0       0;
         0       0       0       0       0       0;
         0       0       0       0       0       0;
         0       0       0       0       0       0;
         0       0       0       0       0       0];
   

    H = zeros(4,13);
    H(1,1) = 1;
    H(2,2) = 1;
    H(3,1) = -(Vh/R2 + Awx*tan(Fi));
    H(3,2) = -Awz;
    H(3,3) = 1;
    H(4,1) = -Vh/R1;
    H(4,4) = 1;

    dX = F*X0 + G*Wsh;
    X = X0 + dX*dt; % Вектор состояния системы

    x1 = X(1); x2 = X(2); x4 = X(4); x5 = X(5);
    dLm = x2/(R2*cos(Fi));
    dFi = x1/R1;
    % dVe = x4 - ((Vh/R2) + We*tan(Fi))*x1 - Wh*x2;
    % dVn = x5 - (Vh/R1)*x1;
    NP_ref1 = [dFi; dLm]; % Измерения БИНС
    
    % Wq = [9*10^-7; 9*10^-7; 9*10^-7; 0.0002; 0.0002; 0.0002];
    Wq = [11e-08; 11e-08; 11e-08; 0.001; 0.001; 0.001];
    % вторая норм, но СКО уходит слишком далеко
    Q = diag(([Wq].^2)/dt);

end