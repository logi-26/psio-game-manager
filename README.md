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
- Patches LibCrypt games.<br/>
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


## LibCrypt Patches
- SLES_031.89 - 102 Dalmatians
- SLES_031.90 - 102 Dalmatians
- SLES_031.91 - 102 Dalmatians
- SLES_012.26 - Actua Ice Hockey 2 (Europe)
- SLES_025.63 - Anstoss - Premier Manager (Germany)
- SCES_015.64 - Ape Escape (Europe)
- SCES_020.28 - Ape Escape (France)
- SCES_020.29 - Ape Escape (Germany)
- SCES_020.30 - Ape Escape (Italy)
- SCES_020.31 - Ape Escape (Spain)
- SLES_033.24 - Asterix: Mega Madness (Europe)
- SCES_023.66 - Barbie: Aventure Equestre (France)
- SCES_023.65 - Barbie: Race & Ride (Europe)
- SCES_023.67 - Barbie: Race & Ride (Germany)
- SCES_023.68 - Barbie: Race & Ride (Italy)
- SCES_023.69 - Barbie: Race & Ride (Spain)
- SCES_024.88 - Barbie: Sports Extreme (France)
- SCES_024.89 - Barbie: Super Sport (Germany)
- SCES_024.87 - Barbie: Super Sports (Europe)
- SCES_024.90 - Barbie: Super Sports (Italy)
- SCES_024.91 - Barbie: Super Sports (Spain)
- SLES_029.77 - BDFL Manager 2001 (Germany)
- SLES_036.05 - BDFL Manager 2002 (Germany)
- SLES_030.62 - Bundesliga 2001 – The Football Manager (Europe)
- SLES_022.93 - Canal+ Premier Manager
- SLES_027.66 - Cochons de Guerre, Les (France)
- SCES_028.34 - Crash Bash (Europe)
- SCES_021.05 - CTR: Crash Team Racing (Europe)
- SLES_022.07 - Dino Crisis (Europe)
- SLES_022.08 - Dino Crisis (France)
- SLES_022.09 - Dino Crisis (Germany)
- SLES_022.10 - Dino Crisis (Italy)
- SLES_022.11 - Dino Crisis (Spain)
- SCES_015.16 - Disney Tarzan (France)
- SCES_015.18 - Disney Tarzan (Italy)
- SCES_015.19 - Disney Tarzan (Spain)
- SCES_014.31 - Disney's Tarzan (Europe)
- SCES_021.85 - Disney's Tarzan (Netherlands)
- SCES_021.84 - Disneyn Tarzan (Finland)
- SCES_021.81 - Disneys Tarzan (Denmark)
- SCES_015.17 - Disneys Tarzan (Germany)
- SCES_021.82 - Disneys Tarzan (Sweden)
- SLES_025.38 - EA Sports Superbike 2000 (Europe)
- SLES_017.15 - Eagle One: Harrier Attack (Europe)
- SCES_017.04 - Esto Es Futbol (Spain)
- SLES_027.22 - F1 2000 (Europe)
- SLES_027.23 - F1 2000 (Europe)
- SLES_027.24 - F1 2000 (Italy)
- SLES_029.67 - Final Fantasy 9 (Germany) (Disc 1)
- SLES_129.67 - Final Fantasy 9 (Germany) (Disc 2)
- SLES_229.67 - Final Fantasy 9 (Germany) (Disc 3)
- SLES_329.67 - Final Fantasy 9 (Germany) (Disc 4)
- SLES_029.65 - Final Fantasy IX (Europe) (Disc 1)
- SLES_129.65 - Final Fantasy IX (Europe) (Disc 2)
- SLES_229.65 - Final Fantasy IX (Europe) (Disc 3)
- SLES_329.65 - Final Fantasy IX (Europe) (Disc 4)
- SLES_029.66 - Final Fantasy IX (France) (Disc 1)
- SLES_129.66 - Final Fantasy IX (France) (Disc 2)
- SLES_229.66 - Final Fantasy IX (France) (Disc 3)
- SLES_329.66 - Final Fantasy IX (France) (Disc 4)
- SLES_029.68 - Final Fantasy IX (Italy) (Disc 1)
- SLES_129.68 - Final Fantasy IX (Italy) (Disc 2)
- SLES_229.68 - Final Fantasy IX (Italy) (Disc 3)
- SLES_329.68 - Final Fantasy IX (Italy) (Disc 4)
- SLES_029.69 - Final Fantasy IX (Spain) (Disc 1)
- SLES_129.69 - Final Fantasy IX (Spain) (Disc 2)
- SLES_229.69 - Final Fantasy IX (Spain) (Disc 3)
- SLES_329.69 - Final Fantasy IX (Spain) (Disc 4)
- SLES_020.81 - Final Fantasy VIII (Europe) (Disc 1)
- SLES_120.81 - Final Fantasy VIII (Europe) (Disc 2)
- SLES_220.81 - Final Fantasy VIII (Europe) (Disc 3)
- SLES_320.81 - Final Fantasy VIII (Europe) (Disc 4)
- SLES_X20.82 - Final Fantasy VIII (Germany)
- SLES_X20.83 - Final Fantasy VIII (Italy)
- SLES_020.84 - Final Fantasy VIII (Spain) (Disc 1)
- SLES_120.84 - Final Fantasy VIII (Spain) (Disc 2)
- SLES_220.84 - Final Fantasy VIII (Spain) (Disc 3)
- SLES_320.84 - Final Fantasy VIII (Spain) (Disc 4)
- SLES_020.80 - Final Fantasy VIII Platinum edition (Europe) (Disc 1)
- SLES_120.80 - Final Fantasy VIII Platinum edition (Europe) (Disc 2)
- SLES_220.80 - Final Fantasy VIII Platinum edition (Europe) (Disc 3)
- SLES_320.80 - Final Fantasy VIII Platinum edition (Europe) (Disc 4)
- SLES_029.78 - Football Manager Campionato 2001
- SLES_036.06 - Football Manager Campionato 2002
- SCES_019.79 - Formula One 99
- SCES_022.22 - Formula One 99
- SLES_027.67 - Frontschweine (Germany)
- SCES_017.02 - Fussball Live (Germany)
- SLES_023.28 - Galerians (Europe) (Disc 1)
- SLES_123.28 - Galerians (Europe) (Disc 2)
- SLES_223.28 - Galerians (Europe) (Disc 3)
- SLES_023.29 - Galerians (France) (Disc 1)
- SLES_123.29 - Galerians (France) (Disc 2)
- SLES_223.29 - Galerians (France) (Disc 3)
- SLES_023.30 - Galerians (Germany) (Disc 1)
- SLES_123.30 - Galerians (Germany) (Disc 2)
- SLES_223.30 - Galerians (Germany) (Disc 3)
- SLES_012.41 - Gekido: Urban Fighters (Europe)
- SLES_010.41 - Hogs of War (Europe)
- SLES_027.69 - Hogs of War: Nati per Soffritto
- SCES_014.44 - Jackie Chan Stuntmaster (Europe)
- SLES_029.76 - La Selection des Champions
- SLES_036.04 - La Selection des Champions 2002
- SLES_013.62 - Le Mans 24 Hours (Europe)
- SCES_017.01 - Le Monde des Bleus
- SLES_029.75 - LMA Manager 2001 (Europe)
- SLES_036.03 - LMA Manager 2002 (Europe)
- SLES_035.30 - Lucky Luke: Western Fever (Europe)
- SLES_024.02 - Manager de Liga (Spain)
- SLES_029.79 - Manager de Liga 2001 (Spain)
- SLES_036.07 - Manager de Liga 2002 (Spain)
- SLES_027.68 - Marranos en Guerra (Spain)
- SCES_003.11 - MediEvil (Europe)
- SCES_014.92 - MediEvil (France)
- SCES_014.93 - MediEvil (Germany)
- SCES_014.94 - MediEvil (Italy)
- SCES_014.95 - MediEvil (Spain)
- SCES_025.44 - MediEvil 2 (Europe)
- SCES_025.45 - MediEvil 2 (Europe)
- SCES_025.46 - MediEvil 2 (Russia)
- SLES_035.19 - MiB: Crashdown (Europe)
- SLES_035.20 - MiB: Crashdown (France)
- SLES_035.21 - MiB: Crashdown (Germany)
- SLES_035.22 - MiB: Crashdown (Italy)
- SLES_035.23 - MiB: Crashdown (Spain)
- SLES_015.45 - Michelin Rally Masters
- SLES_023.95 - Michelin Rally Masters
- SLES_028.39 - Mike Tyson Boxing (Europe)
- SLES_019.06 - Mission: Impossible (Europe)
- SLES_028.30 - MoHo (Europe)
- SCES_016.95 - Mulan (Europe)
- SCES_020.04 - Mulan (France)
- SCES_020.05 - Mulan (Germany)
- SCES_020.06 - Mulan (Italy)
- SCES_022.64 - Mulan (Netherlands)
- SCES_020.07 - Mulan (Spain)
- SLES_020.86 - N-Gen Racing (Europe)
- SLES_026.89 - NFS: Porsche 2000
- SLES_027.00 - NFS: Porsche 2000
- SLES_X18.79 - OverBlood 2 (Europe)
- SLES_X18.80 - OverBlood 2 (Italy)
- SLES_X25.58 - Parasite Eve II (Europe)
- SLES_X25.59 - Parasite Eve II (France)
- SLES_X25.60 - Parasite Eve II (Germany)
- SLES_X25.62 - Parasite Eve II (Italy)
- SLES_X25.61 - Parasite Eve II (Spain)
- SLES_020.61 - PGA European Tour Golf
- SLES_023.96 - PGA European Tour Golf
- SLES_022.92 - Premier Manager 2000
- SLES_000.17 - Prince Naseem Boxing (Europe)
- SLES_019.43 - Radikal Biker (Pal/Multi)
- SLES_028.24 - RC Revenge (Europe)
- SLES_025.29 - Resident Evil 3 (Europe)
- SLES_025.30 - Resident Evil 3 (France)
- SLES_025.31 - Resident Evil 3 (Germany)
- SLES_026.98 - Resident Evil 3 (Ireland)
- SLES_025.33 - Resident Evil 3 (Italy)
- SLES_025.32 - Resident Evil 3 (Spain)
- SLES_009.95 - Ronaldo V-Football
- SLES_026.81 - Ronaldo V-Football
- SLES_021.12 - SaGa Frontier 2 (Europe)
- SLES_021.13 - SaGa Frontier 2 (France)
- SLES_021.18 - SaGa Frontier 2 (Germany)
- SLES_027.63 - SnoCross Championship Racing (Eur)
- SLES_013.01 - Soul Reaver (Europe)
- SLES_020.24 - Soul Reaver (France)
- SLES_020.25 - Soul Reaver (Germany)
- SLES_020.27 - Soul Reaver (Italy)
- SLES_020.26 - Soul Reaver (Spain)
- SCES_022.90 - Space Debris (Europe)
- SCES_024.30 - Space Debris (France)
- SCES_024.31 - Space Debris (Germany)
- SCES_024.32 - Space Debris (Italy)
- SCES_024.33 - Space Debris (Spain)
- SCES_017.63 - Speed Freaks (Europe)
- SCES_021.04 - Spyro 2: Gateway to Glimmer
- SLES_028.58 - Sydney 2000
- SLES_028.59 - Sydney 2000
- SLES_028.60 - Sydney 2000
- SLES_028.61 - Sydney 2000
- SLES_028.62 - Sydney 2000
- SLES_028.57 - Sydney 2000 (Europe)
- SLES_032.41 - TechnoMage (Europe)
- SLES_032.42 - TechnoMage (France)
- SLES_028.31 - TechnoMage (Germany)
- SLES_032.43 - TechnoMage (Italy)
- SLES_032.45 - TechnoMage (Netherlands)
- SLES_032.44 - Technomage (Spain)
- SLES_030.61 - The F.A. Premier League Football Manager 2001 (Europe)
- SLES_034.89 - The Italian Job
- SLES_036.26 - The Italian Job
- SLES_036.48 - The Italian Job
- SLES_026.88 - Theme Park World (Europe)
- SCES_017.00 - This Is Football (Europe)
- SCES_018.82 - This Is Football (Europe)
- SCES_017.03 - This Is Football (Italy)
- SCES_022.69 - This Is Soccer (Australia)
- SLES_025.72 - TOCA World Touring Cars (English, German, French)
- SLES_025.73 - TOCA World Touring Cars (Italian, Spanish)
- SLES_027.04 - UEFA Euro 2000 (Europe)
- SLES_027.05 - UEFA Euro 2000 (France)
- SLES_027.06 - UEFA Euro 2000 (Germany)
- SLES_027.07 - UEFA Euro 2000 (Italy)
- SLES_027.08 - UEFA Euro 2000 (Spain)
- SLES_017.33 - UEFA Striker
- SLES_020.71 - Urban Chaos (Europe)
- SLES_023.54 - Urban Chaos (France)
- SLES_023.55 - Urban Chaos (Germany)
- SLES_019.07 - V-Rally: Championship Edition 2
- SLES_027.54 - Vagrant Story (Europe)
- SLES_027.55 - Vagrant Story (France)
- SLES_027.56 - Vagrant Story (Germany)
- SLES_027.33 - Walt Disney World Quest
- SCES_019.09 - Wip3out (Europe)

