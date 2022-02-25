from optimization.nsga_two import NsgaTwo
from sim_runner.simulation_executor import  SimulationExecutor

SimulationExecutor.set_cpu(2)
SimulationExecutor.set_ram(12)
lower_limits = [  1, 1, 0.000085415,    1]
upper_limits = [40, 20, 0.000854150, 1800]
constraint_limit = 0.99
NsgaTwo(lower_limits=lower_limits, upper_limits=upper_limits,
        constraint_limit=constraint_limit,
        population_size=60, generations=15)
