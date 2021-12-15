#!/usr/bin/env python3
import pprint

from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.factory import get_termination
from pymoo.optimize import minimize
from problem import PipelineCostResourceProblem

lower_limits = [1, 1, 0.000085415, 1, 410.8]
upper_limits = [40, 40, 0.000085415, 9282, 410.8]
constraint_limit = 0.99

problem = PipelineCostResourceProblem(lower_limits, upper_limits, constraint_limit)
algorithm = NSGA2(pop_size=2)
termination = get_termination("n_gen", 2)

res = minimize(problem, algorithm, termination, seed=1, save_history=True, verbose=True)
pprint.pprint(res.X)
pprint.pprint(res.F)
