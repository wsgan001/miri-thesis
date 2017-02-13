#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import sys, multiprocessing
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt

import numpy as np
from sklearn.cluster import DBSCAN

from cluster import cluster
import constants

def plot_data(data):
    fig=plt.figure()
    ax2d=fig.add_subplot(111)
    #ax3d=fig.add_subplot(111,projection="3d")

    xs=[];ys=[];zs=[]
    for point in data:
            xs.append(point[0])
            ys.append(point[1])
            #zs.append(point[2])
    ax2d.scatter(xs,ys)
    #ax3d.scatter(xs,ys,zs)
    
    ax2d.set_xlabel(constants._x_axis)
    ax2d.set_ylabel(constants._y_axis)

    #ax3d.set_xlabel(constants._x_axis)
    #ax3d.set_ylabel(constants._y_axis)
    #ax3d.set_zlabel(constants._z_axis)
    
    #ax3d.set_xlim([-0.1,1.1])
    #ax3d.set_ylim([-0.1,1.1])
    #ax3d.set_zlim([-0.1,1.1])

    plt.show()

def normalize_data(data):
    data=np.array(data)
    amax=1/(np.amax(data,axis=0).transpose())
    data=data*amax

    return data

def show_clustering(data, labels, core_samples_mask, n_clusters_):
    X=np.array(data)
    
    unique_labels = set(labels)
    colors = plt.cm.Spectral(np.linspace(0, 1, len(unique_labels)))
    plt_labels=[]
    for k, col in zip(unique_labels, colors):
        if k == -1:
            # Black used for noise.
            col = 'k'

        class_member_mask = (labels == k)

        xy = X[class_member_mask & core_samples_mask]
        lab, =plt.plot(xy[:, 0], xy[:, 1], 'o', markerfacecolor=col,
                 markeredgecolor=col, markersize=9, marker='x', label="Cluster {0}".format(k))
        plt_labels.append(lab)

        xy = X[class_member_mask & ~core_samples_mask]
        lab, =plt.plot(xy[:, 0], xy[:, 1], 'o', markerfacecolor=col,
                 markeredgecolor=col, markersize=9, marker='x')
        #plt_labels.append(lab)

    plt.title('Estimated number of clusters: %d' % n_clusters_)
    plt.xlabel(constants._x_axis_label)
    plt.ylabel(constants._y_axis_label)
    plt.ylim([-0.1,1.1])
    plt.xlim([-0.1,1.1])
    plt.legend(handles=plt_labels)
    plt.show()

def clustering(cdist, ranks, show_plot):

    #
    # 1. Preparing data
    #
    data=[]
    for cs in cdist:
        for k,v in cs.items():
            data.append([v[constants._x_axis],v[constants._y_axis]])
            #data.append([ v[constants._x_axis],
            #              v[constants._y_axis],
            #              v[constants._z_axis] ])

    normdata=normalize_data(data)
    #plot_data(data)

    #
    # 2. Perform clustering
    #
    db = DBSCAN(eps=constants._eps, min_samples=constants._min_samples).fit(normdata)
    core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
    core_samples_mask[db.core_sample_indices_] = True
    labels=db.labels_

    clustered_cs={}
    for l in labels: 
        clustered_cs.update({l:[]})

    label_index=0
    for cs in cdist:
        for k,v in cs.items():
            clustered_cs[labels[label_index]].append({k:v})
            label_index+=1

    n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)

    #
    # 3. Show plots 
    #
    if show_plot:
        show_plot_thread=multiprocessing.Process(
                target=show_clustering,
                args=(normdata, labels, core_samples_mask, n_clusters_))

        show_plot_thread.start()

    #
    # 4. Build up cluster objects with clustered data
    #
    cluster_set=[]
    for k in clustered_cs.keys():
        cluster_set.append(cluster(clustered_cs[k], ranks))

    return n_clusters_, cluster_set
