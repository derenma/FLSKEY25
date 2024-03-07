# name=Akai APC Key 25 MK2
# url=https://forum.image-line.com/viewtopic.php?f=1994&t=225886
# Author: Martijn Tromp // Matt Deren
# Changelog:
# 23/04/2020 0.01: Implement Play/Pause Button (AKFSM-2)
# 23/04/2020 0.02: Clean up code and handle Note Off
# 23/04/2020 0.03: Add Record and Pattern/Song toggle
# 24/04/2020 0.04: More refactoring, making it easier to map and implement new stuff.
# 02/05/2020 0.05: Implement stuff for calling LEDs on the controller. The played note gets passed to the method.
# 03/05/2020 0.06: Basic fast forward functionality using playback speed. Time in FL studio seems to be mismatched.
#                  Lights work.
#                  Mode switching now using shift modifier.
# 08/05/2020 0.07: fastForward/rewind implemented using transport.fastForward/transport.rewind
#                  kill LEDs when exiting FL Studio
#  3/06/2024 0.10: Reworked most of the LED controls
#				 : Added better knob control (no longer jumps from 1 to 127)
#                : Performance mode scripting added! (No color changes as of yet)
#                : 		- Must do a Shift-Stop to enter correct mode
#                :		- Updating script will turn off pad leds until a change is made to the playlist
#				 :		- Added mappings for LEDs as well as pad controls
#                : There is a *ton* of debug/info lines in this code. Will remove after beta
#                : Controls to the right and bottom of the pads have NOT been mapped yet
#				 : TODO:
#				 :		- Clean and refactor for brevity (It's still a wierd mix of two different scripts..)
#				 :		- Map the rest of the controls
# 				 :		- ??
#				 :		- Profit?

# This import section is loading the back-end code required to execute the script. You may not need all modules that are available for all scripts.
import transport
import mixer
import ui
import midi
import sys
import device
import channels
import playlist
import patterns
import plugins

#definition of controller modes
ctrlUser = 0
ctrlTransport = 1
ctrlMixer = 2
ctrlBrowser = 3
ctrlPattern = 4
ctrlPlaylist = 5

controllerMode = 0

# Shift Modifier and Button definition
shiftModifier = 0
shiftButton = 98

#LED colorCodes, for blink add 1 to the value
green = 1
red = 3
yellow = 5

# Versions?
#APCKeyVersion = 1 # MK1
APCKeyVersion = 2  # MK2

# Echo levels
def info(message):
	info = False
	if info:
		print(f"Info: {message}")

def debug(message):
	debug = False
	if debug:
		print(f"* Debug: {message}")

def msg(message):
	msg = True
	if msg:
		print(f"Message: {message}")

class InitClass():
	def __init__(self):
		print("Actual Init.")

	def startTheShow(self):
		#set global transport mode
		msg("Welcome Friends!")
		shiftAction = ShiftAction()
		shiftAction.setTransportMode(82) #need to set the note manually, since no note was actually played.

class KnobHandler():
	def __init__(self):
		self.knobs = {}

		for a in range(47, 56):
			self.knobs[a] = 1
		pass

	def adjust(self, event):
		knob = event.data1
		state = event.data2
		if state == 1:
			if self.knobs[knob] > 1:
				self.knobs[knob] = self.knobs[knob] - 1
			event.data2 = self.knobs[knob]
		if state == 127:
			if self.knobs[knob] < 128:
				self.knobs[knob] = self.knobs[knob] + 1
			event.data2 = self.knobs[knob]

		return(event)

class DeviceHandler():
	def __init__(self):
		debug("Device Info:")
		debug(" - getName:" + str(device.getName()))
		debug(" - isAssigned:" + str(device.isAssigned()))
		
		# deviceID Data Map
		self.dIdMap = [None] * 29
		self.dIdMap[0] = "Manu. ID" # 0x47
		self.dIdMap[1] = "Prod. ID" # 0x4E
		self.dIdMap[2] = "Bytes Start" # 0x00
		self.dIdMap[3] = "Bytes End" # 0x19
		self.dIdMap[4] = "<Version>"
		self.dIdMap[5:7] = "xxx"
		self.dIdMap[8] = "<DeviceID>"
		self.dIdMap[9] = "<Serial>"
		self.dIdMap[10:12] = "xxx"
		self.dIdMap[13] = "<Manufacturing>"
		self.dIdMap[14:28] = "xxxxxxxxxxxxxxx"

		self.parseDevID()

	def parseDevID(self):
		mmcOffset = 5
		debug(" - Raw Device ID:")
		for idx,c in enumerate(device.getDeviceID()):
			debug(f"  - {idx:02d}/{idx+1+mmcOffset:02d}: {self.dIdMap[idx]:>15}: (x){c}") # (d){c:02X} 

