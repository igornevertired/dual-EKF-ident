function [xnew,xd, A, W]= RK4(FX1,time,dt,xx,u)
%% 1st call
[xd]=FX1(xx,u,time);
xa=xd*dt;
x=xx+0.5*xa;
t=time+0.5*dt;
%% 2nd call
[xd]=FX1(x,u,t);
q=xd*dt;
x=xx+0.5*q;
xa=xa+2.0*q;
%% 3rd call
[xd]=FX1(x,u,t);
q=xd*dt;
x=xx+q;
xa=xa+2*q;
time=time+dt;
%% 4th call
[xd, A, W]=FX1(x,u,time);
xnew=xx+(xa+xd*dt)/6.0;

% % Метод Эйлера, для проверки
% [xd, A, W]=FX1(xx,u,time);
% xnew=xx+xd*dt;
end