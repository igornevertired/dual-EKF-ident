function[DX, afBI_b, WBI_b]=FX1(X,U,TIME)
global PAR PMAX T_THROTTLE T_ELEV T_RUD T_AIL TGLIDE
    m=PAR(1);
    fiP=PAR(2)*pi/180;
    Jxx=PAR(3);
    Jyy=PAR(4);
    Jzz=PAR(5);
    Jxy=PAR(6);

    Cy0=PAR(7);
    Cy_ALP=PAR(8);
    Cy_deltaV=PAR(9);
    Cy_fi=PAR(10);

    Cx0=PAR(11);
    A=PAR(12);
    B=PAR(13);
    Cx_deltaV=PAR(14);
    Cx_ALP_deltaV=PAR(15);
    Cx_ALP2_deltaV=PAR(16);
    Cx_fi=PAR(17);
    Cx_ALP_fi=PAR(18);
    Cx_ALP2_fi=PAR(19);

    mz0=PAR(20);
    mz_ALP=PAR(21);
    mz_ALP2=PAR(22);
    mz_deltaV=PAR(23);
    mz_fi=PAR(24);
    mz_Wz=PAR(25);
    mz_DALP=PAR(26);        

    Cz_BE=PAR(27);
    Cz_deltaN=PAR(28);

    mx_deltaN=PAR(29);
    mx_ALP_deltaN=PAR(30);
    mx_BE=PAR(31);
    mx_ALP_BE=PAR(32);
    mx_deltaE=PAR(33);
    mx_Wx=PAR(34);
    mx_ALP_Wx=PAR(35);
    mx_ALP2_Wx=PAR(36);
    mx_Wy=PAR(37);
    mx_ALP_Wy=PAR(38);

    my_BE=PAR(39);
    my_deltaN=PAR(40);
    my_Wx=PAR(41);
    my_ALP_Wx=PAR(42);
    my_ALP2_Wx=PAR(43);
    my_Wy=PAR(44);
    my_ALP_Wy=PAR(45);
    my_ALP2_Wy=PAR(46);
    my_DBE=PAR(47);

    xT=PAR(48);
    S=PAR(49);
    l=PAR(50);
    ba=PAR(51);
    fiST=PAR(52);
    ALPKR=PAR(53);
    GR=180.0/pi;
    R00=0.125;    
    PMAX=260000.0;    
    a=6378245.0;
    b=6356856.0;
    e2=(a^2-b^2)/a^2;
    Ue=7292115.0E-11;
    
    % Текущее состоояние
    Vx1=X(1);   Vy1=X(2);    Vz1=X(3);  % Земная скорость в ССК
    Wx1=X(4);   Wy1=X(5);    Wz1=X(6);  % Угловая скорость в ССК
    GAM=X(7);   PSI=X(8);    TET=X(9);  % Углы ориентации в ГСК
    Xg=X(10);   H=X(11);     Zg=X(12);  % Координаты в ГСК
    FI=X(13);   LAMD=X(14);             % Географические углы ориентации
    Vwx1=X(20); Vwy1=X(21);  Vwz1=X(22);% Скорость ветра в ССК 
    % Текущее положение органов управления
    deltaT=X(16);
    deltaV=X(17);
    deltaN=X(18);
    deltaE=X(19);
    % Матрица перехода от ГСК в ССК
    [Cgb] = C_gb(TET, GAM, PSI);

    % Модель гравитации и поля силы тяжести
    [Gg, R1, R2, GTg] = EARTHMODEL(H, FI, LAMD); 
    Gb=Cgb*Gg;
    % Воздушная скорость ЛА
    Vax1=Vx1-Vwx1;
    Vay1=Vy1-Vwy1;
    Vaz1=Vz1-Vwz1;
    Va=sqrt(Vax1^2+Vay1^2+Vaz1^2);
    ALPHA=-atan(Vay1/Vax1);
    BETA=asin(Vaz1/Va);
    % Перевод в градусы (для аэродинамики)
    ALP=ALPHA*GR+ALPKR;
    BE=BETA*GR;
    % Коэффициенты аэросил
    Cy=Cy0+Cy_ALP*ALP+Cy_deltaV*deltaV+Cy_fi*fiST;
    Cx=Cx0+A*Cy+B*Cy^2+(Cx_deltaV+Cx_ALP_deltaV*ALP+Cx_ALP2_deltaV*ALP^2)*deltaV+...	
		+(Cx_fi+Cx_ALP_fi*ALP+Cx_ALP2_fi*ALP^2)*fiST;
    Cz=Cz_BE*BE+Cz_deltaN*deltaN;
    % Скоростной напор           
    RHO =R00*((288.16-0.0066*H)/288.16)^4.255;
    V=sqrt(Vx1^2+Vy1^2+Vz1^2);
    q=0.5*RHO*V^2*S*norm(GTg);
    % Аэросилы в ЭСК
    Fx=Cx*q;
    Fy=Cy*q;
    Fz=Cz*q;
    % Аэросилы в ССК
    Fx1=Fx*cos(ALPHA)-Fy*sin(ALPHA);
    Fy1=Fx*sin(ALPHA)+Fy*cos(ALPHA);
    Fz1=Fz;   
    % Тяга
    P = deltaT*PMAX*(RHO/R00)^0.75;
    % Вектор абсолютной угловой скорости вращения Земли в ГСК
    WEI_g=[Ue*cos(FI);Ue*sin(FI);0];
    % Вектор абсолютной угловой скорости вращения Земли в ССК
    WEI_b=Cgb*WEI_g;
    % Вектор абсолютной угловой скорости вращения ССК в ССК
    WBI_b=[Wx1;Wy1;Wz1];
    % Вектор земной скорости в ССК
    VBE_b=[Vx1;Vy1;Vz1];
    % Радиус вектор в ГСК
    rg=[-R1*e2*sin(FI)*cos(FI);R1*(1-e2*(sin(FI))^2);0];
    % Переносное ускорение в ГСК
    APg=-cross(WEI_g,cross(WEI_g,rg));
    % Переносное ускорение в CСК
    APb=Cgb*APg;
    % Кориолисово ускорение в CСК
    AKb=-2*cross(WEI_b,VBE_b);
    % Вектор угловой скорости вращения ССК отн Земли в ССК
    WBE_b=WBI_b-WEI_b;
    % Вспомагательный массив ATemp
    ATb=-cross(WBE_b,VBE_b);
    % Динамика центра масс ЛА    
    dVx1=(1.0/m)*(P*cos(fiP)-Fx1)+APb(1)+AKb(1)+ATb(1)+Gb(1);
    dVy1=(1.0/m)*(P*sin(fiP)+Fy1)+APb(2)+AKb(2)+ATb(2)+Gb(2);
    dVz1=Fz1/m+APb(3)++ATb(3)+Gb(3);

    % Производные от аэродинамических углов
    dALP=-(dVy1*Vax1-dVx1*Vay1)/(Vax1^2+Vay1^2);
    dBE=(dVz1*(Vax1^2+Vay1^2+Vaz1^2)-Vz1*(Vax1*dVx1+Vay1*dVy1+Vaz1*dVz1))/(sqrt(Vax1^2+Vay1^2)*(Vax1^2+Vay1^2+Vaz1^2));
        
    % Текущие угловые скорости в ЭСК
    OMGx=WBE_b(1)*cos(ALPHA)-WBE_b(2)*sin(ALPHA);
    OMGy=WBE_b(1)*sin(ALPHA)+WBE_b(2)*cos(ALPHA);
    OMGz=WBE_b(3); 
    
    % Коэффициенты аэромоментов
    mx=(mx_deltaN+mx_ALP_deltaN*ALP)*deltaN+(mx_BE+mx_ALP_BE*ALP)*BE+mx_deltaE*deltaE+...
        +(mx_Wx+mx_ALP_Wx*ALP+mx_ALP2_Wx*ALP^2)*OMGx*l/(2.0*V)+(mx_Wy+mx_ALP_Wy*ALP)*OMGy*l/(2.0*V);
    my=my_BE*BE+my_deltaN*deltaN+(my_Wx+my_ALP_Wx*ALP+my_ALP2_Wx*ALP^2)*OMGx*l/(2.0*V)+...
        +(my_Wy+my_ALP_Wy*ALP+my_ALP2_Wy*ALP^2)*OMGy*l/(2.0*V)+my_DBE*dBE*l/(2.0*V);
    mz=mz0+mz_ALP*ALP+mz_ALP2*ALP^2+mz_deltaV*deltaV+mz_fi*fiST+mz_Wz*OMGz*ba/V+mz_DALP*dALP*ba/V+(xT-25.0)*Cy*0.01;
    % Аэромоменты в ЭСК
    Mx=mx*q*l;
    My=my*q*l;
    Mz=mz*q*ba;
    % Аэромоменты в ССК   
    Mx1=Mx*cos(ALPHA)+My*sin(ALPHA);
    My1=-Mx*sin(ALPHA)+My*cos(ALPHA);
    Mz1=Mz;
    
    % Угловые ускорения в ССК
    DWx1=(Jyy*Mx1+Jxy*My1+Jxy*(Jxx+Jyy-Jzz)*Wx1*Wz1+(Jyy^2-Jyy*Jzz+Jxy^2)*Wy1*Wz1)/(Jxx*Jyy-Jxy^2);
    DWy1=(Jxy*Mx1+Jxx*My1-(Jxx^2-Jxx*Jzz+Jxy^2)*Wx1*Wz1+Jxy*(Jxx+Jyy-Jzz)*Wy1*Wz1)/(Jxx*Jyy-Jxy^2);
    DWz1=(Mz1-(Jyy-Jxx)*Wx1*Wy1-Jxy*(Wy1^2-Wx1^2))/Jzz;
    
    % Скорость ЛА в ГСК
    DXg=Vx1*cos(PSI)*cos(TET)-Vy1*(cos(PSI)*sin(TET)*cos(GAM)-sin(PSI)*sin(GAM))+Vz1*(sin(PSI)*cos(GAM)+cos(PSI)*sin(TET)*sin(GAM));
    DH=Vx1*sin(TET)+Vy1*cos(TET)*cos(GAM)-Vz1*cos(TET)*sin(GAM);
    DZg=-Vx1*sin(PSI)*cos(TET)+Vy1*(cos(PSI)*sin(GAM)+sin(PSI)*sin(TET)*cos(GAM))+Vz1*(cos(PSI)*cos(GAM)-sin(PSI)*sin(TET)*sin(GAM));
    
    % Вектор угловой скорости вращения ГСК отн. Земли в ГСК
    WGE_g=[DZg/R1; DZg*tan(FI)/R1; -DXg/R2];
    % Вектор абсолютной угловой скорости вращения ГСК в ГСК
    WGI_g=WGE_g+WEI_g;    
    % Вектор абсолютной угловой скорости ГСК в ССК
    WGI_b=Cgb*WGI_g;
    
    % Вектор угловой скорости ЛА отн ГСК в ССК
    WBG_b = WBI_b - WGI_b;
