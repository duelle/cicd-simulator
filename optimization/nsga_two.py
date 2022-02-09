#!/usr/bin/env python3
import pprint

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.factory import get_termination
from pymoo.operators.integer_from_float_operator import IntegerFromFloatMutation, IntegerFromFloatCrossover, \
    IntegerFromFloatSampling
from pymoo.optimize import minimize
from optimization.problem import PipelineCostResourceProblem
from pymoo.visualization.scatter import Scatter
from pymoo.factory import get_sampling, get_crossover, get_mutation
from pymoo.operators.mixed_variable_operator import MixedVariableSampling, MixedVariableMutation, MixedVariableCrossover


class NsgaTwo:

    def __init__(self, lower_limits: [], upper_limits: [], constraint_limit, population_size: int, generations: int):
        # lower_limits = [ 1,  1, 0.000085415,    1]
        # upper_limits = [40, 20, 0.000854150, 1800]

        mask = ["int", "int", "real", "int"]  # , "real"]

        sampling = MixedVariableSampling(mask, {
            "real": get_sampling("real_random"),
            "int": get_sampling("int_random")
        })

        crossover = MixedVariableCrossover(mask, {
            "real": get_crossover("real_sbx", prob=1.0, eta=3.0),
            "int": get_crossover("int_sbx", prob=1.0, eta=3.0)
        })

        mutation = MixedVariableMutation(mask, {
            "real": get_mutation("real_pm", eta=3.0),
            "int": get_mutation("int_pm", eta=3.0)
        })

        problem = PipelineCostResourceProblem(lower_limits, upper_limits, constraint_limit)
        algorithm = NSGA2(pop_size=population_size, sampling=sampling, mutation=mutation, crossover=crossover, eliminate_duplicates=True)
        termination = get_termination("n_gen", generations)

        res = minimize(problem,
                       algorithm,
                       termination,
                       seed=1,
                       save_history=True,
                       verbose=True,
                       )

        df = pd.DataFrame(PipelineCostResourceProblem.stack_array)
        df.columns = ['in_jobs',
                      'in_workers',
                      'in_arrival',
                      'duration_avg',
                      # 'in_duration_sd',
                      'iteration',
                      'config_name',
                      'duration',
                      'jobs',
                      'workers',
                      'workers_meanTkPop',
                      'ordp_jobs_meanTkPop',
                      'doqp_stage_meanTkPop',
                      'qoqp_stage_meanTkPop',
                      'arrival_rate',
                      'stage_duration',
                      'stage_arrival_count',
                      'utilization',
                      'build_duration',
                      'credit_usage',
                      'constraint']
        np.set_printoptions(precision=20)
        pd.set_option("display.precision", 20)
        df['in_arrival'] = pd.to_numeric(df['in_arrival'])
        df['in_arrival'] = df['in_arrival'].round(20)
        df['optimal'] = 0

        x_df = pd.DataFrame(res.X, columns=['in_jobs', 'in_workers', 'in_arrival', 'duration_avg'])
        x_df['in_arrival'] = pd.to_numeric(x_df['in_arrival'])
        x_df.in_arrival = x_df.in_arrival.round(20)

        optimal = []
        for index, row in x_df.iterrows():
            rindex = df[(df.in_jobs == row.in_jobs) & (df.in_workers == row.in_workers) & (df.in_arrival == row.in_arrival)].index
            cindex = df.optimal.index
            df.loc[rindex, 'optimal'] = 1
            # entry['optional'] = 1
            # df[(df.in_jobs == row.in_jobs) & (df.in_workers == row.in_workers) & (df.in_arrival == row.in_arrival)] = entry

        df.to_csv('/tmp/results.csv')

        print()
        print("res.X")
        pprint.pprint(res.X)
        print()
        print("res.F")
        pprint.pprint(res.F)
        # print()
        # print("res.G")
        # pprint.pprint(res.G)
        # print()
        # print("res.CV")
        # pprint.pprint(res.CV)


# plot = Scatter()
# plot.add(problem.pareto_front(), plot_type="line", color="black", alpha=0.7)
# plot.add(F, facecolor="none", edgecolor="red")
# plot.show()
#
# xl, xu = problem.bounds()
# plt.figure(figsize=(7, 5))
# plt.scatter(X[:, 0], X[:, 1], s=30, facecolors='none', edgecolors='r')
# plt.xlim(xl[0], xu[0])
# plt.ylim(xl[1], xu[1])
# plt.title("Design Space")
# plt.show()
#
# plt.figure(figsize=(7, 5))
# plt.scatter(F[:, 0], F[:, 1], s=30, facecolors='none', edgecolors='blue')
# plt.title("Objective Space")
# plt.show()

# print(res.X)
# print(res.F)
# print(res.pop.get("X"))
# print(res.history)

