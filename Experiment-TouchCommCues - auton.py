from psychopy import visual, core, event, data, gui, parallel
import numpy as np
import random, os, pygame, copy
from touchcomm import *


# -- GET INPUT FROM THE EXPERIMENTER --

exptInfo = {'00. Experiment name':'touch-comm-auton',
            '01. Participant Code':'test',
            '02. Number of presentations per touch':5,
            '03. Inter-stimulus interval (sec)':50,
            '04. Require response on (n) bonus trials per touch':1,
            '05. Participant screen':0,#1,
            '06. Participant screen resolution':'800,600', #'1920, 1200',
            '07. Experimenter screen':0,
            '08. Experimenter screen resolution':'400,300', #'1280,720',
            '09. Play audio cue for video sync':True,
            '10. Send signal for biopac sync':'serial', #('none','serial','parallel'),
            '11. Port address':'COM5', #'0x3FF8',
            '12. Folder for saving data':'data'}


dlg = gui.DlgFromDict(exptInfo, title='Experiment details')
if dlg.OK:
    pass ## continue
else:
    core.quit() ## the user hit cancel so exit

exptInfo['14. Date and time']= data.getDateStr(format='%Y-%m-%d_%H-%M-%S') ##add the current time


# text displayed to experimenter and participant
displayText = {'startMessage': 'Press Space to start.',
                'waitMessage': 'Please wait.',
                'continueMessage': 'Press space for the audio cue.',
                'touchMessage': 'Follow the audio cue.',
                'fixationMessage': '+',
                'finishedMessage': 'The session has finished.',
                'finishedSyncMessage': 'The session has finished.\n Unplug the headphones, then press space to play the video sync sound.'}
if exptInfo['09. Play audio cue for video sync']:
    displayText['startMessage'] = 'Make sure speakers are plugged in, not headphones. Then press space to start. Plug in headphones after the video sync sound has played.'

# ----


# -- SETUP STIMULUS RANDOMISATION AND CONTROL --

stimLabels = ['attention','gratitude','love','sadness','happiness','calming']
receiverCueText = dict((line.strip().split('\t') for line in open('receiver-cues.txt')))
toucherCueText = dict((line.strip().split('\t') for line in open('toucher-cues.txt')))
soundDurations = dict((line.strip().split('\t') for line in open('./sounds/durations.txt')))

stimList = []
for stim in stimLabels: 
    stimList.append({'stim':stim,
                    'toucherCueText':toucherCueText[stim],
                    'receiverCueText':receiverCueText[stim],
                    'cueSound':'./sounds/{} - short.wav' .format(stim),
                    'cueSoundDuration':float(soundDurations[stim]),
                    'SignalNo':stimLabels.index(stim)+1})
trials = data.TrialHandler(stimList, exptInfo['02. Number of presentations per touch'])

bonusStimList = copy.deepcopy(stimList)
bonusTrials = data.TrialHandler(bonusStimList, exptInfo['04. Require response on (n) bonus trials per touch'])
# ----

# -- MAKE FOLDER/FILES TO SAVE DATA --

saveFiles = DataFileCollection(foldername = exptInfo['12. Folder for saving data'],
                filename = exptInfo['00. Experiment name'] + '_' + exptInfo['14. Date and time'] +'_P' + exptInfo['01. Participant Code'],
                headers = ['trial','cued','response'],
                dlgInput = exptInfo)

# ----

# -- SETUP VISUAL INTERFACE --

toucher = DisplayInterface(False,
                        exptInfo['07. Experimenter screen'],
                        [int(i) for i in exptInfo['08. Experimenter screen resolution'].split(',')], ## convert text input to numbers
                        displayText['startMessage'])

receiver = VASInterface(fullscr = True, 
                        screen = exptInfo['05. Participant screen'], 
                        size = [int(i) for i in exptInfo['06. Participant screen resolution'].split(',')],
                        message = displayText['waitMessage'],
                        question = 'How pleasant was the last stimulus on your skin?',
                        minLabel = 'unpleasant',
                        maxLabel = 'pleasant')