class MidiInHandler():
	def __init__(self):
		self.mapPadFunction = []
		self.inPerformanceMode = False
		self.knobs = KnobHandler()
		
		# Real
		#32,33,34,35,36,37,38,39
		#24,25,26,27,28,29,30,31
		#16,17,18,19,20,21,22,23
		#08,09,10,11,12,13,14,15
		#00,01,02,03,04,05,06,07

		# Mapped
		#00,01,02,03,04,05,06,07
		#12,13,14,15,16,17,18,19
		#24,25,26,27,28,29,30,31
		#36,37,38,39,40,41,42,43
		
		self.map = {}
		self.map[0] = 48
		self.map[1] = 49
		self.map[2] = 50 
		self.map[3] = 51
		self.map[4] = 52
		self.map[5] = 53
		self.map[6] = 54
		self.map[7] = 55
		
		self.map[8] = 36
		self.map[9] = 37
		self.map[10] = 38
		self.map[11] = 39
		self.map[12] = 40
		self.map[13] = 41
		self.map[14] = 42
		self.map[15] = 43
		
		self.map[16] = 24
		self.map[17] = 25
		self.map[18] = 26
		self.map[19] = 27
		self.map[20] = 28
		self.map[21] = 29
		self.map[22] = 30
		self.map[23] = 31

		self.map[24] = 12
		self.map[25] = 13
		self.map[26] = 14
		self.map[27] = 15
		self.map[28] = 16
		self.map[29] = 17
		self.map[30] = 18
		self.map[31] = 19

		self.map[32] = 0
		self.map[33] = 1
		self.map[34] = 2
		self.map[35] = 3
		self.map[36] = 4
		self.map[37] = 5
		self.map[38] = 6
		self.map[39] = 7

	#'controlNum', 'controlVal', 'data1', 'data2', 'handled', 'inEv', 'isIncrement',
	#'midiChan', 'midiChanEx', 'midiId', 'note', 'outEv', 'pitchBend', 'pmeFlags',
	#'port', 'pressure', 'progNum', 'res', 'senderId', 'status', 'sysex'
	def OnMidiIn(self, event):
		if event.data1 < 56 and event.data1 > 47:
			event = self.knobs.adjust(event)
		debug(f"OnMidiIn:")
		debug(f"  - controlNum: {event.controlNum}")
		debug(f"  - controlVal: {event.controlVal}")
		debug(f"  - data1: {event.data1}")
		debug(f"  - data2: {event.data2}")
		debug(f"  - handled: {event.handled}")
		
		debug(f"  - inEv: {int(event.inEv)}")
		debug(f"  - outEv: {int(event.outEv)}")
		
		debug(f"  - isIncrement: {event.isIncrement}")
		debug(f"  - midiChan: {int(event.midiChan)}")
		debug(f"  - midiChanEx: {int(event.midiChanEx)}")
		debug(f"  - midiId: {event.midiId}")
		debug(f"  - note: {event.note}")
		debug(f"  - outEv: {event.outEv}")

		debug(f"  - pitchBend: {event.pitchBend}")
		debug(f"  - pmeFlags: {event.pmeFlags}")
		debug(f"  - port: {event.port}")
		debug(f"  - pressure: {event.pressure}")
		debug(f"  - progNum: {event.progNum}")
		debug(f"  - res: {event.res:5.8f}")
		debug(f"  - res: {event.res}")
		debug(f"  - senderId: {event.senderId}")	
		debug(f"  - status: {event.status}")
		debug(f"  - sysex: {event.sysex}")

		
	# dictionary mapping 
	def noteDict(self, i):
		#dictionary with list of tuples for mapping note to class and method
		dict={
			91:[("GlobalAction", "togglePlay")], # PLAY/PAUSE button on controller
			93:[("GlobalAction", "toggleRecord")], # REC button on controller
			82:[("ShiftAction", "setTransportMode")], #CLIP STOP button on controller
			83:[("ShiftAction", "setMixerMode")], #SOLO button on controller
			84:[("ShiftAction", "setBrowserMode")], 
			85:[("ShiftAction", "setPatternMode")],
			86:[("ShiftAction", "setPlayListMode"), ("TransportAction", "toggleLoopMode")], 
			81:[("ShiftAction", "setUserMode")],
			66:[("TransportAction", "pressRewind"), ("ReleaseAction", "releaseRewind")],
			67:[("TransportAction", "pressFastForward"), ("ReleaseAction", "releaseFastForward")],
		}
		return dict.get(i,[("notHandled", "")])

	def callAction(self, actionType, action, note):
			callClass = getattr(sys.modules[__name__], actionType)()
			func = getattr(callClass, action) 
			return func(note)

	#Handle the incoming MIDI event
	def OnMidiMsg(self, event):
		global shiftModifier

		#Custom MIDI ids
		midiNOTE_ON = 144
		midiNOTE_OFF = 128

		# Map our input midi key to our new position
		try:
			event.data1 = self.map[event.data1]
		except KeyError:
			pass

		# If for some reason you need to evaluate each mapping, enable this
		#
		#info("Pad Remapping ***")
		#for idx,val in enumerate(map):
		#	if event.data1 == val:
		#		info(f"******* Key {int(event.data1)} Mapped to: {val}")
		#		event.data1 = map[val]

		debug(playlist.getTrackActivityLevel(1))
		info( f"DEVICE: Controller Mode: {str(controllerMode)}")
		msg(  f"DEVICE:  Key/Note - {str(event.data1)} - Value: {str(event.data2)}")
		debug(f"DEVICE:   Key Val - {str(event.data2)}")
		debug(f"DEVICE:   MidiCH  - {str(event.midiChan)}")
		debug(f"DEVICE:   MidiID  - {str(event.midiId)}")
		
		if (event.midiChan == 0 and event.pmeFlags and midi.PME_System != 0): # MidiChan == 0 --> To not interfere with notes played on the keybed
			noteFuncList = self.noteDict(event.data1)
			for noteFunc in noteFuncList:
				actionType = noteFunc[0]
				action = noteFunc[1]
				if (noteFunc[0] == "notHandled" and event.data1 != shiftButton and controllerMode != ctrlUser):
					event.handled = True
				#elif (event.midiId == midi.MIDI_NOTEOFF):
				elif (event.midiId == midiNOTE_OFF):
					event.handled = True
					if (event.data1 == shiftButton):
						shiftModifier = 0
					elif (actionType == "ReleaseAction" and shiftModifier == 0):
						self.callAction(actionType, action, event.data1)
						event.handled = True
				#elif (event.midiId == midi.MIDI_NOTEON):
				elif (event.midiId == midiNOTE_ON):
					event.handled = True
					if (event.data1 == shiftButton):
						shiftModifier = 1
						info ("shiftmodifier on " + str(shiftModifier))
					if (actionType == "ShiftAction" and shiftModifier == 1):
						self.callAction(actionType, action, event.data1)
					elif (actionType == "GlobalAction" and shiftModifier == 0):
						self.callAction(actionType, action, event.data1)
					elif (actionType == "TransportAction" and controllerMode == ctrlTransport and shiftModifier == 0):
						self.callAction(actionType, action, event.data1)
					elif (actionType == "MixerAction" and controllerMode == ctrlMixer and shiftModifier == 0):
						self.callAction(actionType, action, event.data1)
					elif (controllerMode == ctrlUser and event.data1 != shiftButton):
						event.handled = False

