#!/usr/bin/env python

#simple abc rejector. samples parameter vector from uniform prior, simulates dataset and then compares simulated
#dataset with actual dataset and either rejects or accepts based on the euclidian distance between the two.
#we'll use Lotka-Voltera model(http://en.wikipedia.org/wiki/Lotka%E2%80%93Volterra_equation) -> get dataset
#with params a=b=1 and add gaussian noise
#also added a simple mcmc based on metropolis algorithm
#and a sequential monte carlo

from scipy import integrate
from scipy import array
from scipy.stats import uniform
from scipy.stats import norm
from scipy.spatial.distance import euclidean
from itertools import izip
import numpy as np
np.seterr(all='ignore')
import matplotlib.pyplot as plt
import random
import math
import stats_util as utils
from scipy.stats.mstats import mquantiles
import sys
import oscillators
from SimpleRepressilator import HillRepressilator
import Hopf as models
import time
import pickle

#global vars used throughout
epsilon = 5.0
data_points = 8
#times = (0, 10, 20, 30, 40, 50, 60, 70)
times = (11, 24, 39, 56, 75, 96, 119, 144)
steps = 100000
param_number = 4
eta = 0.

def summary(theta):
    from scipy.stats.mstats import gmean
    from scipy.stats.mstats import mode
    return gmean(theta), mode(theta)

#ode system for Lotka-Voltera model
def lv(X,t,theta):
    a = theta[0]
    b = theta[1]
    y = array([a*X[0] - X[0]*X[1], b*X[0]*X[1] - X[1]])
    return y
    
def dx_dt(X, t, th):
    kA = th[0]
    k2 = th[1]
    k3 = th[2]
    k4 = th[3]
    k5 = th[4]
    y = array([(kA- k4)*X[0] - k2*X[0]*X[1],
               -k3*X[1] + k5*X[2],
               k4*X[0] - k5*X[2]])
    return y
    
def generate_dataset(dx_dt, theta):
    dataset = np.zeros([data_points, 2])
    #init = np.array([2.0, 5.0, 3.0])
    init = np.array([1, 0.5])
    t = np.arange(0, 15, 0.1)
    X= integrate.odeint(dx_dt, init, t, args=(theta,),mxhnil=0,hmin=1e-20)
    for i in xrange(data_points):
        dataset[i] = create_datapoint(X[times[i]])
    return dataset

def generate_dataset_full(dx_dt, theta, init = np.array([1., 1., 1.])):
    t = np.arange(0., 15, 0.1)
    #init = np.array([1., 1., 1.])
    X = integrate.odeint(dx_dt, init, t, args=(theta,), mxstep=1000)
    return X

def generate_dataset_hp(theta):
    hp = HillRepressilator(*theta, n=3.)
    return hp.run(20)[:, 3:]

def generate_dataset_rep(theta):
    hp = HillRepressilator(alpha=theta[0],alpha0=theta[1], beta=theta[2], n=theta[3])
    ds = hp.run(T=50)
    dataset = np.zeros([data_points, 3])
    for ind, time in enumerate(times):
        dataset[ind, :] = ds[time, :]
    return dataset

def add_gaussian_noise_full(dataset):
    x_noise = np.random.normal(0, 0.5, np.shape(dataset))
    return dataset + x_noise

#returns the average distance between the signals in the 2 datasets
def fourier_distance(dataset, sim_dataset):
    sum_ferr = 0.
    signals = np.shape(dataset)[1]
    for i in xrange(signals):
        sum_ferr += oscillators.fourier_compare(dataset[:, i], sim_dataset[:, i])
    return sum_ferr / signals

def fitness(dataset, sim_dataset):
    global eta
    fitness = (eta*fourier_distance(dataset, sim_dataset) +
               (1-eta)*euclidean(dataset, sim_dataset))
    return fitness / 2.
    
#create a datapoint from 
def create_datapoint(data):
    data_n = len(data)
    datapoint = np.zeros(data_n)
    for i in xrange(data_n):
        datapoint[i] = data[i]
    return datapoint

def add_gaussian_noise(dataset):
    x_noise = np.random.normal(0, 0.5, data_points)
    for i in xrange(dataset.shape[1]):
        dataset[:,i] = dataset[:,i] + x_noise
    
    return dataset

def euclidian_distance(dataset, sim_dataset):
    sq_error = 0
    from scipy.spatial.distance import sqeuclidean
    for i in xrange(dataset.shape[1]):
        sq_error += sqeuclidean(sim_dataset[:,i],dataset[:,i])
    return sq_error

