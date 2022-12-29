"""
Platform for ETA sensor integration in Home Assistant

Help Links:
 Entity Source: https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/entity.py
 SensorEntity derives from Entity https://github.com/home-assistant/core/blob/dev/homeassistant/components/sensor/__init__.py


author hubtub2

"""

from __future__ import annotations
import requests  
import xmltodict
from lxml import etree
import logging
import voluptuous as vol


_LOGGER = logging.getLogger(__name__)
VAR_PATH = "/user/var"
MENU_PATH = "/user/menu"

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
    PLATFORM_SCHEMA,
    ENTITY_ID_FORMAT
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
import homeassistant.helpers.config_validation as cv

from homeassistant.helpers.entity import generate_entity_id

# See https://github.com/home-assistant/core/blob/dev/homeassistant/const.py
from homeassistant.const import (CONF_HOST, CONF_PORT, TEMP_CELSIUS, ENERGY_KILO_WATT_HOUR, POWER_KILO_WATT, MASS_KILOGRAMS, PRESSURE_BAR, PERCENTAGE)


# See https://community.home-assistant.io/t/problem-with-scan-interval/139031
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_PORT): cv.positive_int,
    #vol.Optional(DEFAULT_NAME): cv.string,
    #vol.Optional(CONF_TYPE): cv.string,
    #vol.Optional(CONF_SCAN_INTERVAL): cv.time_period,
})


def get_base_url(
        config: ConfigType,
        context: str = ""
) -> str:
    return "".join(["http://", config.get(CONF_HOST), ":", str(config.get(CONF_PORT)), context])


