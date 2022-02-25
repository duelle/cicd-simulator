import datetime
import json
import os
import pprint
import re
import shutil
import subprocess
import sys

import yaml

import multiprocessing as mp
import numpy as np
import pandas as pd
from pathlib import Path

from parser.qpme_output_parser import QPMEOutputParser


class SimulationExecutor:

    base_dir = r'/tmp'
    config_template = Path(__file__).parent / 'ci_auto.qpe'
    arrival_pattern = '#exp_arrival#'
    job_pattern = '1234567890'
    worker_pattern = '1234567891'
    duration_avg_pattern = '#duration_avg#'
    duration_sd_pattern = '#duration_sd#'

    default_cpu = 2
    default_ram = 4
    cpu = None
    ram = None


    # job_range = range(1, 41, 5)
    # job_range = [1]
    # worker_range = range(1, 20, 1)
    # worker_range = [1]
    # arrival_range = [0.000085415]
    # duration_range = [
    #     1,  # MIN
    #     183,  # Q25
    #     283,  # MEDIAN
    #     435.584,  # AVG
    #     566,  # Q75
    #     9282,  # MAX
    # ]
    # duration_sd_range = [410.8]

    @staticmethod
    def set_cpu(cpu):
        SimulationExecutor.cpu = cpu

    @staticmethod
    def set_ram(ram):
        SimulationExecutor.ram = ram

    @staticmethod
    def create_settings_from_array(settings_array: np.ndarray, iteration: int) -> {}:
        configs = {}
        i: int = 0

        for row in settings_array:
            configs[i] = {
                'jobs': str(int(row[0])),
                'workers': str(int(row[1])),
                'arrival': str(("%.17f" % row[2]).rstrip('0').rstrip('.')),
                'duration_avg': str(row[3]),
                'duration_sd': str(row[3]/10.0),  # str(row[4]),
                'cfg_iteration': iteration,
                'cfg_id': i,
            }
            i += 1
        return configs

    @staticmethod
    def create_config_files(configs):
        config_files = []
        for config_id in configs.keys():
            with open(SimulationExecutor.config_template, 'r') as f_src:
                config = configs[config_id]
                iteration = configs[config_id]['cfg_iteration']
                os.makedirs('/tmp/qpme_configs/', exist_ok=True)
                config_file_name = f'/tmp/qpme_configs/ci_cfg_{iteration}_{config_id}.qpe'
                log_file_name = f'{config_file_name}.log'
                with open(log_file_name, 'w') as f_dest_log:
                    json.dump(config, f_dest_log)
                    f_dest_log.write('\n')
                with open(config_file_name, 'w') as f_dest:
                    for line in f_src:
                        line = re.sub(SimulationExecutor.job_pattern, config['jobs'], line, count=1)
                        line = re.sub(SimulationExecutor.worker_pattern, config['workers'], line, count=1)
                        line = re.sub(SimulationExecutor.arrival_pattern, config['arrival'], line, count=1)
                        line = re.sub(SimulationExecutor.duration_avg_pattern, config['duration_avg'], line, count=1)
                        line = re.sub(SimulationExecutor.duration_sd_pattern, config['duration_sd'], line, count=1)
                        f_dest.write(line)
                config_files.append(os.path.abspath(config_file_name))
        return config_files

    @staticmethod
    def docker_run(config, verbose=False):
        if SimulationExecutor.cpu and SimulationExecutor.ram:
            cpu = SimulationExecutor.cpu
            ram = SimulationExecutor.ram
        else:
            cpu = SimulationExecutor.default_cpu
            ram = SimulationExecutor.default_ram

        docker_image = 'qpme_experiment:latest'
        process_timeout = 55
        process_killout = 5
        before_time = datetime.datetime.now()
        subprocess.run(['docker', 'run', '-m', f'{ram}G', '--cpus', f'{cpu}', '-v',
                        f'{SimulationExecutor.base_dir}/{config}:/tmp/experiment',
                        '-e', f'TIMEOUT={process_timeout}',
                        '-e', f'KILLOUT={process_killout}',
                        docker_image])
        after_time = datetime.datetime.now()
        time_diff = after_time - before_time
        if verbose:
            print(time_diff)
        return config, time_diff

    @staticmethod
    def run_docker_experiments(config_files):
        experiments = {}
        configs = []

        for cfg in config_files:
            filename = os.path.basename(cfg)
            f_name, f_ext = os.path.splitext(filename)
            current_config_dir = f'{SimulationExecutor.base_dir}/{f_name}'
            current_config_file = 'in.qpe'
            current_log_file = 'out.log'
            os.makedirs(current_config_dir, exist_ok=True)
            shutil.copy(cfg, f'{current_config_dir}/{current_config_file}')
            shutil.copy(f'{cfg}.log', f'{current_config_dir}/{current_log_file}')

            configs.append(f_name)

            experiments[f_name] = {
                'basedir': current_config_dir,
                'name': f_name,
                'config': current_config_file,
                'log': current_log_file,
                'stats': {}  # + Operational Law (build duration), Execution time (simulation)
            }

        pool = mp.Pool()
        timings = pool.map(SimulationExecutor.docker_run, configs)
        pool.close()

        for k, v in timings:
            experiments[k]['stats']['duration'] = v

        return experiments

    @staticmethod
    def parse_experiments(experiments: {}) -> pd.DataFrame:
        entry_set = [('config', ['name']),  # 0
                     ('duration', ['stats', 'duration']),  # 1
                     ('jobs', ['yaml', 'config', 'jobs']),  # 2
                     ('workers', ['yaml', 'config', 'workers']),  # 3
                     ('workers_meanTkPop', ['yaml', 'ordp', 'Workers', 'color', 'token', 'meanTkPop']),  # 4
                     ('ordp_jobs_meanTkPop', ['yaml', 'ordp', 'Jobs', 'color', 'token', 'meanTkPop']),  # 5
                     ('doqp_stage_meanTkPop', ['yaml', 'doqp', 'Stage', 'color', 'token', 'meanTkPop']),  # 6
                     ('qoqp_stage_meanTkPop', ['yaml', 'qoqp', 'Stage', 'color', 'token', 'meanTkPop']),  # 7
                     ('arrival_rate', ['yaml', 'queue', 'build_arrival', 'totArrivThrPut']),  # 8
                     ('stage_duration', ['yaml', 'probe', 'PT', 'color', 'token', 'meanST']),  # 9
                     ('stage_arrival_count', ['yaml', 'qoqp', 'Stage', 'color', 'token', 'arrivCnt']),  # 10
                     ('utilization', None),
                     ('build_duration', None),
                     ('credit_usage', None),
                     ]
        header = [entry[0] for entry in entry_set]

        data_rows = []

        for e in experiments:
            experiments[e]['yaml_file'] = 'out_parsed.yml'
            QPMEOutputParser(experiments[e]['basedir'], experiments[e]['log'], experiments[e]['yaml_file'])
            with open(f'''{experiments[e]['basedir']}/{experiments[e]['yaml_file']}''') as yaml_content:
                experiments[e]['yaml'] = yaml.safe_load(yaml_content)

            broken = False
            results = []

            for entry in entry_set:
                if entry[1]:
                    entry_path = entry[1]
                    entry_content = experiments[e]
                    for element in entry_path:
                        try:
                            entry_content = entry_content[element]
                        except KeyError:
                            broken = True
                            entry_content = 1
                            break

                    results.append(str(entry_content))

            # In case fields are not populated or the meanST property is negative, we mark the results as defective
            if broken or float(results[9] < 0):
                results.extend([10, sys.float_info.max, sys.float_info.max])

            else:
                # 1-(WorkerTokens/#Worker)
                results.append(1 - (float(results[4]) / float(results[3])))

                # TokenPop(Jobs/Stage)/#Jobs/ArrivalRate
                results.append((float(results[5]) + float(results[6])
                                + float(results[7]))/float(results[2])/float(results[8]))

                # 'credits': (mean stage duration * stage arrival count)
                results.append(float(results[9]) * float(results[10]))

            data_rows.append(results)

        df = pd.DataFrame(np.array(data_rows), columns=header)
        df.to_csv('/tmp/data_rows.csv')
        return df

    @staticmethod
    def do_run(param_array: np.ndarray, iteration: int) -> pd.DataFrame:
        # rows, columns = param_array.shape
        # print(f'Starting {rows} experiments.')
        settings = SimulationExecutor.create_settings_from_array(param_array, iteration)
        config_files = SimulationExecutor.create_config_files(settings)
        experiments = SimulationExecutor.run_docker_experiments(config_files)
        return SimulationExecutor.parse_experiments(experiments)


if __name__ == "__main__":
    # legacy_execution()

    input_array = np.array([
        [1, 1, 0.000085415, 283, 410.8],
        [1, 1, 0.000085415, 566, 410.8]
    ])
    result_df = SimulationExecutor.do_run(input_array)

    duration = list(result_df['build_duration'])
    cusage = list(result_df['credit_usage'])
    print(duration)
    print(cusage)
    #result_df.to_csv('/tmp/plot_data.csv', index=False)
    #pprint.pprint(result_df)
