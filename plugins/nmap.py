import subprocess
import logging

def execute_command(command):
    """
    Executes a system command and returns the output.
    """
    try:
        result = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
        return True, result.decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        return True, e.output.decode('utf-8').strip()  # Return True even in case of a standard error

def run(ip, command_flag=None):
    """
    Main function to be called by the plugin system.
    The 'command_flag' can be used to modify the command behavior.
    """

    # Append command_flag if provided
    command = f"nmap {command_flag} {ip}" if command_flag else f"nmap {ip}"
    logging.debug(f'Executing command: {command}')
    
    success, output = execute_command(command)
    logging.debug(f"Command output for IP {ip}: {output}")

    # Following the standardized format
    return {'success': success, 'result': output}

if __name__ == "__main__":
    # Test the plugin
    test_ip = "8.8.8.8"
    result = run(test_ip)
    print(result)