def get_entity_name(
        config: ConfigType,
        uri: str
) -> str:
    ns = {'xsi':'http://www.eta.co.at/rest/v1'}
    # TODO: exception handling
    data = requests.get(get_base_url(config, MENU_PATH), stream=True)
    data.raw.decode_content = True
    doc = etree.parse(data.raw)
    for o in doc.iterfind('//xsi:object', namespaces=ns):
        if o.attrib.get('uri') == uri:
            return o.attrib.get('name')
    return "unknown"


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the sensor platform."""
    
    _LOGGER.warning("ETA Integration - setup platform")
    
    var = "/user/var"
    kessel = "/264/10891"
    puffer = "/120/10601"
    lager = "/264/10211"
    solar = "/120/10221"
    kreis1 = "/120/10101"
    kreis2 = "/120/10102"

    entities = [
        EtaSensor(config, hass, get_entity_name(config, puffer + "/0/0/12197"), var + puffer + "/0/0/12197", TEMP_CELSIUS),
        EtaSensor(config, hass, get_entity_name(config, kessel + "/0/0/12077"), var + kessel + "/0/0/12077", POWER_KILO_WATT, device_class = SensorDeviceClass.POWER),
        EtaSensor(config, hass, get_entity_name(config, kessel + "/0/0/12006"), var + kessel + "/0/0/12006", TEMP_CELSIUS),
        EtaSensor(config, hass, get_entity_name(config, kessel + "/0/11109/0"), var + kessel + "/0/11109/0", TEMP_CELSIUS),
        EtaSensor(config, hass, get_entity_name(config, kreis1 + "/0/11125/2121") + " Vorlauf Heizkreis 1", var + kreis1 + "/0/11125/2121", TEMP_CELSIUS),
        EtaSensor(config, hass, get_entity_name(config, kreis2 + "/0/11125/2121")+ " Vorlauf Heizkreis 2", var + kreis2 + "/0/11125/2121", TEMP_CELSIUS),
        EtaSensor(config, hass, get_entity_name(config, lager + "/0/0/12015"), var + lager + "/0/0/12015", MASS_KILOGRAMS, device_class = SensorDeviceClass.WEIGHT),
        EtaSensor(config, hass, get_entity_name(config, kessel + "/0/0/12016"), var + kessel + "/0/0/12016", MASS_KILOGRAMS, device_class = SensorDeviceClass.WEIGHT),
        EtaSensor(config, hass, get_entity_name(config, kessel + "/0/0/12180"), var + kessel + "/0/0/12180", PRESSURE_BAR, device_class = SensorDeviceClass.PRESSURE),
        EtaSensor(config, hass, get_entity_name(config, kessel + "/0/0/12011"), var + kessel + "/0/0/12011", MASS_KILOGRAMS, device_class = SensorDeviceClass.WEIGHT),
        EtaSensor(config, hass, get_entity_name(config, solar + "/0/11139/0"), var + solar + "/0/11139/0", TEMP_CELSIUS),
        EtaSensor(config, hass, get_entity_name(config, solar + "/0/0/12379") + " Solar", var + solar + "/0/0/12379", POWER_KILO_WATT, device_class = SensorDeviceClass.POWER),
        EtaSensor(config, hass, get_entity_name(config, solar + "/0/0/12354"), var + solar + "/0/0/12354", PERCENTAGE, device_class = SensorDeviceClass.MOISTURE),
        EtaSensor(config, hass, get_entity_name(config, kessel + "/0/0/12016") + " gesamt Solar", var + kessel + "/0/0/12016", ENERGY_KILO_WATT_HOUR, device_class = SensorDeviceClass.ENERGY, state_class = SensorStateClass.TOTAL_INCREASING),
        EtaSensor(config, hass, get_entity_name(config, solar + "/0/0/12349") + " Energie", var + solar + "/0/0/12349", ENERGY_KILO_WATT_HOUR, device_class = SensorDeviceClass.ENERGY, state_class = SensorStateClass.TOTAL_INCREASING, factor = 4.8)
    ]
    add_entities( entities )


class EtaSensor(SensorEntity):
    """Representation of a Sensor."""

    #_attr_device_class = SensorDeviceClass.TEMPERATURE
    #_attr_state_class = SensorStateClass.MEASUREMENT
    
    def __init__(self, config, hass, name, uri, unit, state_class = SensorStateClass.MEASUREMENT, device_class =  SensorDeviceClass.TEMPERATURE, factor = 1.0):
        """
        Initialize sensor.
        
        To show all values: http://192.168.178.75:8080/user/menu
        
        There are:
          - entity_id - used to reference id, english, e.g. "eta_outside_temperature"
          - name - Friendly name, e.g "Außentemperatur" in local language
          - unique_id - globally unique id of sensor, e.g. "eta_11.123488_outside_temp", based on serial number
        
        """
        _LOGGER.warning("ETA Integration - init sensor")
        
        self._attr_state_class = state_class
        self._attr_device_class = device_class
        
        id = name.lower().replace(' ','_')
        self._attr_name = name     # friendly name - local language
        self.entity_id = generate_entity_id(ENTITY_ID_FORMAT, "eta_" + id, hass=hass)
        #self.entity_description = description
        self._attr_native_unit_of_measurement = unit
        self.uri = uri
        self.factor = factor
        self.host = config.get(CONF_HOST)
        self.port = config.get(CONF_PORT)
        
        # This must be a unique value within this domain. This is done use serial number of device
        serial1 = requests.get(get_base_url(config, VAR_PATH) + "/264/10891/0/0/12489")
        serial2 = requests.get(get_base_url(config, VAR_PATH) + "/264/10891/0/0/12490")
        
        # Parse
        serial1 = xmltodict.parse(serial1.text)
        serial1 = serial1['eta']['value']['@strValue']
        serial2 = xmltodict.parse(serial2.text)
        serial2 = serial2['eta']['value']['@strValue']
        
        self._attr_unique_id = "eta" + "_" + serial1 + "." + serial2 + "." + name.replace(" ","_")

    def update(self) -> None:
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        TODO: readme: activate first: http://www.holzheizer-forum.de/attachment/28434-eta-restful-v1-1-pdf/
        """
        
        # REST GET
        data = requests.get("http://" + self.host + ":" + str(self.port) + self.uri)
        data = xmltodict.parse(data.text)
        value = data['eta']['value']['@strValue']
        value = float( value.replace(',', '.') ) * self.factor

        self._attr_native_value = value