%     P = WBI_b(1) - WGI_b(1);
%     R = WBI_b(2) - WGI_b(2);
%     Q = WBI_b(3) - WGI_b(3);

    % Производные от углов ориентации
    DPSI   = (WBG_b(2)*cos(GAM) - WBG_b(3)*sin(GAM)) / cos(TET);
    DTET   =  WBG_b(3)*cos(GAM) + WBG_b(2)*sin(GAM);
    DGAM   =  WBG_b(1) - DPSI*sin(TET);
    
    % Производные от географических углов ориентации
    DFI=DXg/R2;
    DLAMD=DZg/R1/cos(FI);
    
    Dd=0.0;
    if (TIME>TGLIDE)
        THETA=asin(DH/sqrt(DXg^2+DZg^2));
        THETATR=-3.0*pi/180.0;
        Dd = V * sin(THETA - THETATR);
    end
    
    % Производные от скоростей ветра
    DVwx1=0.0;
    DVwy1=0.0;
    DVwz1=0.0;
    
    % Органы управления
    DdeltaT=(U(1)-deltaT)/T_THROTTLE;
	DdeltaV=(U(2)-deltaV)/T_ELEV;
	DdeltaN=(U(3)-deltaN)/T_RUD;
	DdeltaE=(U(4)-deltaE)/T_AIL;
    
    % В режиме выравнивании
    DHFL=0.0;DEPS=0.0;DX1=0.0;
    if (H<=15.0)
        DHFL=-0.5*X(23);
        DEPS=X(23)-H;
        DX1=-10.0*X(25)+X(24);
    end
    
    % Вектор правой части системы диффур. движения ЛА
    DX=[dVx1,dVy1,dVz1,...
        DWx1,DWy1,DWz1,...
        DGAM,DPSI,DTET,...
        DXg,DH,DZg,...
        DFI,DLAMD,...
        Dd,...
        DdeltaT,DdeltaV,DdeltaN,DdeltaE,...
        DVwx1,DVwy1,DVwz1,...
        DHFL,DEPS,DX1]'; 
    
    % Для БИНС
    axb=(1.0/m)*(P*cos(fiP)-Fx1);
    ayb=(1.0/m)*(P*sin(fiP)+Fy1);
    azb=Fz1/m;
    afBI_b=[axb;ayb;azb];
    
end

%% МАТРИЦЫ ПЕРЕХОДОВ
% 1. Переход от ГСК в ССК
function [Cgb] = C_gb(TET, PH, PSI)

Cgb = zeros(3,3);

Cgb(1,1) =  cos(PSI) * cos(TET);
Cgb(1,2) =  sin(TET);
Cgb(1,3) = -sin(PSI) * cos(TET);

Cgb(2,1) = -cos(PSI)*sin(TET)*cos(PH)+sin(PSI)*sin(PH);
Cgb(2,2) =  cos(TET)*cos(PH);
Cgb(2,3) =  cos(PSI)*sin(PH)+sin(PSI)*sin(TET)*cos(PH);

Cgb(3,1) =  cos(PSI)*sin(TET)*sin(PH)+sin(PSI)*cos(PH);
Cgb(3,2) = -cos(TET)*sin(PH);
Cgb(3,3) =  cos(PSI)*cos(PH)-sin(PSI)*sin(TET)*sin(PH); 
end