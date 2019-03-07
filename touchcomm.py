from psychopy import visual, event, core
import numpy as np
import random, os, pygame, time, math, serial

class DataFileCollection():
    def __init__(self,foldername,filename,headers,dlgInput):
        self.folder = './'+foldername+'/'
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)
        self.fileprefix = self.folder + filename
        
        self.infoFile = open(self.fileprefix+'_info.csv', 'w') 
        for k,v in dlgInput.items(): self.infoFile.write(k + ',' + str(v) + '\n')
        self.infoFile.close()
        
        self.dataFile = open(self.fileprefix+'_data.csv', 'w')
        self.writeTrialData(headers)
        
        self.logFile = open(self.fileprefix+'_log.csv', 'w')
        self.logFile.write('time,event\n')
    
    def logEvent(self,time,event):
        self.logFile.write('{},{}\n' .format(time,event))
        print('LOG: {} {}' .format(time, event))
    
    def closeFiles(self):
        self.dataFile.close()
        self.logFile.close()
    
    def logAbort(self,time):
        self.logEvent(time,'experiment aborted')
        self.closeFiles()
    
    def writeTrialData(self,trialData):
        lineFormatting = ','.join(['{}']*len(trialData))+'\n'
        self.dataFile.write(lineFormatting.format(*trialData))

class DisplayInterface:
    def __init__(self,fullscr,screen,size,message):
        self.textColour = [-1,-1,-1]
        
        self.win = visual.Window(fullscr = fullscr, 
                                    allowGUI = True, 
                                    screen = screen,
                                    size = size)
        
        self.message = visual.TextStim(self.win,
                                        text = message,
                                        height = 0.12,
                                        color = self.textColour,
                                        units = 'norm',
                                        pos = (0,-0))
        
        self.timerDisplay = visual.TextStim(self.win,
                                        text = '',
                                        height = 0.12,
                                        color = self.textColour,
                                        units = 'norm',
                                        pos = (0.8,-0.8))
    def updateMessage(self,message):
        self.message.text = message
        self.win.flip()
    
    def startScreen(self,message):
        self.message.text = message
        self.message.autoDraw = True
        event.clearEvents()
        self.win.flip()
    
    def updateTimerDisplay(self,timer):
        self.timerDisplay.text = str(int(math.ceil(timer)))
        self.timerDisplay.autoDraw = True
        self.win.flip()
    
    def hideTimerDisplay(self):
        self.timerDisplay.text = ''
        self.timerDisplay.autoDraw = False
        self.win.flip()

class VASInterface(DisplayInterface):
    def __init__(self,fullscr,screen,size,message,question,minLabel,maxLabel):
        DisplayInterface.__init__(self,fullscr,screen,size,message)
        
        self.mouse = event.Mouse(True,None,self.win)
        
        barMarker = visual.TextStim(self.win, text='|', units='norm')
        
        self.VAS = visual.RatingScale(self.win, low=-10, high=10, precision=10, 
            showValue=False, marker=barMarker, scale = question,
            tickHeight=1, stretch=1.5, size = 0.8, 
            labels=[minLabel, maxLabel],
            tickMarks=[-10,10], mouseOnly = True, pos=(0,0))
    
    def getVASrating(self,clock):
        event.clearEvents()
        self.VAS.reset()
        resetTime = clock.getTime()
        aborted = False
        while self.VAS.noResponse and not aborted:
            self.VAS.draw()
            self.win.flip()
            for (key,t) in event.getKeys(['escape'], timeStamped=clock):
                response = -99
                rTime = t
                aborted = True
        if not aborted:
            response = self.VAS.getRating()
            rTime = self.VAS.getRT() + resetTime
        self.win.flip()
        return(response,rTime)

