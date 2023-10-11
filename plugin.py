# Manage AirZone
# $Id: plugin.py 207 2023-09-21 12:15:26Z eric $
#

"""
<plugin key="AirZone" name="AirZone Local" author="Morand" version="1.0.0" wikilink="" externallink="">
    <description>
        <h2>AirZone Local</h2><br/>
            Manage AirZone system via local REST API.
            Need Airzone listening to port 3000.
        <h3>Parameters</h3><br />
        <ul>
          <li>Address: AirZone local address</li>
          <li>Port: AirZone local port (default 3000) </li>
          <li>ZoneId: the Id of the Zone (default 1) </li>
        </ul>
   </description>
    <params>
      <param field="Address" label="Address" width="150px" default=''/>
      <param field="Port" label="Port" width="50px" default='3000'/>
      <param field="Mode1" label="ZoneId" width="75px">
         <options>
           <option label="1" value="1" default="true" />
           <option label="2" value="2"  />
           <option label="3" value="3"  />
           <option label="4" value="4"  />
           <option label="5" value="5"  />
           <option label="6" value="6"  />
           <option label="7" value="7"  />
           <option label="8" value="8"  />
           <option label="9" value="9"  />
           <option label="10" value="10"  />
           <option label="11" value="11"  />
           <option label="12" value="12"  /> 
           <option label="13" value="13"  /> 
           <option label="14" value="14"  /> 
           <option label="15" value="15"  /> 
           <option label="16" value="16"  /> 
           <option label="17" value="17"  /> 
           <option label="18" value="18"  /> 
           <option label="19" value="19"  /> 
           <option label="20" value="20"  /> 
           <option label="21" value="21"  /> 
           <option label="22" value="22"  />  
           <option label="23" value="23"  />  
           <option label="24" value="24"  />  
           <option label="25" value="25"  />  
           <option label="26" value="26"  />  
           <option label="27" value="27"  />  
           <option label="28" value="28"  />  
           <option label="29" value="29"  />  
           <option label="30" value="30"  /> 
           <option label="31" value="31"  /> 
           <option label="32" value="32"  />  
         </options>
      </param>
      <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal"  default="true" />
            </options>
       </param>
    </params>
</plugin>
"""

import Domoticz
import sys
import os
import requests
import urllib
import json
from urllib.parse import urlparse

# manual:
#   $ wget -qO - --post-data '{"systemid":1,"zoneid":0}' http://192.168.0.116:3000/api/v1/hvac
#   $ wget -qO - --method=PUT --body-data '{"systemid":1,"zoneid":0,"on":1}' http://192.168.0.116:3000/api/v1/hvac

# Unit number according to device type
#    1 -  48 Mode (Stop, Cooling, heating...), 49 for main
#   51 -  98 Temperature and humidity
#  101 - 148 SetPoint, 149 for main
#  151 - 198 Status: On or Off, 199 for main
#  200 : Demand to cold or heat
        
