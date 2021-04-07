# psio-assist
Python scripts with a basic GUI to prepare PlayStation 1 bin/cue games for use with a PSIO device.<br>
Works on Linux, Mac and Windows.<br>

![alt text](https://github.com/logi-26/psio-assist/blob/main/image.png?raw=true)

**This application:**<br/>
Merges multi-bin games into a single bin file.<br/>
Generates cu2 files for all games.<br/>
Works in batch mode on all bin/cue files in the selected directory and any sub-directories.<br/>
Adds the game cover image.<br/>
Generates the MULTIDISC.LST file for mult-disc games.<br/>
Does not modify the original bin/cue files.<br/>

## Info
This uses the following scripts:<br/>
**binmerge**<br/>
https://github.com/putnam/binmerge <br/>
**cue2cu2**<br/>
https://github.com/NRGDEAD/Cue2cu2

## Usage
Requires Python 3.<br/>
Download or clone this repo.<br/>
Run psio_assist.py that is in the src directory.<br/>
**For example**:<br/>
python psio_assist.py<br/><br/>

Click on the Browse button and select the directory that contains your bin/cue files.<br>
Click on the Start button and the application will start to process the games.<br>
The progress bar will show the progress of the application.<br>
Once the application has finished you can find your PSIO ready files in the 'output' directory.<br>
Just copy all of the directories from the 'output' directory to the root of your SD card.<br>
If any errors occur you can check the log file in the 'error_log' directory for more information.<br>