class ButtonInterface(DisplayInterface):
    def __init__(self,fullscr,screen,size,message,nCol,nRow,buttonLabels):
        DisplayInterface.__init__(self,fullscr,screen,size,message)
        self.nButtons = nCol*nRow
        self.outlineColour = [-1,-1,-1]
        self.buttonWidth = 0.6
        self.buttonHeight = 0.2
        self.buttonColour = [0,.25,.9]
        self.mouse = event.Mouse(True,None,self.win)
        
        ##evenly space the buttons from each other and edges
        xpos = np.linspace(-1,1,nCol+2)[1:nCol+1]
        ypos = -np.linspace(-1,1,nRow+2)[1:nRow+1]
        self.buttonPosition = []
        for x in xpos:
            for y in ypos:
                self.buttonPosition += [(x,y)]
        
        self.buttons = []
        self.buttonText = []
        for n in range(self.nButtons):
            self.buttons += [visual.Rect(self.win,
                                    width = self.buttonWidth,
                                    height= self.buttonHeight,
                                    fillColor = self.buttonColour,
                                    lineColor = self.outlineColour,
                                    units = 'norm',
                                    pos = self.buttonPosition[n])]
            self.buttonText += [visual.TextStim(self.win,
                                    text=buttonLabels[n],
                                    height=self.buttonHeight/3,
                                    wrapWidth = self.buttonWidth,
                                    color = self.textColour,
                                    units = 'norm',
                                    pos = self.buttonPosition[n])]
    
    def showButtons(self,buttonLabels):
        self.mouse.clickReset()
        for n in range(self.nButtons):
            self.buttonText[n].text = buttonLabels[n]
            self.buttons[n].opacity = 1
            self.buttons[n].autoDraw = True
            self.buttonText[n].autoDraw = True
        self.win.flip()
    
    def hideButtons(self):
        for n in range(self.nButtons):
            self.buttonText[n].autoDraw = False
            self.buttons[n].autoDraw = False
        self.win.flip()
    
    def getButtonClick(self,clock):
        event.clearEvents()
        self.mouse.clickReset()
        mouseResetTime = clock.getTime()
        clicked = False
        aborted = False
        while not clicked and not aborted:
            for n, button in enumerate(self.buttons):
                if self.mouse.isPressedIn(button, buttons=[0]):
                    mbutton, tList = self.mouse.getPressed(getTime=True)
                    t = tList[0] + mouseResetTime
                    clicked = True
                    response = n
                    break
                ## is the mouse inside the shape (hovering over it)?
                if button.contains(self.mouse):
                    button.opacity = 0.3
                else:
                    button.opacity = 1
                self.win.flip()
                time.sleep(0.001)
            for (key,t) in event.getKeys(['escape'], timeStamped=clock):
                response = -2
                aborted = True
        return (response,t)
    
    def getSelection(self,timeout,clock):
        event.clearEvents()
        confirmed = False
        aborted = False
        fwd = ['a','down']
        bwd = ['b','up']
        conf = ['c','return']
        quit = ['escape']
        buttonSelected = -1
        response = -1
        countDown = core.CountdownTimer()
        countDown.add(timeout)
        while not aborted and not confirmed and countDown.getTime() > 0:
            for (key,t) in event.getKeys(fwd+bwd+conf+quit, timeStamped=clock):
                if key in fwd:
                    self.buttons[buttonSelected].opacity = 1
                    buttonSelected = (buttonSelected+1) % self.nButtons
                    self.buttons[buttonSelected].opacity = 0.3
                if key in bwd:
                    self.buttons[buttonSelected].opacity = 1
                    if buttonSelected < 0:
                        buttonSelected = buttonSelected % self.nButtons
                    else:
                        buttonSelected = (buttonSelected-1) % self.nButtons
                    self.buttons[buttonSelected].opacity = 0.3
                if key in conf and buttonSelected >= 0:
                    self.buttons[buttonSelected].opacity = 1
                    response = buttonSelected
                    confirmed = True
                if key in quit:
                    self.buttons[buttonSelected].opacity = 1
                    response = -2
                    aborted = True
                self.win.flip()
        if countDown.getTime() <= 0: t = clock.getTime()
        self.buttons[buttonSelected].opacity = 1
        self.win.flip()
        return (response,t)

