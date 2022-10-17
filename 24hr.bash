#Use crontab to launch this script as root every 24 hours
#This script will:
    #Kill the old responseDaemon process
    #Launch main.py which should make a new post and fork a new responseDaemon.py to run for the next 24 hours

killall python3
python3 ~/main.py