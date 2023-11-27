import subprocess
import logging
import ipaddress

def execute_command(command):
    """
    Executes a system command and returns the output.
    """
    try:
        result = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True) 
        if "DOWN" in result:
            return True, result.decode('utf-8').strip()  
        else:     
            return True, result.decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        # Output if the ping command fails because host is down, which is information we want to pass to the main program:
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

    logging.debug(f'Executing command: {command}')
    success, output = execute_command(command)

    # Determine the result based on the output
    if "rtt" in output and success == True:
        result_message = f"{ip}: UP"
    else:
        result_message = f"{ip}: DOWN"
        
    return {'success': success, 'result': result_message}

if __name__ == "__main__":
    # Test the plugin
    test_ip = "8.8.8.8"
    result = run(test_ip)
    print(result)