#Handle action that use the shift modifier
class ShiftAction():
	def setTransportMode(self, note):
			self.changeMode(ctrlTransport, note)
			msg("FUNCTION: Transport Mode set")

	def setMixerMode(self, note):
			self.changeMode(ctrlMixer, note)
			msg("FUNCTION: Mixer Mode set")

	def setBrowserMode(self, note):
			self.changeMode(ctrlBrowser, note)
			msg("FUNCTION: Browser Mode set")

	def setPatternMode(self, note):
			self.changeMode(ctrlPattern, note)
			msg("FUNCTION: Pattern Mode set")

	def setPlayListMode(self, note):
			self.changeMode(ctrlPlaylist, note)
			msg("FUNCTION: PlayList Mode set")

	def setUserMode(self, note):
			self.changeMode(ctrlUser, note)
			msg("FUNCTION: User Mode set")

	def changeMode(self, ctrlMode, note):
		global controllerMode
		print(f"controllerMode: {controllerMode}")
		ledCtrl = LedControl()
		ledCtrl.killAllLights()
		controllerMode = ctrlMode
		ledCtrl.setLedMono(note, False)

#Handle actions that trigger on button release
class ReleaseAction():
	def releaseFastForward(self, note):
		if (controllerMode == ctrlTransport):
			transport.fastForward(0)
			ledCtrl = LedControl()
			ledCtrl.ledOff(note)
			msg("fastForward off")
	def releaseRewind(self, note):
		if (controllerMode == ctrlTransport):
			transport.rewind(0)
			ledCtrl = LedControl()
			ledCtrl.ledOff(note)
			msg("rewind off")

