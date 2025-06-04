import subprocess
import os
import argparse

def parse_ty_output(output):
    errors = []
    for line in output.splitlines():
        if line.startswith('error'):
            parts = line.split(':')
            file_path = parts[0].split('/')[-1]
            line_number = int(parts[1])
            error_message = ':'.join(parts[2:])
            errors.append((file_path, line_number, error_message))
    return errors

def parse_pyrefly_output(output):
    errors = []
    for line in output.splitlines():
        if line.startswith('ERROR'):
            parts = line.split(':')
            file_path = parts[0].split('/')[-1]
            line_number = int(parts[1].split('-')[0])
            error_message = ':'.join(parts[2:])
            errors.append((file_path, line_number, error_message))
    return errors

def parse_pyright_output(output):
    errors = []
    for line in output.splitlines():
        if line.startswith('/Users/'):
            # This line contains the file path
            # This line contains the line number and error type
            parts = line.split('-')
            file = parts[0]
            print(parts)
            file_path = file.split(':')[0]
            line_number = int(file_path[1].strip())
            error_message = parts[1].strip()
            errors.append((file_path, line_number, error_message))

        print(errors)
    return errors

def parse_pyper_output(output):
    errors = []
    for line in output.splitlines():
        if line.endswith('Unused ignore [0]:'):
            parts = line.split(':')
            file_path = parts[0].split('/')[-1]
            line_number = int(parts[1])
            error_message = ':'.join(parts[2:]) + 'Unused ignore [0]:'
            errors.append((file_path, line_number, error_message))
    return errors

def compare_outputs(outputs):
    errors = {}
    for checker, output in outputs.items():
        parsed_output = []
        if checker == 'ty':
            parsed_output = parse_ty_output(output)
        elif checker == 'pyrefly':
            parsed_output = parse_pyrefly_output(output)
        elif checker == 'pyright':
            parsed_output = parse_pyright_output(output)
        elif checker == 'pyre':
            parsed_output = parse_pyper_output(output)
        
        for error in parsed_output:
            key = (error[0], error[1])
            if key not in errors:
                errors[key] = {'checkers': set([checker]), 'error_message': error[2]}
            else:
                errors[key]['checkers'].add(checker)

    common_errors = {key: value for key, value in errors.items() if len(value['checkers']) > 1}

    print("Common errors:")
    for key, value in common_errors.items():
        print(f"File: {key[0]}, Line: {key[1]}")
        print(f"Error message: {value['error_message']}")
        print(f"Found by: {', '.join(sorted(value['checkers']))}")
        print()

    unique_errors = {key: value for key, value in errors.items() if len(value['checkers']) == 1}

    print("Unique errors:")
    for checker in outputs.keys():
        print(f"{checker}:")
        for key, value in unique_errors.items():
            if checker in value['checkers']:
                print(f"  File: {key[0]}, Line: {key[1]}")
                print(f"  Error message: {value['error_message']}")
        print()

def main():
    parser = argparse.ArgumentParser(description='Compare type checkers')
    parser.add_argument('--file', help='File to check')
    args = parser.parse_args()
    file_to_check = args.file
    if file_to_check is None:
        file_to_check = ""
    outputs = {}
    # Run ty
    ty_command = f"ty check {file_to_check} --output-format concise"
    ty_result = subprocess.run(ty_command, shell=True, capture_output=True)
    outputs['ty'] = ty_result.stdout.decode('utf-8')
    # Run pyrefly
    pyrefly_command = f"pyrefly check {file_to_check}"
    pyrefly_result = subprocess.run(pyrefly_command, shell=True, capture_output=True)
    outputs['pyrefly'] = pyrefly_result.stdout.decode('utf-8')
    # Run pyright
    pyright_command = f"pyright {file_to_check}"
    pyright_result = subprocess.run(pyright_command, shell=True, capture_output=True)
    outputs['pyright'] = pyright_result.stdout.decode('utf-8')
    # Run pyre
    pyre_command = f"pyre {file_to_check}"
    pyre_result = subprocess.run(pyre_command, shell=True, capture_output=True)
    outputs['pyre'] = pyre_result.stdout.decode('utf-8')
    compare_outputs(outputs)

if __name__ == "__main__":
    main()