class AirZonePlugin:

    def __init__(self):
        self._addr=None
        self._port=None
        self._httpConn=None
        self._url=None
        self._systemId=1
        self._master = None
        self._masterOptions = {"LevelActions": "",
                               "LevelNames": "Off",
                               "LevelOffHidden": "true",
                               "SelectorStyle": "1"}
        self._modes = {}
        return

    def onStart(self):
        if Parameters["Mode6"] == "Debug":
            Domoticz.Debugging(1)
        Domoticz.Log("onStart called")
        DumpConfigToLog()
        self._addr=Parameters["Address"]
        self._port=Parameters["Port"]
        self._systemId=int(Parameters["Mode1"])
        self._url='http://'+self._addr+':'+self._port+'/api/v1/hvac'
        try:
            data={'systemid':self._systemId}
            r=requests.post(self._url,json=data)
            res=r.json()
            Domoticz.Status('Manfacturer: '+res['data']['manufacturer'])
            for error in res['data']['errors']:
                Domoticz.Status('Errors: '+error)

            # Get list of zones
            data={'systemid':self._systemId,'zoneid':0}
            r=requests.post(self._url,json=data)
            res=r.json()
            for zone in res['data']:
                zId=zone["zoneID"]
                zName=zone["name"]
                Domoticz.Status("Zone "+str(zId)+": "+zName)
                # Get Master Zone
                if self._master == None:
                    if 'master_zoneID' in zone:
                        dataMaster={'systemid':self._systemId,'zoneid':int(zone["master_zoneID"])}
                        r2 = requests.post(self._url,json=dataMaster)
                        self._master = r2.json()['data'][0]
                    else:
                        self._master = zone
                    Domoticz.Status("Master zone is "+str(self._master['zoneID'])+": "+self._master['name'])
                    cpt = 1
                    for mode in self._master['modes']:
                        self._modes[mode]=cpt*10
                        self._masterOptions['LevelNames']+='|'+self.getModeStr(mode)
                        self._masterOptions['LevelActions']+='|'
                        cpt += 1 
                # Create new devices
                if int(zId) not in Devices:
                    self.createDevice(int(zId),zName)
            # Global command is 49 (only 32 zones can be declared so no problem)        
            if 49 not in Devices:
                self.createDevice(49,'Principal')
            # Heat or cold demand
            if 200 not in Devices:
               Domoticz.Device(Name="Demande ",Unit=(200),TypeName="Switch",Switchtype=0,Image=9).Create()
        except Exception as e:
            Domoticz.Error("Can not retrieve info for System")
            Domoticz.Error(str(e))
        return

    def createDevice(self,zId,zName):
        if zId == 49:
            Domoticz.Status("Creating device for main zone")
        else:
            Domoticz.Status("Creating device for zone "+str(zId)+": "+zName)
            # Temperature and humidity
            Domoticz.Device(Name="TÂ°"+zName,Unit=(50+int(zId)),Type=82, Subtype=1).Create()
        # Mode
        Domoticz.Device(Name=zName+' Mode',Unit=int(zId),TypeName="Selector Switch", Image=9,Options=self._masterOptions).Create()
        # SetPoint
        Domoticz.Device(Name="Consigne "+zName,Unit=(100+int(zId)),Type=242,Subtype=1).Create()
        # On/Off
        Domoticz.Device(Name="Status "+zName,Unit=(150+int(zId)),TypeName="Switch",Switchtype=0,Image=9).Create()


    def getModeStr(self,idMode):
        if idMode == 1:
             return 'Stop'
        elif idMode == 2:
            return 'Climatisation'
        elif idMode == 3:
            return 'Chauffage'
        elif idMode == 4:
            return 'Ventilation'
        elif idMode == 5:
            return 'DÃ©shumidificateur'
        elif idMode == 7:
            return 'Auto'

        
    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat called")
        try:
            self.updateStatus()
        except Exception as e:
            Domoticz.Error("Update Failed with:")
            Domoticz.Error(str(e))
            Domoticz.Error("Try to restart")

    def updateStatus(self):
        data={'systemid':self._systemId,'zoneid':0}
        r=requests.post(self._url,json=data)
        if r.status_code==200:
            res=r.json()['data']
            Domoticz.Debug(res)
            allStatus=0
            demand=False
            for zone in res:
                Domoticz.Debug('Updating zone '+zone['name']+': '+str(zone['on'])+', setpoint: '+str(zone['setpoint'])+', roomTemp: '+str(zone['roomTemp'])+', mode: '+self.getModeStr(zone['mode']))
                zoneId = zone['zoneID']
                # Mode
                mode = self._modes[zone['mode']]
                Devices[zoneId].Update(sValue=str(mode),nValue=mode)
                if zoneId==self._master['zoneID']:
                    Devices[49].Update(sValue=str(mode),nValue=mode)
                # Temperature
                uval=' C'
                if zone['units'] == 1:
                    uval=' F'
                temp = str(round(zone['roomTemp'],1))
                Devices[50+zoneId].Update(sValue=str(temp)+';'+str(zone['humidity'])+';0',nValue=0)
                # SetPoint
                sp=zone['setpoint']
                Devices[100+zoneId].Update(sValue=str(sp),nValue=round(sp))
                # On/Off
                sval="Off"
                nval=0
                if zone['on'] == 1:
                    sval="On"
                    nval=1
                    allStatus=1
                Devices[150+zoneId].Update(sValue=sval,nValue=nval)
                #Cold or head Demand
                if zone['cold_demand'] == 1 or zone['heat_demand'] == 1 :
                    demand=True

            if demand:
                if Devices[200].sValue!="On":
                    Devices[200].Update(sValue="On",nValue=1)
            else:
                if Devices[200].sValue!="Off":
                    Devices[200].Update(sValue="Off",nValue=0)
                    
            if allStatus==1:
                Devices[199].Update(sValue="On",nValue=1)
            else:
                Devices[199].Update(sValue="Off",nValue=0)
        else:
            Domoticz.Error(str(r))
            
    def onDeviceAdded(self):
        Domoticz.Log("Adding device")
        return

    def onStop(self):
        return

    def onConnect(self,Connection, Status, Description):
        Domoticz.Log("onConnect called")
        return
        
    def onMessage(self,Connection,Data):
        Domoticz.Debug("onMessage called for connection: "+Connection.Address+":"+Connection.Port)
        Domoticz.Debug(Data)
        return

    def onCommand(self,Unit,Command,Level,Hue):
        Domoticz.Status("onCommand called:" +str(Unit)+" ("+str(Command)+"/"+str(Level)+")")
        zoneId=Unit
        data={"systemid":self._systemId}
        # global commands
        if zoneId==49 or zoneId==149 or zoneId==199:
            zoneId-=49
        if zoneId < 50:
            data["zoneid"]=zoneId
            data['mode']=[k for k, v in self._modes.items() if v == Level][0]
        elif zoneId <100:
            return
        elif zoneId < 150:
            zoneId-=100
            data["zoneid"]=zoneId
            data['setpoint']=Level            
        elif zoneId < 200:
            zoneId-=150
            data["zoneid"]=zoneId
            if Command == 'On':
                data['on']=1
            else:
                data['on']=0
        try:
            Domoticz.Error(self._url+" "+str(data))
            r = requests.put(self._url, json = data)
            if r.status_code!=200:
                Domoticz.Error(str(r.status_code) + ": "+ self._url+" "+str(data))
        except Exception as e:
            Domoticz.Error(str(e))
        self.updateStatus()
        return

    def onNotification(self,Name,Subject,Text,Status,Priority,Sound,ImageFile):
        return

    def onDisconnect(self,Connection):
        Domoticz.Log("onDisconnect called for connection '"+Connection.Name+"'.")
        self._httpConn.Disconnect()
        return

global _plugin
_plugin = AirZonePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

def  onDeviceAdded():
    global _plugin
    _plugin.onDeviceAdded()
    # Generic helper functions

def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
            Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return