#Handle actions that will be independent of selected mode.
class GlobalAction():
	def togglePlay(self, note):
		debug("isPlaying: " + str(transport.isPlaying()))
		if (transport.isPlaying() == 0):
			transport.start()
			msg("Starting Playback")
		elif (transport.isPlaying() == 1):
			transport.stop()
			msg("Stopping Playback")
	def toggleRecord(self, note):
		if (transport.isPlaying() == 0): # Only enable recording if not already playing
			transport.record()
			msg("Toggle recording")
	
#Handle actions that work in Transport Control ControllerMode
class TransportAction():
	def toggleLoopMode(self, note):
		if (transport.isPlaying() == 0): #Only toggle loop mode if not already playing
			transport.setLoopMode()
			msg("Song/Pattern Mode toggled")

	def pressFastForward(self, note):
		transport.fastForward(2)
		ledCtrl = LedControl()
		ledCtrl.setLedMono(note, False)
		msg("FastForward on")

	def pressRewind(self, note):
		transport.rewind(2)
		ledCtrl = LedControl()
		ledCtrl.setLedMono(note, False)
		msg("Rewind on")

class LedControl():
	def __init__(self):
		self.ledOffCode = 128
		self.ledOnCode = 144
		self.pulseChannel = self.ledOnCode + 6
		# Button States
		self.playing = False

		colorCode = 0
		self.PrevBeat = 0

	def OnUpdateBeatIndicator(self, value):
		CcIdTempo = 0x2F
		if self.PrevBeat == 0:
			if self.PrevBeat != value:
				# bar/beat off -> on
				self.ledOn(7, 50, 6)
				self.PrevBeat = value
		else:
			if self.PrevBeat != value:
				if value == 0:
					#bar/beat on -> off
					self.ledOff(7)
				self.PrevBeat = value

	def ledOn(self, pad, color, brightness):
		# 0 - Dimmest
		# 6 - Brightest
		print(f"ledOn: {pad}")
		if pad >= 0 and pad <=40:
			device.midiOutMsg((self.ledOnCode + brightness) + (pad << 8) + (color << 16))
		else:
			debug(f"ledOn : Invalid pad number sent: {pad}")

	def ledOff(self, pad):
		if (pad >= 0 and pad <=40) or (pad >= 82 and pad <= 87) or (pad >= 64 and pad <= 72):
			self.sendMidiCommand(pad, 0)
			#device.midiOutMsg(self.ledOnCode + (pad << 8) + (0 << 16))
		else:
			debug(f"PadOff: Invalid pad number sent: {pad}")

	def ledPulse(self, pad, color, speed):
		# 0 - off
		# 1 - Fastest
		# 9 - Slowest
		if pad >= 0 and pad <=40:
			device.midiOutMsg((self.pulseChannel + speed) + (pad << 8) + (color << 16))
		else:
			debug(f"PulseOn: Invalid pad number sent: {pad}")

	def setLedMono(self, note, blink):
		if ((64 <= note <= 71) or (82 <= note <= 86)): # 64 to 71: buttons under grid, 82 to 86: buttons to the right of grid.
			if (blink == True):
				colorCode = 2
			else:
				colorCode = 1
			self.sendMidiCommand(note, colorCode)

	def setLedOff(self, note):
		self.sendMidiCommand(note, 0)

	def killAllLights(self):
		self.killRightSideLights()
		self.killGridLights()
		self.killUnderLights()

	def killRightSideLights(self):
		for i in range(82, 87):
			self.ledOff(i)

	def killUnderLights(self):
		for i in range(64, 72):
			#print(f"killing lights {i}")
			self.ledOff(i)

	def killGridLights(self):
		for i in range(40):
			#print(f"killing lights {i}")
			self.ledOff(i)

	def sendMidiCommand(self, note, colorCode):
		device.midiOutMsg(midi.MIDI_NOTEON + (note << 8) + (colorCode << 16))

