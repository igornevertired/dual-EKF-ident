global PAR PMAX T_THROTTLE T_ELEV T_RUD T_AIL
PAR=  [1.700E05    5            8.400E06     3.000E07     2.300E07  ... 
    -0.700E06    0.00E00      0.093E00     0.006E00     0.145E-01 ...
     0.586E-01  -0.518E-01    0.876E-01   -1.920E-04    8.110E-05 ...
     0.000E00   -2.330E-03    5.020E-04   -1.340E-05    0.515E-01 ...
    -3.215E-02   5.300E-04   -0.185E-01   -0.465E-01   -1.290E01  ...
    -5.000E00   -0.152E-01   -0.344E-02   -0.064E-02    5.200E-05 ...
    -0.145E-02  -1.700E-04   -0.120E-02   -0.430E00    -3.833E-03 ...
     1.133E-03  -0.075E00    -8.250E-03   -0.280E-02   -0.002E00  ...
     0.020E00    0.215E-01   -1.300E-03   -0.300E00     8.330E-04 ...
     8.700E-05   000E00       2.500E01     0.330E03     4.806E01  ...
     7.570E00   -3.9026       3.0];
PMAX = 260000.0;
% постоянные времени ОУ
T_THROTTLE = 5.0;
T_ELEV=0.1;
T_RUD=1.0/20.2;
T_AIL=1.0/20.2;


%{
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
 %}