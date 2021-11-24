#!/usr/bin/env python3

import os
import re
import sys
import yaml


class QPMEOutputParser:
    def __init__(self, base_dir, log_file, output_file):

        log_file_path = f'{base_dir}/{log_file}'
        output_file_path = f'{base_dir}/{output_file}'

        result = {
            'Queue of Queueing Place': {},
            'Depository of Queueing Place': {},
            'Queue': {},
            'Ordinary Place': {},
            'Probe': {},
        }

        if log_file_path and output_file_path:
            pass
            # print(f'Processing file: {log_file_path}. Writing results to: {output_file_path}.')
        else:
            print('No file to process provided.')
            exit()

        with open(log_file_path, 'r') as in_file:
            config_line = yaml.safe_load(in_file.readline().strip())
            config_content = in_file.read() + 'EOF'

        matches = re.findall(r'REPORT for (.*?)(?=(REPORT|EOF))', config_content, re.DOTALL)

        for match in matches:
            # print(match[0])

            # Remove empty lines
            filtered = os.linesep.join([s for s in match[0].splitlines() if s.strip()])

            # Remove dashes
            filtered = re.sub(r'(-){2,}', '', filtered)

            # Retrieve header elements
            header = filtered.partition('\n')[0].replace('-', '').split(' : ')

            # Add information to results
            result[header[0]][header[1]] = filtered.partition('\n')[2]

        output = {'config': config_line}

        for key in result:
            if key == 'Queue':
                output['queue'] = QPMEOutputParser.queue_handler(result[key])
            elif key == 'Probe':
                output['probe'] = QPMEOutputParser.probe_handler(result[key])
            elif key == 'Queue of Queueing Place':
                output['qoqp'] = QPMEOutputParser.queue_of_queueing_place_handler(result[key])
            elif key == 'Ordinary Place':
                output['ordp'] = QPMEOutputParser.ordinary_place_handler(result[key])
            elif key == 'Depository of Queueing Place':
                output['doqp'] = QPMEOutputParser.depository_of_queueing_place_handler(result[key])

        with open(output_file_path, 'w') as out_yaml:
            out_yaml.write(yaml.dump(output))

    # queue
    @staticmethod
    def queue_handler(items):
        result = {}
        for key in items:
            key_result = {}
            kv_pairs = items[key].replace('\n', ' ').split(' ')
            for entry in kv_pairs:
                split_entry = entry.split('=')
                key_result[split_entry[0]] = float(split_entry[1])
            key_result['type'] = 'queue'
            key_result['name'] = key
            result[key] = key_result

        return result

    # probe
    @staticmethod
    def probe_handler(items):
        result = {}
        for key in items:

            # Create 'color' section
            key_result = {'color': {}, 'steady_state_statistics': {}}

            # Sanitize string and split it
            kv_pairs = items[key] \
                .replace(' Color = ', 'Color=') \
                .replace('\n', ' ') \
                .replace('Steady State Statistics:', 'SteadyStateStatistics') \
                .replace('95% c.i. = ', '95%c.i.=') \
                .replace(' +/- ', '+/-') \
                .split(' ')

            # Default status to not colored and no current_color
            color = None
            ignore_spaces = 0
            steady_state_statistics = False
            for entry in kv_pairs:
                split_entry = entry.split('=')
                if entry.startswith('Color='):
                    color = split_entry[1]
                    key_result['color'][color] = {}
                    ignore_spaces = 2
                elif color and not entry:
                    if ignore_spaces > 0:
                        ignore_spaces -= 1
                    else:
                        color = None
                elif not entry:
                    continue
                elif entry == 'SteadyStateStatistics':
                    steady_state_statistics = True
                elif steady_state_statistics:
                    # print(split_entry)
                    key_result['steady_state_statistics'][split_entry[0]] = split_entry[1]
                elif not color:
                    key_result[split_entry[0]] = float(split_entry[1])
                elif color:
                    key_result['color'][color][split_entry[0]] = float(split_entry[1])
            key_result['type'] = 'probe'
            key_result['name'] = key
            result[key] = key_result

        return result

    # queue of queueing place
    @staticmethod
    def queue_of_queueing_place_handler(items):
        result = {}
        for key in items:

            # Create 'color' section
            key_result = {'color': {}, 'steady_state_statistics': {}}

            # Sanitize string and split it
            kv_pairs = QPMEOutputParser.sanitization_chain(items[key])

            # Default status to not colored and no current_color
            color = None
            one_after_color = False
            steady_state_statistics = False
            for entry in kv_pairs:
                split_entry = entry.split('=')
                if entry.startswith('Color='):
                    color = split_entry[1]
                    key_result['color'][color] = {}
                    one_after_color = True
                elif color and not entry:
                    if one_after_color:
                        one_after_color = False
                    else:
                        color = None
                elif not entry:
                    continue
                elif entry == 'SteadyStateStatistics':
                    steady_state_statistics = True
                elif steady_state_statistics:
                    key_result['steady_state_statistics'][split_entry[0]] = split_entry[1]
                elif not color:
                    key_result[split_entry[0]] = float(split_entry[1])
                elif color:
                    key_result['color'][color][split_entry[0]] = float(split_entry[1])
            key_result['type'] = 'queue_of_queueing_place'
            key_result['name'] = key
            result[key] = key_result

        return result

    # ordinary place
    @staticmethod
    def ordinary_place_handler(items):
        result = {}
        for key in items:

            # Create 'color' section
            key_result = {'color': {}}

            # Sanitize string and split it
            kv_pairs = items[key].replace(' Color = ', 'Color=').replace('\n', ' ').split(' ')

            # Default status to not colored and no current_color
            color = None
            for entry in kv_pairs:
                if not entry:
                    continue

                split_entry = entry.split('=')
                if entry.startswith('Color='):
                    color = split_entry[1]
                    key_result['color'][color] = {}
                elif not color:
                    key_result[split_entry[0]] = float(split_entry[1])
                else:
                    key_result['color'][color][split_entry[0]] = float(split_entry[1])
            key_result['type'] = 'ordinary_place'
            key_result['name'] = key
            result[key] = key_result

        return result

    # depository of queueing place
    @staticmethod
    def depository_of_queueing_place_handler(items):
        result = {}
        for key in items:

            # Create 'color' section
            key_result = {'color': {}, 'steady_state_statistics': {}}

            # Sanitize string and split it
            kv_pairs = QPMEOutputParser.sanitization_chain(items[key])

            # Default status to not colored and no current_color
            color = None
            one_after_color = False
            steady_state_statistics = False
            for entry in kv_pairs:
                split_entry = entry.split('=')
                if entry.startswith('Color='):
                    color = split_entry[1]
                    key_result['color'][color] = {}
                    one_after_color = True
                elif color and entry:
                    key_result['color'][color][split_entry[0]] = float(split_entry[1])
                elif color and not entry:
                    if not one_after_color:
                        color = None
                    else:
                        one_after_color = False
                elif not entry:
                    continue
                elif entry == 'SteadyStateStatistics':
                    steady_state_statistics = True
                elif steady_state_statistics:
                    key_result['steady_state_statistics'][split_entry[0]] = split_entry[1]
                elif not color:
                    key_result[split_entry[0]] = float(split_entry[1])
            key_result['type'] = 'depository_of_queueing_place'
            key_result['name'] = key
            result[key] = key_result

        return result

    @staticmethod
    def sanitization_chain(input_string: str) -> []:
        return input_string \
            .replace(' Color = ', 'Color=') \
            .replace('\n', ' ') \
            .replace('Steady State Statistics:', 'SteadyStateStatistics') \
            .replace('95% c.i. = ', '95%c.i.=') \
            .replace(' +/- ', '+/-') \
            .split(' ')


class QPMEParsingResult:
    def __init__(self):
        pass

    def get_full_dict(self):
        pass


if __name__ == "__main__":
    if len(sys.argv) > 2:
        input_param = sys.argv[1]
        output_param = sys.argv[2]
        if os.path.isfile(input_param) and os.path.isfile(output_param):
            QPMEOutputParser(input_param, output_param)
