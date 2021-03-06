#!/usr/bin/python

from scipy import integrate
from scipy import array
import matplotlib.pyplot as plt
import numpy as np
import math
import abcinfer_multi as abc
import numpy as np
import stats_util as utils
import sys
times = (1.1, 2.4, 3.9, 5.6, 7.5, 9.6, 11.9,14.4)
datapoints = 8

def generate_data():
    th = 1
    dataset = np.zeros([datapoints, 2])
    for i in range(datapoints):
        dataset[i] = np.array([np.cos(times[i]), np.cos(times[i] + th)])
    return dataset

def generate_dataset_full():
    th = 1
    t = np.arange(0, 15, 0.1)
    dataset = np.zeros([len(t), 2])
    for ind, time in enumerate(t):
        dataset[ind] = np.array([np.cos(time), np.cos(time + th)])
    return dataset
    

def dn_dt(N, t, theta):
    k = theta[0]
    a = theta[1]
    n = array([k * N[1] * N[0], -a * k * N[1] * N[0]])
    return n

def dX_dt(X, t):
    ka = 3.4
    k2 = 1
    k3 = 1
    k4 = 1
    k5 = 1
    y = array([(ka-k4)*X[0] - k2*X[0]*X[1], -k3*X[1] + k3*X[2], k4*X[0] - k5*X[2]])
    return y

def dx_dt(X,t,th):
    a1 = th[0]
    a2 = th[1]
    b1 = th[2]
    b2 = th[3]
    b3 = th[4]
    c1 = th[5]
    d1 = th[6]
    d2 = th[7]
    y = array([((a1 * X[0]**2) / (b1 + X[0]**2 + c1 * X[1])) - d1 * X[1],
               ((a2 * X[0]**2) / (b2 + b3 * X[0]**2)) - d2 * X[0]])
    return y

#ode system for Lotka-Voltera model
def dy_dt(X,t,theta):
    a = theta[0]
    b = theta[1]
    y = array([a*X[0] - X[0]*X[1], b*X[0]*X[1] - X[1]])
    return y

def plot_solution(population):
    #theta1 = np.array([1,1])
    theta = []
    plt.figure(1)
    for p in population:
        m = math.fsum(p) / len(p)
        print m
        theta.append(m)
        plt.hist(p)
        plt.figure(2)
    print theta
    X0 = np.array([1, 0.5])
    t = np.arange(0, 15, 0.1)
    X= integrate.odeint(dx_dt, X0, t, args=(theta,))
    #Y= integrate.odeint(dx_dt, X0, t, args=(theta1,))
    x,y = X.T
    #x1,y1 = Y.T
    plt.figure(1)
    plt.subplot(211)
    plt.plot(t, x, 'r-', label='x(t)')
    plt.plot(t,np.cos(t),'g-',label='x(t))')
    plt.subplot(212)
    plt.plot(t, y, 'b-', label='y(t)')
    plt.plot(t, np.cos(t+1), 'g-', label='y(t)')
    plt.xlabel('time')
    plt.show()

def dist(nds, ds):
    sum_dist = 0.0
    for i in range(len(ds)):
        err = (nds[i][0] - ds[i][0])**2 + (nds[i][1] - ds[i][1])**2
        print "err: ", err
        sum_dist += err
    print "sum_dist: ", sum_dist
    return sum_dist

#simple clock model with 2 genes A,B
def dA_dt(A, t, theta):
    k = theta[0]
    c = theta[1]
    b = theta[2]
    d = theta[3]
    b1 = theta[4]
    p = theta[5]
    k1 = theta[6]
    d1 = theta[7]
    y = array([(A[1]*A[0] / (k + A[0])) - c / (b + A[1]) - d*A[0],
               (b1*A[0]**p / (k1 + A[0]**p) - d1*A[1])])
    return y


def main():
    X0 = [1, 0.5]
    t = np.arange(0, 15, 0.1)
    ds = generate_data()
    populations = abc.smc(dx_dt, ds, [700.0])
    last_population = populations[:-1]
    theta = utils.colMeans(np.vstack(last_population))
    X = integrate.odeint(dx_dt, X0, t, args=(theta,))
    plt.plot(t,X)
    plt.show()
    
if __name__ == "__main__":
    main()
    
    
    

    
    
    
