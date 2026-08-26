%% Генератор случайных возмущений
%%
global wnNx1 wnNy1 wnNz1 wnWx1 wnWy1 wnWz1 wnNx2 wnNy2 wnNz2 wnWx2 wnWy2 wnWz2 wnNx3 wnNy3 wnNz3 wnWx3 wnWy3 wnWz3
global wnFi1 wnLm1 wnVn1 wnVe1
nseed = randi(100000,1,22); % случайные целые числа
    
% Для БИНС 1
sNx1  = RandStream('mt19937ar','Seed',nseed(1)); % поток для моделирования ДЛУ
sNy1  = RandStream('mt19937ar','Seed',nseed(2)); % поток для моделирования ДЛУ
sNz1  = RandStream('mt19937ar','Seed',nseed(3)); % поток для моделирования ДЛУ
sWx1  = RandStream('mt19937ar','Seed',nseed(4)); % поток для моделирования ДУС
sWy1  = RandStream('mt19937ar','Seed',nseed(5)); % поток для моделирования ДУС
sWz1  = RandStream('mt19937ar','Seed',nseed(6)); % поток для моделирования ДУС
    
wnNx1 = GEN2(sNx1); wnNy1 = GEN2(sNy1); wnNz1 = GEN2(sNz1);
wnWx1 = GEN1(sWx1); wnWy1 = GEN1(sWy1); wnWz1 = GEN1(sWz1);

% Для БИНС 2
sNx2  = RandStream('mt19937ar','Seed',nseed(7)); % поток для моделирования ДЛУ
sNy2  = RandStream('mt19937ar','Seed',nseed(8)); % поток для моделирования ДЛУ
sNz2  = RandStream('mt19937ar','Seed',nseed(9)); % поток для моделирования ДЛУ
sWx2  = RandStream('mt19937ar','Seed',nseed(10)); % поток для моделирования ДУС
sWy2  = RandStream('mt19937ar','Seed',nseed(11)); % поток для моделирования ДУС
sWz2  = RandStream('mt19937ar','Seed',nseed(12)); % поток для моделирования ДУС

wnNx2 = GEN2(sNx2); wnNy2 = GEN2(sNy2); wnNz2 = GEN2(sNz2);
wnWx2 = GEN1(sWx2); wnWy2 = GEN1(sWy2); wnWz2 = GEN1(sWz2);

% Для БИНС 3
sNx3  = RandStream('mt19937ar','Seed',nseed(13)); % поток для моделирования ДЛУ
sNy3  = RandStream('mt19937ar','Seed',nseed(14)); % поток для моделирования ДЛУ
sNz3  = RandStream('mt19937ar','Seed',nseed(15)); % поток для моделирования ДЛУ
sWx3  = RandStream('mt19937ar','Seed',nseed(16)); % поток для моделирования ДУС
sWy3  = RandStream('mt19937ar','Seed',nseed(17)); % поток для моделирования ДУС
sWz3  = RandStream('mt19937ar','Seed',nseed(18)); % поток для моделирования ДУС

wnNx3 = GEN2(sNx3); wnNy3 = GEN2(sNy3); wnNz3 = GEN2(sNz3);
wnWx3 = GEN1(sWx3); wnWy3 = GEN1(sWy3); wnWz3 = GEN1(sWz3);

% Для ГНСС 1
sFi1  = RandStream('mt19937ar','Seed',nseed(19)); % поток для моделирования ГНСС_1(Fi)
sLm1  = RandStream('mt19937ar','Seed',nseed(20)); % поток для моделирования ГНСС_1(Lm)
sVn1  = RandStream('mt19937ar','Seed',nseed(21)); % поток для моделирования ГНСС_1(Vn)
sVe1  = RandStream('mt19937ar','Seed',nseed(22)); % поток для моделирования ГНСС_1(Ve)

wnFi1 = GEN4(sFi1); wnLm1 = GEN4(sLm1); wnVn1 = GEN3(sVn1); wnVe1 = GEN3(sVe1);

function [Xizm] = GEN1(s) % для датчиков ДУС
    m = 0;
    d = 10^-4;
    Xizm = m + d.*randn(s,1);
end
function [Xizm] = GEN2(s) % для датчиков ДЛУ
    m = 0;
    d = 10^-4;
    Xizm = m + d.*randn(s,1);
end
function [Xizm] = GEN3(s) % для скоростей ГНСС
    m = 0;
    d = 10^-2;
    Xizm = m + d.*randn(s,1);
end
function [Xizm] = GEN4(s) % для координат ГНСС 1
    m = 0;
    d = ((1)/111000*pi/180); % норм 7 для 1 схемы % для замкнутого попробовать 0.8
    Xizm = m + d.*randn(s,1);
end