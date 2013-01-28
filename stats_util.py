import numpy as np

def dmvnorm(x, mean, sigma):
    k = x.shape[0]
    part1 = np.exp(-0.5*k*np.log(2*np.pi))
    part2 = np.power(np.linalg.det(sigma),-0.5)
    dev = x - mean
    part3 = np.exp(-0.5*np.dot(np.dot(dev.transpose(), np.linalg.inv(sigma)), dev))
    return part1*part2*part3


def colMeans(X):
    col_num = X.shape[1]
    mean = np.zeros(col_num)
    for i in range(col_num):
        mean[i] = np.mean(X[:,i])
    return mean