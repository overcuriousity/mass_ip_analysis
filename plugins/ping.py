import subprocess
import logging
import ipaddress
import datetime
from datetime import datetime, timezone

def execute_command(command):
    """
    Executes a system command and returns the output.
    """
    try:
        result = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
        return True, result.decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        return True, e.output.decode('utf-8').strip()
    # Even if the ping command fails, it's a valid result for our purpose.

def run(ip, command_flag=None):
    """
    Main function to be called by the plugin system.
    The 'command_flag' can be used to modify the command behavior.
    """
    try:
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_global:
            # Append command_flag if provided
            command = f"ping {command_flag} {ip}" if command_flag else f"ping -c 1 {ip}"
            logging.debug(f'Executing command: {command}')
            success, output = execute_command(command)
            ct = datetime.now(timezone.utc)
            ct = ct.strftime('%Y-%m-%d %H:%M:%S')
            # Determine the result based on the output
            if "rtt" in output:               
                result_message = f"{ip}: UP at {ct}"
            else:
                result_message = f"{ip}: DOWN at {ct}"
        else:
            success = True
            result_message = f"{ip} is in a private address range, skipped"

        return {'success': success, 'result': result_message}
    except ValueError:
        return {'success': False, 'result': f"{ip} is not a valid IP address"}

if __name__ == "__main__":
    # Test the plugin
    test_ip = "8.8.8.8"
    result = run(test_ip)
    print(result)
