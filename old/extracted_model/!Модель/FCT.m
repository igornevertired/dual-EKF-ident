%% ПРОГРАММА РЕШЕНИЯ ЗАДАЧИ БАЛАНСИРОВКИ
function[J]=FCT(BAL,HTR,VTR,THETATR,GAMTR,BETATR)
    global PAR PMAX    
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
    % Требуемые угловые скорости
    W1xTR=0.0;
    W1yTR=0.0;
    W1zTR=0.0;
    % Текущее положение органов управления
    deltaT=BAL(1);
    deltaV=BAL(3);
    deltaN=BAL(4);
    deltaE=BAL(5);
    % Текущее значение угла атаки
    ALPHA=BAL(2);
    % Текущее значение угла скольжения
    BETA=BETATR;
    % Текущее значение угла тангажа
    TET=ALPHA+THETATR;
    % Текущее значение угла крена
    GAM=GAMTR;
    % Перевод в градусы (для аэродинамики)
    ALP=ALPHA*GR+ALPKR;
    BE=BETA*GR;
    % Текущие скорости
    V=VTR;
    Vx1=V*cos(BETA)*cos(ALPHA);
    Vy1=-V*cos(BETA)*sin(ALPHA);
    Vz1=V*sin(BETA);
    % Текущие угловые скорости в ЭСК
    OMGx=W1xTR*cos(ALPHA)-W1yTR*sin(ALPHA);
    OMGy=W1xTR*sin(ALPHA)+W1yTR*cos(ALPHA);
    OMGz=W1zTR;   

    % Коэффициенты аэросил
    Cy=Cy0+Cy_ALP*ALP+Cy_deltaV*deltaV+Cy_fi*fiST;
    Cx=Cx0+A*Cy+B*Cy^2+(Cx_deltaV+Cx_ALP_deltaV*ALP+Cx_ALP2_deltaV*ALP^2)*deltaV+...	
		+(Cx_fi+Cx_ALP_fi*ALP+Cx_ALP2_fi*ALP^2)*fiST;
    Cz=Cz_BE*BE+Cz_deltaN*deltaN;

    % Скоростной напор
    G=9.81;        
    RHO =R00*((288.16-0.0066*HTR)/288.16)^4.255;
    q=0.5*RHO*V^2*S*G;    
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
    % Динамика центра масс ЛА
    dVx1=(1.0/m)*(P*cos(fiP)-Fx1)+W1zTR*Vy1-W1yTR*Vz1-G*sin(TET);
    dVy1=(1.0/m)*(P*sin(fiP)+Fy1)+W1xTR*Vz1-W1zTR*Vx1-G*cos(TET)*cos(GAM);
    dVz1=Fz1/m-W1xTR*Vy1+W1yTR*Vx1+G*cos(TET)*sin(GAM);
    
    % Производные от аэродинамических углов
    dALP=-(dVy1*Vx1-dVx1*Vy1)/(Vx1^2+Vy1^2);
    dBE=(dVz1*(Vx1^2+Vy1^2+Vz1^2)-Vz1*(Vx1*dVx1+Vy1*dVy1+Vz1*dVz1))/(sqrt(Vx1^2+Vy1^2)*(Vx1^2+Vy1^2+Vz1^2));
    
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
    
    %% Члены критерия
    SIGF(1)=dVx1*m;
    SIGF(2)=dVy1*m;
    SIGF(3)=dVz1*m;
    
    SIGF(4)=Jyy*Mx1+Jxy*My1+Jxy*(Jxx+Jyy-Jzz)*W1xTR*W1zTR+(Jyy^2-Jyy*Jzz+Jxy^2)*W1yTR*W1zTR;
    SIGF(5)=Jxy*Mx1+Jxx*My1-(Jxx^2-Jxx*Jzz+Jxy^2)*W1xTR*W1zTR+Jxy*(Jxx+Jyy-Jzz)*W1yTR*W1zTR;
    SIGF(6)=Mz1-(Jyy-Jxx)*W1xTR*W1yTR-Jxy*(W1yTR^2-W1xTR^2);
    

    %% Критерий
%    J=SIGF(1)^2+SIGF(2)^2+SIGF(3)^2+SIGF(4)^2+SIGF(5)^2+SIGF(6)^2;
    J=SIGF(1)^2+SIGF(2)^2+SIGF(6)^2;   
end
