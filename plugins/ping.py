import subprocess
import logging
import ipaddress

def execute_command(command):
    """
    Executes a system command and returns the output.
    """
    try:
        result = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
        return True, result.decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        return False, e.output.decode('utf-8').strip()

def run(ip, command_flag=None):
    """
    Main function to be called by the plugin system.
    The 'command_flag' can be used to modify the command behavior.
    """


    # Append command_flag if provided
    if command_flag:
        command = f"ping {command_flag} {ip}"
    else:
        command = f"ping -c 1 {ip}"

    logging.debug(f'{command}')
    success, output = execute_command(command)
    
    # Debug: Print the command output
    print(f"Command output for IP {ip}: {output}")

    if success and "rtt" in output:
        return f"{ip}: UP"
    else:
        return f"{ip}: DOWN"


if __name__ == "__main__":
    # Test the plugin
    test_ip = "8.8.8.8"
    print(run(test_ip))
