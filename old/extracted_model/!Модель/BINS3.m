function [Q_new, C3_new, NP_new, A_dlu] = BINS3(A, W, NP3, C3, Q3, DT, TIME, H_et, DH_et)
    % Измерения датчиков
    W_dus = DUS(W, TIME);
    A_dlu = DLU(A, TIME);

    % Вычисление
    [NP_new] = Navigation(A_dlu, C3, NP3, DT, H_et, DH_et);
    [C3_new, Q_new] = Orientation(W_dus, Q3, C3, NP3, DT, H_et, DH_et);
end

function [W_dus] = DUS(W, TIME)
    global dw_3 kmw_3 fiw_3 wnWx3 wnWy3 wnWz3
    % Характеристики шумов измерения ДУС
    mu_gyro = [wnWx3;
               wnWy3;
               wnWz3];
    dw = dw_3;
    % if TIME >= 400
    %     dw = -[0.6*pi/180*1/3600;
    %           0.6*pi/180*1/3600;
    %           0.6*pi/180*1/3600];
    % end

    Wp = fiw_3*W;
    W_dus = (eye(3) + kmw_3)*Wp + dw + mu_gyro;
     % W_dus = W + dw + mu_gyro;

end

function [A_dlu] = DLU(A, TIME)
    global da0_3 kma_3 fia_3 wnNx3 wnNy3 wnNz3
    mu_accel = [wnNx3;
                wnNy3;
                wnNz3];
    da = da0_3;
    % if TIME >= 400
    %     da = -[0.004;
    %           0.004;
    %           0.004];
    % end
    Ap = fia_3*A;
    A_dlu = (eye(3) + kma_3)*Ap + da + mu_accel;
 %   A_dlu = A + da + mu_accel;
end

function [NP_new] = Navigation(A_dlu, Cbn, NP3, dt, H_et, DH_et)
    Ue=7292115.0E-11;
    VBE_n=[NP3(1);NP3(2);NP3(3)];
    H=H_et;
    % H=NP1(4);
    FI=NP3(5);
    LAMD=NP3(6);

    % Вектор абсолютной угловой скорости вращения Земли в ГСК
    WEI_n=[Ue*cos(FI); Ue*sin(FI); 0];

    % EARTHMODEL
    [Gg, R1, R2] = EARTHMODEL(H, FI, LAMD);
    a=6378245.0;
    b=6356856.0;
    e2=(a^2-b^2)/a^2;
    rn=[-R1*e2*sin(FI)*cos(FI);R1*(1-e2*(sin(FI))^2);0];

    % Переносное ускорение в ГСК
    APn=-cross(WEI_n,cross(WEI_n,rn));

    % Кориолисово ускорение в CСК
    AKn=-2*cross(WEI_n,VBE_n);

    % Вектор угловой скорости вращения ССК отн Земли в ССК
    WGE_n=[VBE_n(3)/R1; VBE_n(3)*tan(FI)/R1; -VBE_n(1)/R2];

    % Вспомагательный массив ATemp
    ATn=-cross(WGE_n,VBE_n);

    % Преобразование показаний акселерометра в НСК через кватернион
    A = Cbn*A_dlu;

    % Динамика центра масс ЛА    
    DVBE_n = A + APn + AKn + ATn + Gg;  
    DH = VBE_n(2);
    DLAMD = VBE_n(3)/R1/cos(FI);
    DFI = VBE_n(1)/R2;
    dNP = [DVBE_n;DH;DFI;DLAMD]; % [Vn, Vh, Ve, H, Fi, Lm]

    % Интегрирование методом Эйлера
    NP_new = NP3 + dNP*dt;
    NP_new(4) = H_et; NP_new(2) = DH_et;
end

function [Cbn_new, Q_new] = Orientation(W_dus, Q1, Cbn_prev, NP3, dt, H_et, DH_et)
    x=1;y=2;z=3;
    Ue = 7292115.0E-11; % рад/сек
    VBE_n = [NP3(1);DH_et;NP3(3)];
    H=H_et;
    % H = NP3(4);
    FI = NP3(5);
    LAMD = NP3(6);

    % Вектор абсолютной угловой скорости вращения Земли в ГСК
    WEI_n = [Ue*cos(FI); Ue*sin(FI); 0];

    % Радиус вектор в ГСК
    [Gg, R1, R2] = EARTHMODEL(H, FI, LAMD);

    % Вектор угловой скорости вращения НСК отн Земли в НСК
    WNE_n = [VBE_n(z)/R1; VBE_n(z)*tan(FI)/R1; -VBE_n(x)/R2];

    % Вектор абсолютной угловой скорости вращения НСК 
    WNI_n = WNE_n + WEI_n;

    % Расчет матрицы переходы из НСК в ССК (через кватернионы)
    Anb = transpose(Cbn_prev);
    WNI_b = Anb*WNI_n;

    % Расчет абсолютной углововой скорости вращения ССК в ССК (WBNb)
    WBNb = W_dus - WNI_b;

    % Уравнение Пуассона
    QQQ = Q1(1)^2 + Q1(2)^2 + Q1(3)^2 + Q1(4)^2;
    DQ0 = 0.5*(-Q1(2)*WBNb(1) - Q1(3)*WBNb(2) - Q1(4)*WBNb(3) + Q1(1)*(1 - QQQ));
    DQ1 = 0.5*( Q1(1)*WBNb(1) - Q1(4)*WBNb(2) + Q1(3)*WBNb(3) + Q1(2)*(1 - QQQ));
    DQ2 = 0.5*( Q1(4)*WBNb(1) + Q1(1)*WBNb(2) - Q1(2)*WBNb(3) + Q1(3)*(1 - QQQ));
    DQ3 = 0.5*(-Q1(3)*WBNb(1) + Q1(2)*WBNb(2) + Q1(1)*WBNb(3) + Q1(4)*(1 - QQQ));

    % Интегрирование методом Эйлера
    Q_new(1) = Q1(1) + DQ0*dt;
    Q_new(2) = Q1(2) + DQ1*dt;
    Q_new(3) = Q1(3) + DQ2*dt;
    Q_new(4) = Q1(4) + DQ3*dt;

    % Матрица перехода из ССК в НСК (через кватернионы)
    Cnb = zeros(3);

    Cnb(1,1) = 1 - 2*(Q_new(3)^2 + Q_new(4)^2);
    Cnb(1,2) = 2*Q_new(2)*Q_new(3) + 2*Q_new(4)*Q_new(1);
    Cnb(1,3) = 2*Q_new(2)*Q_new(4) - 2*Q_new(3)*Q_new(1);

    Cnb(2,1) = 2*Q_new(2)*Q_new(3) - 2*Q_new(4)*Q_new(1);
    Cnb(2,2) = 1 - 2*(Q_new(2)^2 + Q_new(4)^2);
    Cnb(2,3) = 2*Q_new(3)*Q_new(4) + 2*Q_new(2)*Q_new(1);

    Cnb(3,1) = 2*Q_new(2)*Q_new(4) + 2*Q_new(3)*Q_new(1);
    Cnb(3,2) = 2*Q_new(3)*Q_new(4) - 2*Q_new(2)*Q_new(1);
    Cnb(3,3) = 1 - 2*(Q_new(2)^2 + Q_new(3)^2);

    Cbn_new = transpose(Cnb);
end