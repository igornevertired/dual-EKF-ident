function [DdeltaT,DdeltaV] = GLCAPTURE(X)
global VTR 
    %% Оценка состояния ЛА
    V=X(10);
    DV=X(11);
    Wz=X(3);
    THETA=X(13);
    d=X(14);
    THETATR=-3.0*pi/180;
    %% Коэффициента автопилота
    K_ELEV_W= 16.714542;
    K_ELEV_THETA = -5.069737;
    K_ELEV_d = 0.472349;
    K_THROTTLE_V = 1.124095;
    K_THROTTLE_DV = -12.788234;
    K_ELEV_V = 1.264112;
    %% Законы управления
    DdeltaT = K_THROTTLE_V * (VTR - V) + K_THROTTLE_DV * DV;
    DdeltaV = K_ELEV_W * Wz * 57.3 + K_ELEV_THETA * (THETATR-THETA)*57.3 + K_ELEV_d*d+ K_ELEV_V*(VTR - V);    
end