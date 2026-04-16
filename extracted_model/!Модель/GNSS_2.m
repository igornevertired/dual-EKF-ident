function [NPgnss2, Vgnss2] = GNSS_2(Fi, Lm, Vn, Ve)
    global wnFi2 wnLm2 wnVn2 wnVe2
    NP1 = Fi + wnFi2;
    NP2 = Lm + wnLm2;
    NP4 = Vn + wnVn2;
    NP5 = Ve + wnVe2;
    NPgnss2 = [NP1; NP2; NP4; NP5];
    sko1 = 3; %м
    sko2 = 0.1; %м/с
    %Vgnss1 = [sko1/111000*pi/180; sko1/111000*pi/180; sko2; sko2];
    Vgnss2 = [6.27*10^-7; 6.27*10^-7; 0.1*10^-7; 0.1*10^-7];
end