def rejector_algorithm(dx_dt, ds):
    naccepted = 0
    i = 0
    population = init_list()
    #draw sample from uniform prior in the interval [-10,10]
    while naccepted < 200:
        i += 1
        theta = np.random.uniform(-10,10,param_number)
        sim_dataset = generate_dataset(dx_dt,theta)
        error = euclidian_distance(ds, sim_dataset)
        print i, theta, error, naccepted
        if error <= epsilon:#accept
            naccepted += 1
            population = add_particle_to_list(population, theta)
    return population

def init_list(lst, times):
    for i in xrange(times):
        lst.append([])
        
def calc_a(sim_th, theta, sigma):
    prior_sim = uniform(-10,10)
    pth_sim = prior_sim.pdf(sim_th)
    pth = prior_sim.pdf(theta)
    jumping_dist_sim = norm(sim_th,sigma)
    prop_th = jumping_dist_sim.pdf(theta)
    jumping_dist = norm(theta,sigma)
    prop_simth = jumping_dist_sim.pdf(sim_th)
    likelihood = (0.1 * prop_th) / (0.1 * prop_simth)
    return min(1, likelihood)

def add_particle(population, sim_theta, theta, sigma):
    for p, sth, th in izip(population, sim_theta, theta):
        a = calc_a(sth, th, sigma)
        r = random.randint(0,1)
        if r <= a:
            th = sth
            p.append(th)
            
def draw_from_jumping(theta, sigma):
    sim_theta = []
    for pth in theta:
        sim_theta.append(np.random.normal(pth, sigma))
    return sim_theta

#simple mcmc algorithm creating a separate chain for each parameter
def mcmc(dx_dt, ds):
    naccepted = 0
    population = init_list()
    sigma = 5
    rej_streak = 0
    counter = 0
    #start of with random values for params taken from uniform prior
    theta = np.random.uniform(-5, 5, param_number)
    while counter < 50000:#steps:
        if len(population[1]) > 500: break
        counter += 1
        sim_theta = draw_from_jumping(theta, sigma)
        sim_dataset = generate_dataset(dx_dt, sim_theta)
        error = euclidian_distance(ds, sim_dataset)
        print counter, sim_theta, sigma, error, naccepted
        if error <= epsilon:
            rej_streak = 0
            sigma = 0.1
            add_particle(population, sim_theta, theta, sigma)
            naccepted += 1
        else:
            rej_streak += 1
            if rej_streak > 10:
                theta = np.random.uniform(-5, 5, param_number)
                rej_streak = 0
                sigma = 1
    print "steps taken ", counter
    return population

#returns a weighted distribution from population and associated weights
def calc_weighted_mean(population, weights):
    wsum = np.zeros(param_number)
    sum_weights = 0.0
    for i in xrange(len(population)):
        wsum += population[i]*weights[i]
        sum_weights += weights[i]
    return wsum / sum_weights

#returns an np.array with values drawn from uniform(start, end)
def draw_uniform(bounds):
    theta = np.array([])
    for i in xrange(param_number):
        theta = np.append(theta, np.random.uniform(bounds[i][0], bounds[i][1]))
    return theta

def get_pert_sigma(prev_population, sim_theta):
    M = (int) (len(prev_population) * 0.2)
    from scipy.spatial.distance import sqeuclidean
    distances = []
    for p in prev_population:
        distances.append(sqeuclidean(p, sim_theta))

    nearest = []
    indices = [i[0] for i in sorted(enumerate(distances), key=lambda x:x[1])]
    for index in indices[:M]:
        nearest.append(prev_population[index])
    return np.cov(np.vstack(nearest).T)

#to do: perturb particle before returning
def sample_from_previous(prev_population, weights):
    weighted_mu = calc_weighted_mean(prev_population, weights)
    sigma = np.cov(np.vstack(prev_population).T)
    particle = np.random.multivariate_normal(weighted_mu, sigma)
    pert_sigma = 2 * sigma#get_pert_sigma(prev_population, particle)
    pert_particle = np.random.multivariate_normal(particle, pert_sigma)
    return pert_particle

def calculate_weight(prev_population, prev_weights, sim_theta):
    wsum = 0.0
    sigma = np.cov(np.vstack(prev_population).T)
    mean = utils.colMeans(np.vstack(prev_population))
    for particle, weight in izip(prev_population, prev_weights):
        wsum += weight * utils.dmvnorm(sim_theta, mean, sigma)
    return 0.1 / wsum

def show_histogram(population):
    plt.figure(1)
    for pop in population:
        plt.hist(pop)
        plt.show()
        plt.figure(2)

def norm_weights(weights):
    sum_weights = math.fsum(weights)
    n_weights = [weight/sum_weights for weight in weights]
    return n_weights

def calc_pert_params(prev_population, weights):
    weighted_mu = calc_weighted_mean(prev_population, weights)
    sigma = np.cov(np.vstack(prev_population).T)
    return weighted_mu, sigma

