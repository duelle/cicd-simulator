import datetime
import json
import os
import pprint
import re
import shutil
import subprocess

import matplotlib.pyplot as plt
import multiprocessing as mp
import numpy as np
import pandas as pd
import yaml

from parser.qpme_output_parser import QPMEOutputParser

config_template = 'ci_auto.qpe'

arrival_pattern = '#exp_arrival#'
job_pattern = '1234567890'
worker_pattern = '1234567891'
duration_avg_pattern = '#duration_avg#'
duration_sd_pattern = '#duration_sd#'

job_range = range(1, 6, 2)
worker_range = range(1, 6, 2)
arrival_range = [0.000085415]
duration_avg_range = [437]
duration_sd_range = [410]

base_dir = r'/tmp'


def create_settings():
    configs = {}
    i = 0
    for job_value in job_range:
        for worker_value in worker_range:
            for arrival_value in arrival_range:
                for duration_avg_value in duration_avg_range:
                    for duration_sd_value in duration_sd_range:
                        configs[i] = {
                            'jobs': str(job_value),
                            'workers': str(worker_value),
                            'arrival': str(("%.17f" % arrival_value).rstrip('0').rstrip('.')),
                            'duration_avg': str(duration_avg_value),
                            'duration_sd': str(duration_sd_value),
                        }
                        i += 1
    return configs


def create_config_files(configs):
    config_files = []
    for config_id in configs.keys():
        with open(config_template, 'r') as f_src:
            config = configs[config_id]
            os.makedirs('/tmp/qpme_configs/', exist_ok=True)
            config_file_name = f'/tmp/qpme_configs/ci_cfg_{config_id}.qpe'
            log_file_name = f'{config_file_name}.log'
            with open(log_file_name, 'w') as f_dest_log:
                # pprint.pprint(config, stream=f_dest_log)
                # f_dest_log.write(json.dumps(config))
                json.dump(config, f_dest_log)
                f_dest_log.write('\n')
            with open(config_file_name, 'w') as f_dest:
                for line in f_src:
                    line = re.sub(job_pattern, config['jobs'], line, count=1)
                    line = re.sub(worker_pattern, config['workers'], line, count=1)
                    line = re.sub(arrival_pattern, config['arrival'], line, count=1)
                    line = re.sub(duration_avg_pattern, config['duration_avg'], line, count=1)
                    line = re.sub(duration_sd_pattern, config['duration_sd'], line, count=1)
                    f_dest.write(line)
            config_files.append(os.path.abspath(config_file_name))
    return config_files


def run_experiments(config_files):
    simqpn_cwd = '/opt/qpme'

    for cfg in config_files:
        print(f'>> Begin: Processing config {cfg}.')
        before_time = datetime.datetime.now()
        results = subprocess.run(['./SimQPN.sh', '-r', 'batch', cfg], capture_output=True, cwd=simqpn_cwd, timeout=360)
        after_time = datetime.datetime.now()
        # time.sleep(5)
        time_diff = after_time - before_time
        log_file = f'{cfg}.log'
        with open(log_file, 'a') as log_out:
            log_out.write(f'return_code: {results.returncode}\n')
            print(f'  Return code: {results.returncode}')

            log_out.write(f'processing_time: {time_diff}\n')
            print(f'  SimQPN took {time_diff} to run this configuration.')

            log_out.write('\nSTDOUT:\n')
            log_out.write(str(results.stdout.decode()))
            log_out.write('\nSTDERR:\n')
            log_out.write(str(results.stderr.decode()))
            print(f'  Wrote log to {log_file}.')
        print(f'<< End: Processing config {cfg}.')


def docker_run(config):
    docker_image = 'qpme_experiment:latest'
    before_time = datetime.datetime.now()
    subprocess.run(['docker', 'run', '-v', f'{base_dir}/{config}:/tmp/experiment', docker_image])
    after_time = datetime.datetime.now()
    time_diff = after_time - before_time
    print(time_diff)
    return config, time_diff


