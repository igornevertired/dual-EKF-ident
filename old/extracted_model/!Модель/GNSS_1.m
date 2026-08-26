function [NPgnss1, Vgnss1] = GNSS_1(Fi, Lm, Vn, Ve)
    global wnFi1 wnLm1 wnVn1 wnVe1
    NP1 = Fi + wnFi1;
    NP2 = Lm + wnLm1;
    NP4 = Vn + wnVn1;
    NP5 = Ve + wnVe1;
    NPgnss1 = [NP1; NP2; NP4; NP5];
    sko1 = 0.5; %м % (для 1 схемы: 0.5) (для 2 схемы: 3)
    sko2 = 0.1; %м/с (для 1 схемы: 0.1) (для 2 схемы: 0.05)

    Vgnss1 = [sko1/111000*pi/180; sko1/111000*pi/180; sko2; sko2];
    % Vgnss1 = [6.27*10^-7; 6.27*10^-7; 0.1*10^-7; 0.1*10^-7];
end