## Windows Users
There is a Windows exe file:<br/>
https://github.com/logi-26/psio-assist/releases/tag/V0.3<br/>

## Notes
  - For best performance, use the application with your games stored on a PC HDD/SSD and then transfer to an SD card. SD card read/write speeds are a lot slower, if you have a lot of multi-bin games the process can take a lot longer.
  - The application uses the games cue sheet to identify the games. If your game does not have a .cue file it will not be detected.
  - If a game is a single disc game the disc number will be displayed with zero to indicate that it is not part of a collection.
  - If a game is not part of a collection the LST will be displayed with an asterisk.
  - If a game is part of a collection and an LST file is not present the LST will be displayed with "No".
  - If a game is part of a collection and an LST file is present the LST will be displayed with "Yes".

  - If a game does not require a CU2 file the CU2 will be displayed with an asterisk.
  - If a game does require a CU2 file and one is not present the CU2 will be displayed with "No".
  - If a game does require a CU2 file and one is present the CU2 will be displayed with "Yes".
  - If a game does not use LibCrypt the LibCrypt will be displayed with an asterisk.
  - If a game does use LibCrypt but their is no patch available the LibCrypt will be displayed with "No".
  - If a game does use LibCrypt and their is a patch available the LibCrypt will be displayed with "Yes".

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

