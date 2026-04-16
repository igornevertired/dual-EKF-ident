function [Gg, R1, R2, GTg] = EARTHMODEL(H, FI, LAMD)    
    %% Параметры гравитационного поля Земли
    d00 = 39861679.0E+7;
    d20 = 175519.0E+20;
    Ue = 7292115.0E-11;
    a = 6378245.0;
    b = 6356856.0;
    e2 = (a^2-b^2)/a^2;

    %% Геоцентрическая широта
    SINFI = sin(FI);
    SINMU = e2*SINFI*cos(FI)/sqrt(1-(2*e2-e2^2)*SINFI^2);
    COSMU = (1-e2*SINFI^2)/sqrt(1-(2*e2-e2^2)*SINFI^2);
    MU = asin(SINMU);
    FIe = FI-MU;

    %% Геоцентрический радиус-вектор
    chi = sqrt(1-e2*SINFI^2);
    R1 = a/chi + H;
    R2 = a*(1-e2)/chi^3 + H;
    Xe = (a/chi+H)*cos(FI)*sin(LAMD);
    Ye = (a*(1-e2)/chi+H)*SINFI;
    Ze = (a/chi+H)*cos(FI)*cos(LAMD);
    r = sqrt(Xe^2+Ye^2+Ze^2);

    %% Проекции вектора гравитационного ускорения на местной вертикаль и перпендикулярную к ней ось
    Gr = -d00/(r^2)-3/2*d20/(r^4)*(3*sin(FIe)*sin(FIe)-1);
    Gfie = -3/2*d20/(r^4)*sin(2*FIe);

    Gn = Gr*COSMU+Gfie*SINMU;
    Gfi = -Gr*SINMU+Gfie*COSMU; 
    
    %% Гравитационное ускорение в ГСК
    Gg = [Gfi;Gn;0];

    %% Ускорение силы тяжести в ГСК
    GTn = Gn-r*Ue^2*cos(FIe)*cos(FI);
    %GTfi = Gfi+r*Ue^2*cos(FIe)*SINFI;%должна быть равна 0

    GTg = [0;GTn;0];
end