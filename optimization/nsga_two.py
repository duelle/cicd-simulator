#!/usr/bin/env python3
import pprint

from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.factory import get_termination
from pymoo.optimize import minimize
from problem import PipelineCostResourceProblem
from pymoo.visualization.scatter import Scatter
from pymoo.factory import get_sampling, get_crossover, get_mutation
from pymoo.operators.mixed_variable_operator import MixedVariableSampling, MixedVariableMutation, MixedVariableCrossover

lower_limits = [1, 1, 0.000085415, 1, 410.8]
#upper_limits = [40, 40, 0.000085415, 9282, 410.8]
upper_limits = [2, 2, 0.000085417, 2, 410.81]
constraint_limit = 0.98

problem = PipelineCostResourceProblem(lower_limits, upper_limits, constraint_limit)
algorithm = NSGA2(pop_size=4)
termination = get_termination("n_gen", 5)

mask = ["int", "int", "real", "int", "real"]
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

res = minimize(problem,
               algorithm,
               termination,
               sampling=sampling,
               crossover=crossover,
               mutation=mutation,
               seed=1,
               save_history=True,
               verbose=True)


# pprint.pprint(res.X)
# pprint.pprint(res.F)

plot = Scatter()
plot.add(problem.pareto_front(), plot_type="line", color="black", alpha=0.7)
plot.add(res.F, facecolor="none", edgecolor="red")
plot.show()

print(res.X)
print(res.F)
print(res.pop.get("X"))
# print(res.history)
