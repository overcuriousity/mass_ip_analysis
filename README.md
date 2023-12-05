# Mass IP Analysis Application

This application is a PyQt5-based tool for analyzing IP addresses inside CSV files. It supports the modular addition of plugins, which can iterate over the IPs and perform any operations, output them to a CSV output file. 

## Features

- can process multiple files at once
- intuitive GUI
- completely modular
- fast multithreading
- status information during runs
- can pass flags to the commands (e.G. nmap -sS)
- displays your outbound ip for opsec

## Installation

! Windows unsupported, as it was developed and tested on a debian host. 

1. Clone the Repository:
   ````bash
   git clone https://github.com/overcuriousity/mass_ip_analysis.git
   cd mass_ip_analysis
   

3. Set up a Virtual Environment (Optional but Recommended):

   - For Linux/Mac:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

4. Install Required Packages:
   ```bash
   pip install -r requirements.txt
   ```

6. Run the Application:

   - For Linux/Mac:
     ```bash
     python3 mass_ip_analysis.py
     ```

## Usage

After starting the application, follow these steps:

- Use the 'Select File for Analysis' button to choose files for analysis.
- Select which plugins to use and which flags to pass
- Click on 'Start Analysis' to begin the analysis.
- After the analysis, results are saved to a CSV file

Educational purposes only, make sure you have the rights/permission to use the commands executed. No responsibilities taken by the author.

## Known Issues

- UI not working as intended
- Parser Modularity not yet implemented

## Contributing

Contributions to this project are welcome. Please feel free to fork the repository, make changes, and submit pull requests.

## License

This project is licensed under the GNU License.
