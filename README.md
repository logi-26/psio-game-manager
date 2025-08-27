# psio-assist
Python scripts with a basic GUI to prepare PlayStation 1 bin/cue games for use with a PSIO device.<br>
Works on Linux, Mac and Windows.<br>

![alt text](https://github.com/logi-26/psio-assist/blob/v0.2/image.png?raw=true)

**This application:**<br/>
Organises and standardises PlayStation 1 games into a format acceptable by the PSIO device. It performs the following tasks:<br/>

- Works in batch mode on all selected games.<br/>
- Merges multi-bin games into a single bin file.<br/>
- Generates cu2 files for all games that use CDDA audio.<br/>
- Adds game cover images for games that do not have them.<br/>
- Ensures that game names are not greater than 60 characters and do not contain periods or slashes.<br/>
- Generates the MULTIDISC.LST file for mult-disc games and organises them into a single directory.<br/>
- Does not modify the original bin/cue files.<br/>
- OPTIONAL: Rename all games using the game names from the PlayStation Redump project.<br/>

## Info
This application uses the following Python scripts, which have been custom modified for psio-assist:<br/>
**binmerge**<br/>
https://github.com/putnam/binmerge<br/>
**cue2cu2**<br/>
https://github.com/NRGDEAD/Cue2cu2<br/>

This application has Python PPF patching functions that where based on this C code:<br/>
**ppf**<br/>
https://github.com/meunierd/ppf

## Windows Users
There is a Windows exe file in the src/dist directory.<br/>
You will also need the "data" folder that contains the database files.<br/>

## Notes
For best performance, use the application with your games stored on a PC HDD/SSD and then transfer to an SD card.<br/>
SD card read/write speeds are a lot slower, if you have a lot of multi-bin games the process can take a lot longer.<br/><br/>
The application uses the games cue sheet to identify the games. If your game does not have a .cue file it will not be detected.

## Dependencies
This project requires Python 3 and the following Python packages:
- `ttkbootstrap`
- `pathlib2`

### Installation Steps for running the Python scripts
1. **Install Python 3**:
   - Download and install Python 3 from the official website: https://www.python.org/downloads/
   - Ensure Python 3 is added to your system PATH.

2. **Install pip**:
   - Pip is usually included with Python 3. To check if pip is installed, run:
     ```bash
     pip --version
     ```
   - If pip is not installed, you can install it by following the instructions here: https://pip.pypa.io/en/stable/installation/

3. **Set up a virtual environment**:
   - It is recommended to use a virtual environment to manage dependencies. To create and activate a virtual environment, follow these steps:
     - Create a virtual environment:
       ```bash
       python3 -m venv venv
       ```
     - Activate the virtual environment:
       - On Windows:
         ```bash
         venv\Scripts\activate
         ```
       - On macOS and Linux:
         ```bash
         source venv/bin/activate
         ```
       - On Linux (alternative method):
         ```bash
         . venv/bin/activate
         ```
   - For more information on virtual environments, refer to the official documentation: https://docs.python.org/3/library/venv.html

4. **Install the required Python packages**:
   - With the virtual environment activated, run:
     ```bash
     pip install ttkbootstrap pathlib2
     ```

## Usage
1. **Run the application**:
   - Ensure you have activated your virtual environment.
   - Navigate to the `src` directory where `psio_assist.py` is located.
   - Run the script using Python:
     ```bash
     python3 psio_assist.py
     ```

2. **Using the GUI**:
   - Click on the **Browse** button and select the directory that contains your bin/cue files.
   - Click on the **Scan** button to scan the games inside the selected directory.
   - OPTIONAL: Select to rename all games using the game names from the PlayStation Redump project.
   - Click on the **Start** button to process the games.
   - The progress bar will display the progress of the application.