class PerformanceMode:
	def __init__(self, led):
		self.led = led
		self.firstRun = True

		self.pos = []
		self.pos.append([0])
		self.pos.append([32,33,34,35,36,37,38,39])
		self.pos.append([24,25,26,27,28,29,30,31])
		self.pos.append([16,17,18,19,20,21,22,23])
		self.pos.append([8,  9,10,11,12,13,14,15])
		self.pos.append([0,  1, 2, 3, 4, 5, 6, 7])
		
		# If script restart, this should update the LEDs
		self.OnUpdateLiveMode(0)

	def OnUpdateLiveMode(self, value):
		if self.firstRun == True:
			self.firstRun = False
			print("**** Live Mode Init!")

		debug(f"-----------------------------------------------")
		debug(" Patterns")
		if debug:
			num = patterns.patternNumber()
		debug(f"patternMax: {patterns.patternMax()}")
		debug(f"patternCount: {patterns.patternCount()}")
		debug(f"(selected) patternNumber: {num}")
		debug(f"(selected) getPatternName: {patterns.getPatternName(num)}")
		debug(f"(selected) getPatternLength: {patterns.getPatternLength(num)}")
		debug(f"(selected) isPatternSelected {patterns.isPatternSelected(num)}")
		debug(f"(selected) getPatternName: {patterns.getPatternName(num)}")
		debug(f"(selected) getPatternColor: {patterns.getPatternColor(num)}")

		if debug:
			for a in range(1, 10):
				debug(f"{a}.0.getLiveStatus: {str(playlist.getLiveStatus(a,0))}")
				debug(f"{a}.1.getLiveStatus: {str(playlist.getLiveStatus(a,1))}")
		
		debug("-----------------------------------------------")
		debug(" Tracks")
		trackNum = 1
		debug(f"isTrackSelected: {playlist.isTrackSelected(trackNum)}")
		debug(f"trackCount: {int(playlist.trackCount())}")
		debug(f"getTrackName: {playlist.getTrackName(trackNum)}")
		debug(f"getLiveLoopMode: {playlist.getLiveLoopMode(trackNum)}")
		debug(f"getLiveTriggerMode: {playlist.getLiveTriggerMode(trackNum)}")
		debug(f"getLivePosSnap: {playlist.getLivePosSnap(trackNum)}")
		debug(f"getLiveTrigSnap: {playlist.getLiveTrigSnap(trackNum)}")
		debug(f"getLiveStatus: {playlist.getLiveStatus(trackNum)}")

		# idx      = top -> bottom
		# blocknum = left -> right
		for idx in range(1, 6):
			for blockNum in range(0, 8):
				active = playlist.getLiveBlockStatus(idx,blockNum,0)
				debug(f"{idx}.{blockNum}.0.getLiveBlockStatus: {playlist.getLiveBlockStatus(idx,blockNum,0)}")
				if active:
					debug(f"{idx},{blockNum},{self.pos[idx][blockNum]}")
					if active == 7:
						self.led.ledOn(self.pos[idx][blockNum], 30, 6)
					else:
						self.led.ledOn(self.pos[idx][blockNum], 30, 1)
				else:
					self.led.ledOff(self.pos[idx][blockNum])
				#print(f"{idx}.{blockNum}.1.getLiveBlockStatus:", playlist.getLiveBlockStatus(idx,blockNum,1))
				#print(f"{idx}.{blockNum}.2.getLiveBlockStatus:", playlist.getLiveBlockStatus(idx,blockNum,2))
		
		debug(f"getLiveBlockColor: {int(playlist.getLiveBlockColor(trackNum,0))}")
		debug(f"OnUpdateLiveMode: {value} changed")

start = InitClass()
midiIn = MidiInHandler()
led = LedControl()
live = PerformanceMode(led)

def OnUpdateLiveMode(event):
	live.OnUpdateLiveMode(event)

def OnUpdateBeatIndicator(event):
	led.OnUpdateBeatIndicator(event)

def OnChannelPressure(event):
	debug(f"OnChannelPressure: {event}")

def OnControlChange(event):
	debug(f"OnControlChange: {event}")

def OnSysEx(event):
	debug(f"OnSysEx: {event}")

def OnNoteOn(event):
	debug(dir(event))
	debug(f"OnNoteOn: {event}")

def OnNoteOff(event):
	debug(f"OnNoteOff: {event}")

def OnIdle():
	pass
	#print(f"OnIdle: Active")

def OnMidiMsg(event):
	midiIn.OnMidiMsg(event)

def OnMidiIn(event):
	midiIn.OnMidiIn(event)

def OnMidiOutMsg(event):
	debug(f"OnMidiOutMsg: {event}")

def OnInit():
	start.startTheShow()
	
def OnDeInit():
	led.killAllLights()
