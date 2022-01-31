from pymoo.core.problem import Problem
from sim_runner.simulation_executor import SimulationExecutor

import numpy as np


class PipelineCostResourceProblem(Problem):

    def __init__(self, lower_limits: [], upper_limits: [], constraint_limit: float):
        self.__xl: [] = lower_limits
        self.__xu: [] = upper_limits
        self.__constraint_limit: float = constraint_limit

        super().__init__(n_var=5, n_obj=2, n_constr=1, xl=self.__xl, xu=self.__xu)

    def _evaluate(self, x, out, *args, **kwargs):
        results = SimulationExecutor.do_run(x)
        results['build_duration'] = results['build_duration'].astype(float)
        results['credit_usage'] = results['credit_usage'].astype(float)
        result_array = np.column_stack((results['build_duration'], results['credit_usage']))
        out["F"] = result_array


        results['utilization'] = results['utilization'].astype(float)
        out["G"] = self._constraint_calculation(results["utilization"])

    def _constraint_calculation(self, value):
        return value - self.__constraint_limit