# -----

# -- SETUP AUDIO --

pygame.mixer.pre_init() 
pygame.mixer.init()
goStopSound = pygame.mixer.Sound('./sounds/go-stop.wav')

# ----


# -- SETUP DATA SYNC --
if exptInfo['09. Play audio cue for video sync']:
    audioSync = './sounds/sync.wav'
else: audioSync = None

sync = DataSync(audioSync,
                portType = exptInfo['10. Send signal for biopac sync'],
                portAddress = exptInfo['11. Port address'],
                portResetCode = 0,
                portBonusStimCode = len(stimLabels)+1,
                portEndStimCode = len(stimLabels)+2,
                portSyncCode = len(stimLabels)+3)

# ----


# -- RUN THE EXPERIMENT --

# display starting screens
exptClock=core.Clock()
exptClock.reset()
isiCountdown = core.CountdownTimer(0)
receiver.startScreen(displayText['waitMessage'])
toucher.startScreen(displayText['startMessage'])

# wait for start trigger
for (key,keyTime) in event.waitKeys(keyList=['space','escape'], timeStamped=exptClock):
    if key in ['escape']:
        saveFiles.logAbort(keyTime)
        core.quit()
    if key in ['space']:
        exptClock.add(keyTime)
        saveFiles.logEvent(0,'experiment started')

# signal the start of the experiment
sync.sendSyncPulse()

totalTrials = trials.nTotal + bonusTrials.nTotal
nTrialsComplete = 0

# start the main experiment loop
for thisTrialN in range(totalTrials):
    
    event.clearEvents()
    
    # bonus trial
    if exptInfo['04. Require response on (n) bonus trials per touch'] > 0 and \
        thisTrialN % ((trials.nTotal+bonusTrials.nTotal)/bonusTrials.nTotal) == 0:
        
        thisTrial = next(bonusTrials)
        thisTrial['SignalNo'] = sync.bonusStim
        
        if nTrialsComplete == 0: isiCountdown.reset(min(5,exptInfo['03. Inter-stimulus interval (sec)']))
        present_stimulus(thisTrial,exptInfo,displayText,receiver,toucher,saveFiles,exptClock,isiCountdown,goStopSound,sync)
        
        response = get_vas_response(toucher,receiver,displayText,exptClock,saveFiles)
    
    # regular trial
    else:
        thisTrial = next(trials)
        
        if nTrialsComplete == 0: isiCountdown.reset(10)
        present_stimulus(thisTrial,exptInfo,displayText,receiver,toucher,saveFiles,exptClock,isiCountdown,goStopSound,sync)
        
        response = 'none'
    
    nTrialsComplete +=1
    saveFiles.writeTrialData([nTrialsComplete,
                            thisTrial['stim'],
                            response])
    
    saveFiles.logEvent(exptClock.getTime(),'{} of {} complete' .format(nTrialsComplete, totalTrials))

# -----

# prompt at the end of the experiment
event.clearEvents()
receiver.updateMessage(displayText['finishedMessage'])
toucher.updateMessage(displayText['finishedMessage'])

if exptInfo['09. Play audio cue for video sync']:
    toucher.updateMessage(displayText['finishedSyncMessage'])
    # wait for finish trigger
    for (key,keyTime) in event.waitKeys(keyList=['space','escape'], timeStamped=exptClock):
        if key in ['escape']:
            saveFiles.logAbort(keyTime)
            core.quit()
        if key in ['space']:
            pass
    # signal the end of the experiment
    sync.sendSyncPulse()

saveFiles.logEvent(exptClock.getTime(),'experiment finished')
saveFiles.closeFiles()
core.wait(2)
receiver.win.close()
toucher.win.close()
core.quit()