class DataSync():
    def __init__(self,audioSync = None, portType = None, portAddress = None, portResetCode = 0,portBonusStimCode =1, portEndStimCode =9, portSyncCode = 10):
        
        if audioSync!=None:
            self.audioOn = True
            pygame.mixer.pre_init() 
            pygame.mixer.init()
            self.syncSound = pygame.mixer.Sound(audioSync)
        else:
            self.audioOn = False
        
        self.portType = portType
        self.reset = portResetCode
        self.bonusStim = portBonusStimCode
        self.endStim = portEndStimCode
        self.syncPulse = portSyncCode
        
        if self.portType == 'parallel':
            self.port = parallel.ParallelPort(portAddress)
            self.port.setData(self.reset)
        elif self.portType == 'serial':
            self.port = serial.Serial(portAddress,9600,timeout = 0.05)
            self.port.write(int(self.reset).to_bytes(1,'big'))
    
    def sendSyncPulse(self):
        if self.portType == 'parallel':
            self.port.setData(self.syncPulse)
        elif self.portType == 'serial':
            self.port.write(int(self.syncPulse).to_bytes(1,'big'))
        if self.audioOn:
            soundCh = self.syncSound.play()
            while soundCh.get_busy():
                pass
        if self.portType == 'parallel':
            core.wait(0.1)
            self.port.setData(self.reset)
        elif self.portType == 'serial':
            core.wait(0.1)
            self.port.write(int(self.reset).to_bytes(1,'big'))
    
    def sendSignal(self,signalCode):
        if self.portType == 'parallel':
            self.port.setData(signalCode)
        elif self.portType == 'serial':
            self.port.write(int(signalCode).to_bytes(1,'big'))



def present_stimulus(stimInfo,exptInfo,displayText,receiver,toucher,saveFiles,exptClock,isiCountdown,goStopSound,sync):
    silentLead = 0.064
    countDownDuration = 3.0
    stopDuration = 0.434
    ppReset = 0
    
    # display messages
    receiver.updateMessage(displayText['waitMessage'])
    toucher.updateMessage(stimInfo['toucherCueText'])
    
    # get the audio cue file for this trial
    thisCueSound = pygame.mixer.Sound(stimInfo['cueSound'])
    thisSoundDuration = stimInfo['cueSoundDuration']
    
    # check if triggers needed
    triggerOnNeeded = triggerOffNeeded = sync.portType != 'none'
    
    startLogNeeded = stopLogNeeded = True
    
    # wait for inter-stimulus interval duration
    while isiCountdown.getTime() > thisSoundDuration + silentLead + countDownDuration:
        toucher.updateTimerDisplay(isiCountdown.getTime())
        for (key,keyTime) in event.getKeys(['escape'], timeStamped=exptClock):
            saveFiles.logAbort(keyTime)
            core.quit()
    
    # audio cue for toucher
    soundCh = thisCueSound.play()
    saveFiles.logEvent(exptClock.getTime(),'toucher cue {}' .format(stimInfo['stim']))
    ## display messages
    toucher.updateMessage(stimInfo['toucherCueText'] + '.\n'+ displayText['touchMessage'])
    receiver.updateMessage(displayText['fixationMessage'])
    while soundCh.get_busy():
        toucher.updateTimerDisplay(isiCountdown.getTime())
        for (key,keyTime) in event.getKeys(['escape'], timeStamped=exptClock):
            soundCh.stop()
            saveFiles.logAbort(keyTime)
            core.quit()
    
    # signal the stimulus
    soundCh = goStopSound.play()
    saveFiles.logEvent(exptClock.getTime() + silentLead,'countdown to touch')
    while soundCh.get_busy():
        # check if the experiment is aborted
        for (key,keyTime) in event.getKeys(['escape'], timeStamped=exptClock):
            soundCh.stop()
            saveFiles.logAbort(keyTime)
            core.quit()
        # start of the stimulus, audio 'go' signal
        if isiCountdown.getTime() < 0:
            toucher.hideTimerDisplay()
            stimStartTime = None
            if triggerOnNeeded:
                sync.sendSignal(stimInfo['SignalNo'])
                stimStartTime = exptClock.getTime()
                saveFiles.logEvent(stimStartTime, 'port signal sent: {}' .format(stimInfo['SignalNo']))
                triggerOnNeeded = False
            if startLogNeeded:
                if stimStartTime == None:
                    stimStartTime = exptClock.getTime()
                saveFiles.logEvent(stimStartTime,'start touching')
                startLogNeeded = False
            # end of the stimulus, audio 'stop' signal
            if isiCountdown.getTime() < -10:
                stimStopTime = None
                if triggerOffNeeded:
                    sync.sendSignal(sync.endStim)
                    stimStopTime = exptClock.getTime()
                    saveFiles.logEvent(stimStopTime, 'port signal sent: {}' .format(sync.endStim))
                    sync.sendSignal(sync.reset)
                    triggerOffNeeded = False
                if stopLogNeeded:
                    if stimStopTime == None:
                        stimStopTime = exptClock.getTime()
                    isiCountdown.reset(exptInfo['03. Inter-stimulus interval (sec)'])
                    saveFiles.logEvent(stimStopTime,'stop touching')
                    stopLogNeeded = False
        # keep updating the timer display before the stimulus starts, during audio countdown
        elif stopLogNeeded: 
            toucher.updateTimerDisplay(isiCountdown.getTime())
    

