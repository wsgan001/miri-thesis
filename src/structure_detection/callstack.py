#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import logging
import numpy
import random
import constants
from delta_calculation import get_cost

class call(object):
    def __init__(self, line, call, call_file, callstack):
        self.call=call
        self.line=int(line)
        self.my_callstack = callstack
        self.call_file = call_file
        self.mpi_call = "MPI_" in call

    def get_signature(self):
        return "{0}{1}".format(
                self.call, 
                str(self.line))

    def __eq__(self, other):
        if other == None:
            return False
        else:
            return  self.call==other.call and \
                    self.line == other.line and \
                    not self.mpi_call


    def __str__(self):
        val = "{0} ({1})".format(self.call, self.line)
        return val

class callstack(object):
    def __init__(self, rank, instant, calls):
        self.common_with_prev = None
        self.rank=rank
        self.repetitions=1
        self.instants=[int(instant)] # TODO: Classify in ranks
        self.instants_distances=[]
        self.instants_distances_mean=None
        self.instants_distances_median=None
        self.delta=None
        self.cluster_id=None
        self.compacted_ranks=[rank]
        self.condition_level = None
        self.reduced=False
        self.calls=calls
        self.metrics={
                "mpi_duration":0,
                "mpi_duration_merged":[],
                "mpi_duration_mean":0,
                "mpi_duration_stdev":0,
                "mpi_duration_sum":0,
                "mpi_duration_percent":0,
                "mpi_cycles":0,
                "mpi_cycles_merged":[],
                "mpi_cycles_mean":0
        }

        for call in calls:
            call.my_callstack = self

    @classmethod
    def from_trace(cls, rank, instant, lines, calls, files):
        assert len(lines)==len(calls), "#lines and #calls must be equal."

        calls_obj = []
        for i in range(0, len(lines)):
            calls_obj.append(call(int(lines[i]), calls[i], files[i], None))

        return cls(rank, instant, calls_obj)

    def get_all_ranks(self):
        return list(set(self.compacted_ranks))

    def get_line_at_level(self, level):
        return self.calls[level].line

    def get_signature(self):
        signature=""
        for call in self.calls:
            signature += call.get_signature()
        return str(self.rank)+"#"+signature

    def merge(self, other):
        assert self.get_signature() == other.get_signature()
        self.repetitions+=1
        self.instants.extend(other.instants)

        self.metrics["mpi_duration_merged"].append(
                other.metrics["mpi_duration"])
 
    def calc_reduce_info(self):
        self.reduced=True
        if self.repetitions == 1: return

        self.instants.sort()
        self.instants_distances=self.__get_distances(self.instants)
        self.instants_distances_median=numpy.median(self.instants_distances)
        self.instants_distances_mean=numpy.mean(self.instants_distances)

        self.metrics["mpi_duration_mean"]=numpy.mean(
            self.metrics["mpi_duration_merged"])
        self.metrics["mpi_duration_stdev"]=numpy.median(
            self.metrics["mpi_duration_merged"])
        self.metrics["mpi_duration_sum"]=sum(
            self.metrics["mpi_duration_merged"])
        self.metrics["mpi_duration_percent"]=\
            self.metrics["mpi_duration_sum"]/constants.TOTAL_TIME*100

    def is_above_delta(self, delta, total_time):
        if self.repetitions == 1: return False
        cost=get_cost(self.repetitions, 
                total_time, 
                self.instants_distances_mean, 
                delta)
        return cost > 0

    def get_instants_dist_median(self):
        return numpy.median(self.instants_distances)

    def get_instants_dist_mean(self):
        return numpy.mean(self.instants_distances)

    def same_flow(self, other):
        return self.get_signature().split("#")[1] == \
                other.get_signature().split("#")[1]

    def get_call_of_func(self, func_name):
        for call_obj in self.calls:
            if call_obj.call == func_name:
                return call_obj
 
    def __get_distances(self, times):
        dist=[]
        for i in range(1,len(times)):
            dist.append(times[i]-times[i-1])
        return dist
       
    def __eq__(self, other):
        return self.get_signature() == other.get_signature()

    def __lt__(self, other):
        assert self.reduced == True and other.reduced == True
        for call_i in range(min(len(self.calls), len(other.calls))):
            if not self.calls[call_i] == other.calls[call_i]:
#               assert self.calls[call_i].call == other.calls[call_i].call,\
#                        "{0} < {1}".format(self, other)
                if not self.calls[call_i].call == other.calls[call_i].call:
                    logging.warn("Same code line jumps to more than one target"\
                            " locations. Assuming arbitrary order.")
                return self.calls[call_i].line < other.calls[call_i].line

    def __gt__(self, other):
        assert self.reduced == True and other.reduced == True
        for call_i in range(min(len(self.calls), len(other.calls))):
            if self.calls[call_i] != other.calls[call_i]:
                assert self.calls[call_i].call == other.calls[call_i].call
                return self.calls[call_i].line > other.calls[call_i].line

    def __le__(self, other):
        assert self.reduced == True and other.reduced == True
        for call_i in range(min(len(self.calls), len(other.calls))):
            if self.calls[call_i] != other.calls[call_i]:
                assert self.calls[call_i].call == other.calls[call_i].call
                return self.calls[call_i].line <= other.calls[call_i].line

    def __ge__(self, other):
        assert self.reduced == True and other.reduced == True
        for call_i in range(min(len(self.calls), len(other.calls))):
            if self.calls[call_i] != other.calls[call_i]:
                assert self.calls[call_i].call == other.calls[call_i].call
                return self.calls[call_i].line >= other.calls[call_i].line

    def __and__(self, other):
        result = []
        for call_i in range(min(len(self.calls), len(other.calls))):
            if self.calls[call_i] == other.calls[call_i]:
                result.append(self.calls[call_i])
            else:
                break

        result = callstack(0, 0, result)
        if len(result) > 0:
            result.rank = self.rank
            result.repetitions = self.repetitions
            result.instants = self.instants
            result.instants_distances = self.instants_distances
            result.instants_distances_mean = self.instants_distances_mean
            result.instants_distances_median = self.instants_distances_median
            result.delta = self.delta
            result.cluster_id = self.cluster_id
            result.compacted_ranks = self.compacted_ranks
            result.condition_level = self.condition_level
            result.reduced = self.reduced
            result.metrics = self.metrics
            result.common_with_prev = self.common_with_prev

        return result

    def __sub__(self, other):
        result = []
        for s_call in self.calls:
            if not s_call in other.calls:
                result.append(s_call)

        result = callstack(0, 0, result)
        if len(result) > 0:
            result.rank = self.rank
            result.repetitions = self.repetitions
            result.instants = self.instants
            result.instants_distances = self.instants_distances
            result.instants_distances_mean = self.instants_distances_mean
            result.instants_distances_median = self.instants_distances_median
            result.delta = self.delta
            result.cluster_id = self.cluster_id
            result.compacted_ranks = self.compacted_ranks
            result.condition_level = self.condition_level
            result.reduced = self.reduced
            result.metrics = self.metrics
            result.common_with_prev = self.common_with_prev

        return result

    def __add__(self, other):
        calls = self.calls
        calls.extend(other.calls)

        result = callstack(0,0, calls)

        if len(result) > 0:
            result.rank = self.rank
            result.repetitions = self.repetitions
            result.instants = self.instants
            result.instants_distances = self.instants_distances
            result.instants_distances_mean = self.instants_distances_mean
            result.instants_distances_median = self.instants_distances_median
            result.delta = self.delta
            result.cluster_id = self.cluster_id
            result.compacted_ranks = self.compacted_ranks
            result.condition_level = self.condition_level
            result.reduced = self.reduced
            result.metrics = self.metrics
            result.common_with_prev = self.common_with_prev

        return result

    def __getitem__(self, key):
        return self.calls[key]

    def __len__(self):
        return len(self.calls)
         
    def __str__(self):
        val = "R:{0} IT:{1} -".format(
                self.compacted_ranks, 
                self.repetitions,
                self.condition_level)
        for call in self.calls:
            val += ">{0}({1})".format(call.call, call.line)
        return val

    def __delitem__(self, index):
        del self.calls[index]