3. **Set up a virtual environment or use a Docker container**:
   
    **To create and run the app in a Python virtual environment, follow these steps**:
     - Create a virtual environment:
       ```bash
       python -m venv psio_assist_env
       ```
     - Activate the virtual environment:
       - On Windows:
         ```bash
         psio_assist_env\Scripts\activate
         ```
       - On macOS and Linux:
         ```bash
         source psio_assist_env/bin/activate
         ```
       - On Linux (alternative method):
         ```bash
         . psio_assist_env/bin/activate
         ```
      - Install dependencies in the virtual environment:
        ```bash
        pip install -r requirements.txt
        ```
      - Navigate to the `src` directory where `psio_assist.py` is located.
      - Run the script using Python:
        ```bash
        python psio_assist.py
        ```

    **To create and run the app in a Docker container, follow these steps**:
      - Download and install Docker Desktop from the official website: https://docs.docker.com/desktop/
      - Open a terminal in your project directory and run:
        ```bash
        docker build -t psio-assist-app .
        ```
        This builds an image named psio-assist-app
      - Run the container with:
        ```bash
        docker run psio-assist-app
        ```

## Usage
1. **Using the GUI**:
   - Click on the **Browse** button and select the directory that contains your bin/cue files.
   - OPTIONAL: Select to rename all games using the game names from the PlayStation Redump project.
   - Click on the **Process** button to process the games.
   - The progress bar will display the progress of the application.

2. **OPTIONAL: Run the application with debug print logs**:
   - Run the script using the -d commandline argument:
     ```bash
     python psio_assist.py -d
     ```

   - Run the exe using the -d commandline argument:
     ```bash
     psio_assist.exe -d
     ```