def run_docker_experiments(config_files):
    docker_image = 'qpme_experiment:latest'
    experiments = {}
    configs = []

    for cfg in config_files:
        filename = os.path.basename(cfg)
        f_name, f_ext = os.path.splitext(filename)
        current_config_dir = f'{base_dir}/{f_name}'
        current_config_file = 'in.qpe'
        current_log_file = 'out.log'
        os.makedirs(current_config_dir, exist_ok=True)
        shutil.copy(cfg, f'{current_config_dir}/{current_config_file}')
        shutil.copy(f'{cfg}.log', f'{current_config_dir}/{current_log_file}')
        # before_time = datetime.datetime.now()
        # subprocess.run(['docker', 'run', '-v', f'{current_config_dir}:/tmp/experiment', docker_image])
        # after_time = datetime.datetime.now()
        # time_diff = after_time - before_time
        # print(time_diff)

        configs.append(f_name)

        experiments[f_name] = {
            'basedir': current_config_dir,
            'name': f_name,
            'config': current_config_file,
            'log': current_log_file,
            'stats': {} # + Operational Law (build duration), Execution time (simulation)
        }

    pool = mp.Pool()
    timings = pool.map(docker_run, configs)
    pool.close()

    for k, v in timings:
        experiments[k]['stats']['duration'] = v

    return experiments


if __name__ == "__main__":
    before_time = datetime.datetime.now()
    settings = create_settings()
    config_files = create_config_files(settings)
    pprint.pprint(config_files)
    experiments = run_docker_experiments(config_files)
    csv_out = '/tmp/plot_data.csv'
    entry_set = [('config', ['name']),
                 ('duration', ['stats', 'duration']),
                 ('workers', ['yaml', 'config', 'workers']),
                 ('jobs', ['yaml', 'config', 'jobs']),
                 ('workers_meanTkPop', ['yaml', 'ordp', 'Workers', 'color', 'token', 'meanTkPop']),
                 ('ordp_jobs_meanTkPop', ['yaml', 'ordp', 'Jobs', 'color', 'token', 'meanTkPop']),
                 ('doqp_stage_meanTkPop', ['yaml', 'doqp', 'Stage', 'color', 'token', 'meanTkPop']),
                 ('qoqp_stage_meanTkPop', ['yaml', 'qoqp', 'Stage', 'color', 'token', 'meanTkPop']),
                 ('arrival_rate', ['yaml', 'queue', 'build_arrival', 'totArrivThrPut']),
                 # ('value', ['yaml', 'doqp', 'Stage', 'color', 'token', 'deptThrPut'])]
                 # ('value', ['yaml', 'probe', 'RT', 'color', 'token', 'meanST']),
                 ('utilization', None),
                 ('build_duration', None),
                ]
    header_string = ';'.join([entry[0] for entry in entry_set])
    header = [entry[0] for entry in entry_set]

    data_rows = []

    for e in experiments:
        experiments[e]['yaml_file'] = 'out_parsed.yml'
        QPMEOutputParser(experiments[e]['basedir'], experiments[e]['log'], experiments[e]['yaml_file'])
        with open(f'''{experiments[e]['basedir']}/{experiments[e]['yaml_file']}''') as yaml_content:
            experiments[e]['yaml'] = yaml.safe_load(yaml_content)

        results = []
        for entry in entry_set:
            if entry[1]:
                entry_path = entry[1]
                entry_content = experiments[e]
                for element in entry_path:
                    entry_content = entry_content[element]
                results.append(str(entry_content))
        # ((#Workers - MeanTokPop) / #Jobs) / #ArrivalRate
        # ((float(results[2]) - float(results[4]))/float(results[3]))/float(results[5]))
        results.append(
            # 1-(WorkerTokens/#Worker)
            1-(float(results[4])/float(results[2])))

        results.append(
            # TokenPop(Jobs/Stage)/#Jobs/ArrivalRate
            (
                (
                    float(results[5]) + float(results[6]) + float(results[7])
                )
                / float(results[3]) / float(results[8])
            )
        )
        data_rows.append(results)

    # pprint.pprint(experiments)
    pd_df = pd.DataFrame(np.array(data_rows), columns=header)

    pprint.pprint(pd_df)
    # pd_df.plot(x='jobs', y='value', kind='scatter')
    pd_df.to_csv('/tmp/plot_data.csv', index=False)
    # plt.show()
    after_time = datetime.datetime.now()
    time_diff = after_time - before_time
    print(f'> Total time > {time_diff}')