def split_params(c_population):
    num_params = np.shape(c_population)[1]
    list_params = []
    init_list(list_params, num_params)
    for particle in c_population:
        for ind, item in enumerate(particle):
            list_params[ind].append(item)
    return list_params
            
#sequential monte carlo
def smc(dx_dt, ds, eps_seq):
    i = 0
    naccepted = 0
    t = 0
    populations = []
    weights = []
    current_weights = []
    current_population = []
    distances_prev = []
    cpopulation_append = current_population.append
    cweights_append = current_weights.append
    epsilon = eps_seq[0]
    prev_epsilon = eps_seq[0]
    steps = []
    while True:
    #for epsilon in eps_seq:
        print "==========population===========", t
        if t == 0:#if first population draw from prior
            while naccepted < 10:
                i += 1
                sim_theta = draw_uniform([[0, 500], [0, 5], [3, 8], [0, 5]])
                sim_dataset = generate_dataset_rep(sim_theta)
                error = euclidian_distance(sim_dataset,ds)
                print i, sim_theta, error, naccepted, epsilon
                if error < epsilon:
                    distances_prev.append(error)
                    naccepted += 1
                    cpopulation_append(sim_theta)
                    cweights_append(1)
        else: #draw from previous population
            while naccepted < 10:
                i += 1
                sim_theta = sample_from_previous(populations[t-1], weights[t-1])
                sim_dataset = generate_dataset_rep(sim_theta)
                error = euclidian_distance(sim_dataset,ds)
                print i, sim_theta, error, naccepted, epsilon
                if error <= epsilon:
                    distances_prev.append(error)
                    naccepted += 1
                    current_population.append(sim_theta)
                    wei = calculate_weight(populations[t-1], weights[t-1], sim_theta)
                    current_weights.append(wei)

        populations.append(current_population)
        weights.append(norm_weights(current_weights))
        epsilon = mquantiles(distances_prev, prob=[0.18, 0.25, 0.5, 0.75])[0]
        if prev_epsilon - epsilon < 0.5: break
        else: prev_epsilon = epsilon
        current_population = []
        current_weights = []
        distances_prev = []
        steps.append(i)
        i = 0
        t += 1
        naccepted = 0
    return populations, steps
    
def write_to_file(filename,theta):
    f = open(filename, 'w')
    f.write("theta\n")
    for th in theta:
        f.write(str(th) + ",")
        
def plot_solution(population, ds):
    ti = [t/10 for t in times]
    theta1 = np.array([1,1])
    plt.figure(1)
    theta = utils.colMeans(np.vstack(population))
    X0 = np.array([1, 0.5])
    t = np.arange(0, 15, 0.1)
    X= integrate.odeint(dx_dt, X0, t, args=(theta,))
    Y= integrate.odeint(dx_dt, X0, t, args=(theta1,))
    x,y = X.T
    x1,y1 = Y.T
    plt.figure(3)
    plt.subplot(211)
    plt.plot(t, x, 'r-', label='x(t)')
    plt.plot(t, x1,'g-',label='x(t))')
    plt.plot(t, ds[:, 0], marker='s', linestyle='', color='g')
    plt.subplot(212)
    plt.plot(t, y, 'b-', label='y(t)')
    plt.plot(t, y1, 'g-', label='y(t)')
    plt.plot(t, ds[:, 1], marker='^', linestyle='', color='g')
    plt.xlabel('time')
    plt.show()

def main():
    theta = [3.]
    ds = generate_dataset_hp(theta)
    ds = add_gaussian_noise_full(ds)
    populations = smc(dx_dt, ds, [300.])
    plt.plot(ds)
    plt.show()

def test():
    theta = [1, 1]
    ds = generate_dataset(dx_dt, theta)
    ds = add_gaussian_noise_full(ds)
    populations = smc(dx_dt, ds, [300.])
    plt.plot(ds)
    plt.show()
    
if __name__ == "__main__":
    orig_theta = [216., .216, 5., 2.]
    orig_ds = generate_dataset_rep(orig_theta)
    ds = add_gaussian_noise(np.copy(orig_ds))
    start_time = time.time()
    populations,steps = smc(lv, ds, [5000., 16.,12., 6., 5., 4.3])
    time_taken = time.time() - start_time
    
    f1 = open("population_smc_multi_lv.txt", "wb")
    f2 = open("steps_smc_multi_lv.txt", "wb")
    f3 = open("ds_smc_multi_lv.txt", "wb")
    f4 = open("time_smc_multi_lv", "wb")
    pickle.dump(populations, f1)
    pickle.dump(steps, f2)
    pickle.dump(ds, f3)
    pickle.dump(time_taken, f4)
    f1.close()
    f2.close()
    f3.close()
    f4.close()
	   
