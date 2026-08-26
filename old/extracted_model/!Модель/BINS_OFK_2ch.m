function [F, G, H, Q] = BINS_OFK_2ch(A1, C1, NP1, dt)
    % X - North; Y - East; Z - Hight(вниз)
    
    % Формирование исходных данных
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
    
    N = C2*A1;
    [Gg,Re,Rn,GTg] = EARTHMODEL(Alt,Fi,Lm);
    O33 = zeros(3,3); O23 = zeros(2,3); O32 = zeros(3,2);
    Ue = 7292115.0E-11;
    WF = ([Ue*cos(Fi); 0; -Ue*sin(Fi)] + [Ve/Re; -Vn/Rn; -Ve*tan(Fi)/Re]);
  
    % Матрица F
    F11 = -[0,     -WF(3), WF(2);
           WF(3),  0,    -WF(1);
          -WF(2),  WF(1), 0];
    
    F12 = [0,    -1/Re;
           1/Rn,  0;
           0,     tan(Fi)/Re];
        
    F13 = [Ue*sin(Fi),                       0;
           0,                                0;
           Ue*cos(Fi) + Ve/(Re*(cos(Fi))^2), 0];

    F21 = -[0,     -N(3),  N(2);
           N(3),   0,    -N(1)];

    F22 = [Vh/Rn,                        (-2*Ve*tan(Fi)/Re)-2*Ue*sin(Fi);
           (Ve*tan(Fi)/Re)+2*Ue*sin(Fi), (Vn*tan(Fi)+Vh)/Re];

    F23 = [(Ve^2/(Re*(cos(Fi))^2))-2*Ve*Ue*cos(Fi),                  0;
           (Vn*Ve/(Re*(cos(Fi))^2))+2*Vn*Ue*cos(Fi)-2*Vh*Ue*sin(Fi), 0];

    F32 = [1/Rn, 0;
           0,    1/(Re*cos(Fi))];

    F33 = [0,                           0;
           Ve*sin(Fi)/(Re*(cos(Fi))^2), 0];
    
    C23 = [C2(1,1) C2(1,2) C2(1,3);
           C2(2,1) C2(2,2) C2(2,3)];

    C33 = [C2(1,1) C2(1,2) C2(1,3);
           C2(2,1) C2(2,2) C2(2,3);
           C2(3,1) C2(3,2) C2(3,3)];

    F = [F11 F12 F13 O33 C33;
         F21 F22 F23 C23 O23;
         O23 F32 F33 O23 O23;
         O33 O32 O32 O33 O33;
         O33 O32 O32 O33 O33];
    
    % Матрица G
    G = [O33 C33;
         C23 O23;
         O23 O23;
         O33 O33;
         O33 O33];

    % Матрица H
    H = zeros(4,13);
    H(1,6) = 1;
    H(2,7) = 1;
    H(3,4) = 1;
    H(4,5) = 1;
    % H = zeros(2,13);
    % H(1,6) = 1;
    % H(2,7) = 1;

    %Wq = [7e-08; 7e-08; 7e-08; 10e-05; 10e-05; 10e-05]; % оптимальные коэффициенты для разомкнутого контура
    
    %Wq = [45e-10; 45e-10; 45e-10; 60e-07; 60e-07; 60e-07]; % для замкнутого контура нормас
    
    Wq = [20e-10; 20e-10; 20e-10; 25e-07; 25e-07; 25e-07]; % для замкнутого контура подбор

    % Иные вариации Wq
    %Wq = [7.7570e-08; 7.7570e-08; 7.7570e-08; 0.00035; 0.00035; 0.00035];
    %Wq = [1.8231e-15; 1.8231e-15; 1.8231e-15; 2.6678e-08; 2.6678e-08; 2.6678e-08];
    %Wq = [1e+01; 1e+01; 1e+01; 1e+01; 1e+01; 1e+01];
    %Wq = [1.8231e-10; 1.8231e-10; 1.8231e-10; 2.6678e-05; 2.6678e-05; 2.6678e-05];

    Q = diag((Wq.^2)/dt);

end