def get_button_response(stimLabels,receiverCueText,stimInfo,displayText,receiver,toucher,saveFiles,exptClock):
    # wait for participant
    toucher.updateMessage(displayText['waitMessage'])
    
    # present cue buttons for receiver to make a choice
    receiver.updateMessage('')
    
    ## randomise button positions
    randomStimLabels = random.sample(stimLabels,len(stimLabels))
    receiver.showButtons([receiverCueText[i] for i in randomStimLabels])
    saveFiles.logEvent(exptClock.getTime(),'buttons presented')
    
     # get response from receiver
    (responseN,rTime) = receiver.getButtonClick(exptClock)
    if responseN == -2:
        saveFiles.logAbort(rTime)
        core.quit()
    elif responseN == -1:
        response = 'timeout'
    else:
        response = randomStimLabels[responseN]
    correctText = ['incorrect','correct']
    saveFiles.logEvent(rTime,'receiver responded {} - {}' .format(response, correctText[int(stimInfo['stim']==response)]))
    
    # stop drawing buttons for receiver
    receiver.hideButtons()
    return(response)

def get_vas_response(toucher,receiver,displayText,exptClock,saveFiles):
    # wait for participant
    toucher.updateMessage(displayText['waitMessage'])
    
    # show VAS to participant and get rating
    receiver.updateMessage('') ## hide message
    (rating,rTime) = receiver.getVASrating(exptClock)
    if rating == -99:
        saveFiles.logAbort(rTime)
        core.quit()
    saveFiles.logEvent(rTime,'Pleasantness rating (-10","10) = {}' .format(rating))
    
    return(rating)


if __name__ == "__main__":
    # demo of the button screens and getting input from mouse and then keyboard
    items = ['attention','gratitude','love','sadness','happiness','calming']
    receiverCueText = dict((line.strip().split('\t') for line in open('receiver-cues.txt')))
    myInt = ButtonInterface(True,
                            1,
                            [1280,720],
                            'wait',
                            2,3,
                            [receiverCueText[i] for i in items])
    exptClock = core.Clock()
    exptClock.reset()
    #buttonOpacity = 1
    
    randomItems = random.sample(items, len(items))
    myInt.showButtons([receiverCueText[i] for i in randomItems])
    clock = core.Clock()
    clock.reset()
    (responseN,rTime) = myInt.getButtonClick(exptClock)
    print(rTime)
    if responseN == -2:
        response = 'aborted'
    elif responseN == -1:
        response = 'timeout'
    else:
        response = randomItems[responseN]
    print(response)
    
    myInt.hideButtons()
    core.wait(2)
    
    randomItems = random.sample(items, len(items))
    myInt.showButtons([receiverCueText[i] for i in randomItems])
    
    (response,rTime) = myInt.getSelection(20,clock)
    
    print(rTime)
    if response == -2:
        print('aborted')
    elif response == -1:
        print('timeout')
    else:
        print(randomItems[response])
        
    myInt.hideButtons()
    core.wait(2)
    
    core.quit()
