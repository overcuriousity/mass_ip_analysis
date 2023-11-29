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
        output = result.decode('utf-8').strip()

        # Remove "GeoIP Country Edition: " from the output
        if "GeoIP Country Edition: " in output:
            output = output.replace("GeoIP Country Edition: ", "")

        return True, output
    except subprocess.CalledProcessError as e:
        output = e.output.decode('utf-8').strip()

        # Remove "GeoIP Country Edition: " from the error output as well
        if "GeoIP Country Edition: " in output:
            output = output.replace("GeoIP Country Edition: ", "")

        return True, output  # Even if the command fails, it's a valid result for our purpose.

def run(ip, command_flag=None):
    """
    Main function to be called by the plugin system.
    The 'command_flag' can be used to modify the command behavior.
    """
    try:
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_global:
            # Append command_flag if provided
            command = f"geoiplookup {command_flag} {ip}" if command_flag else f"geoiplookup {ip}"
            logging.debug(f'Executing command: {command}')
            success, result_message = execute_command(command)
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

